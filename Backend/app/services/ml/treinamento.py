from __future__ import annotations

import math
from datetime import date
from typing import Callable

import numpy as np
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.consumo_tratado import ConsumoTratado
from app.models.modelo_treinado import ModeloTreinado
from app.services.ml.elegibilidade import separar_elegiveis
from app.services.ml.estimadores import ALGORITMOS, Estimador
from app.services.ml.validacao import (
    ResultadoAvaliacao,
    comparar_algoritmos,
    selecionar_melhor,
)


def _serie_mensal_continua(por_periodo: dict[date, float]) -> np.ndarray:
    """Reindexa a série num intervalo mensal contínuo (do 1º ao último mês),
    preenchendo com zero os meses sem consumo — demanda intermitente é sinal,
    não ausência de dado (ver metrics.mape, que trata o zero real)."""
    inicio, fim = min(por_periodo), max(por_periodo)
    valores: list[float] = []
    atual = inicio
    while atual <= fim:
        valores.append(por_periodo.get(atual, 0.0))
        atual += relativedelta(months=1)
    return np.array(valores)


def carregar_series_por_item(db: Session, empresa_id: int) -> dict[int, np.ndarray]:
    """Série mensal de quantidade por item (somada entre locais), em ordem temporal
    e com os meses faltantes preenchidos com zero."""
    linhas = (
        db.query(
            ConsumoTratado.item_id,
            ConsumoTratado.periodo,
            func.sum(ConsumoTratado.quantidade_total),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id, ConsumoTratado.periodo)
        .order_by(ConsumoTratado.item_id, ConsumoTratado.periodo)
        .all()
    )
    por_item: dict[int, dict[date, float]] = {}
    for item_id, periodo, quantidade in linhas:
        por_item.setdefault(item_id, {})[periodo] = float(quantidade)
    return {item_id: _serie_mensal_continua(mapa) for item_id, mapa in por_item.items()}


def ultimo_periodo_por_item(db: Session, empresa_id: int) -> dict[int, date]:
    linhas = (
        db.query(ConsumoTratado.item_id, func.max(ConsumoTratado.periodo))
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id)
        .all()
    )
    return {item_id: periodo for item_id, periodo in linhas}


def _media_sem_nan(valores: list[float]) -> float:
    valores = [v for v in valores if not math.isnan(v)]
    return float(np.mean(valores)) if valores else float("nan")


def selecionar_algoritmo_por_item(
    series_por_item: dict[int, np.ndarray],
    *,
    algoritmos=ALGORITMOS,
    fabrica: Callable[[str], Estimador] | None = None,
    n_dobras: int = 3,
    horizonte: int = 1,
) -> dict[int, ResultadoAvaliacao]:
    """Para CADA item, avalia todos os algoritmos por walk-forward e escolhe o de
    menor MAPE. A decisão é por item — itens diferentes podem ter algoritmos
    diferentes (diverge do RFC 5.6.4, que seleciona um único pela média Classe A)."""
    selecao: dict[int, ResultadoAvaliacao] = {}
    for item_id, serie in series_por_item.items():
        resultados = comparar_algoritmos(
            serie, algoritmos, n_dobras=n_dobras, horizonte=horizonte, fabrica=fabrica
        )
        selecao[item_id] = selecionar_melhor(resultados, criterio="mape")
    return selecao


def _nan_para_none(valor: float) -> float | None:
    return None if valor is None or math.isnan(valor) else float(valor)


def desativar_modelos_anteriores(db: Session, empresa_id: int) -> None:
    db.query(ModeloTreinado).filter(
        ModeloTreinado.empresa_id == empresa_id, ModeloTreinado.ativo.is_(True)
    ).update({ModeloTreinado.ativo: False})


def ativar_modelo(db: Session, empresa_id: int, modelo_id: int) -> ModeloTreinado | None:
    """Ativa um modelo específico e desativa os demais da empresa (RF11)."""
    modelo = (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.id == modelo_id, ModeloTreinado.empresa_id == empresa_id)
        .first()
    )
    if not modelo:
        return None
    desativar_modelos_anteriores(db, empresa_id)
    modelo.ativo = True
    db.commit()
    db.refresh(modelo)
    return modelo


def treinar_empresa(
    db: Session,
    empresa_id: int,
    *,
    algoritmos=ALGORITMOS,
    fabrica: Callable[[str], Estimador] | None = None,
    n_dobras: int = 3,
    horizonte: int = 1,
) -> ModeloTreinado:
    """Seleciona o melhor algoritmo POR ITEM (menor MAPE) sobre todos os itens
    elegíveis e persiste como um único modelo ativo da empresa; a escolha de cada
    item fica registrada em `parametros["itens"]` e é usada na geração das previsões."""
    series_por_item = carregar_series_por_item(db, empresa_id)
    elegiveis, _omitidos = separar_elegiveis(series_por_item)
    if not elegiveis:
        raise ValueError("Nenhum item elegível para treino (RN06).")

    selecao = selecionar_algoritmo_por_item(
        elegiveis, algoritmos=algoritmos, fabrica=fabrica, n_dobras=n_dobras, horizonte=horizonte
    )
    melhores = list(selecao.values())
    # Métricas do modelo = média das métricas do melhor algoritmo de cada item.
    mae = _media_sem_nan([r.mae for r in melhores])
    rmse = _media_sem_nan([r.rmse for r in melhores])
    mape = _media_sem_nan([r.mape for r in melhores])

    desativar_modelos_anteriores(db, empresa_id)
    modelo = ModeloTreinado(
        empresa_id=empresa_id,
        algoritmo="melhor_por_item",
        rmse=_nan_para_none(rmse),
        mae=_nan_para_none(mae),
        mape=_nan_para_none(mape),
        ativo=True,
        parametros={
            "selecao": "por_item",
            "n_itens_avaliados": len(selecao),
            "itens": {
                str(item_id): {
                    "algoritmo": r.algoritmo,
                    "mae": _nan_para_none(r.mae),
                    "rmse": _nan_para_none(r.rmse),
                    "mape": _nan_para_none(r.mape),
                }
                for item_id, r in selecao.items()
            },
        },
    )
    db.add(modelo)
    db.commit()
    db.refresh(modelo)

    # Rastreabilidade (RNF09)
    from app.services import log_service

    log_service.registrar(
        db, "treino", "info",
        f"Modelo treinado com seleção por item (MAPE médio={mape})",
        empresa_id=empresa_id,
        contexto={"selecao": "por_item", "n_itens": len(selecao)},
    )
    return modelo
