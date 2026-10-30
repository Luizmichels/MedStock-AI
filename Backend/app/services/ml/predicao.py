"""Geração de previsões multi-step e persistência.

Usa o algoritmo do modelo ativo para projetar ``horizonte`` meses à frente para
cada item elegível, de forma recursiva, com um intervalo simples de incerteza.
"""

from __future__ import annotations

from typing import Callable

from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.consumo_tratado import ConsumoTratado
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.services.ml.elegibilidade import separar_elegiveis
from app.services.ml.estimadores import ALGORITMOS, Estimador, criar
from app.services.ml.treinamento import (
    HORIZONTE_MESES,
    carregar_series_por_item,
    estender_ate_referencia,
    periodo_referencia,
    ultimo_periodo_por_item,
)

HORIZONTE_PADRAO = HORIZONTE_MESES
# Largura do intervalo de incerteza (±20%) — heurística simples e transparente.
_MARGEM_INTERVALO = 0.20


def algoritmo_do_item(modelo: ModeloTreinado, item_id: int) -> str:
    """Algoritmo escolhido para o item no treino (seleção por item). Cai para um
    algoritmo válido caso o mapa não exista (ex.: modelo antigo)."""
    selecao = (modelo.parametros or {}).get("itens", {})
    info = selecao.get(str(item_id))
    if info and info.get("algoritmo") in ALGORITMOS:
        return info["algoritmo"]
    return modelo.algoritmo if modelo.algoritmo in ALGORITMOS else "sma"


def gerar_previsoes(
    db: Session,
    empresa_id: int,
    modelo: ModeloTreinado,
    horizonte: int = HORIZONTE_PADRAO,
    *,
    fabrica: Callable[[str], Estimador] | None = None,
) -> list[Previsao]:
    construir = fabrica or criar

    series_por_item = carregar_series_por_item(db, empresa_id)
    elegiveis, _omitidos = separar_elegiveis(series_por_item)
    ultimos = ultimo_periodo_por_item(db, empresa_id)
    # Origem COMUM: todas as previsões partem do último mês da empresa, então todo
    # item projeta a mesma janela futura (RF08).
    referencia = periodo_referencia(db, empresa_id)

    # Regeneração completa: descarta as previsões anteriores da empresa.
    db.query(Previsao).filter(Previsao.empresa_id == empresa_id).delete()

    novas: list[Previsao] = []
    for item_id, serie in elegiveis.items():
        serie = estender_ate_referencia(serie, ultimos[item_id], referencia)
        estimador = construir(algoritmo_do_item(modelo, item_id))
        estimador.fit(serie)
        previsto = estimador.prever(horizonte)

        base = referencia
        for passo, valor in enumerate(previsto, start=1):
            quantidade = max(float(valor), 0.0)
            periodo = base + relativedelta(months=passo)
            previsao = Previsao(
                empresa_id=empresa_id,
                modelo_id=modelo.id,
                item_id=item_id,
                periodo=periodo,
                quantidade_prevista=quantidade,
                intervalo_inferior=quantidade * (1 - _MARGEM_INTERVALO),
                intervalo_superior=quantidade * (1 + _MARGEM_INTERVALO),
            )
            db.add(previsao)
            novas.append(previsao)

    db.commit()
    return novas


def detalhe_mensal(db: Session, empresa_id: int, item_id: int) -> dict | None:
    """Histórico mensal do item (meses sem consumo = 0, até a referência comum),
    as previsões do modelo ativo e o algoritmo escolhido para ele, com as
    métricas da validação. ``None`` se o item não tem consumo na empresa."""
    linhas = (
        db.query(ConsumoTratado.periodo, func.sum(ConsumoTratado.quantidade_total))
        .filter(ConsumoTratado.empresa_id == empresa_id, ConsumoTratado.item_id == item_id)
        .group_by(ConsumoTratado.periodo)
        .all()
    )
    if not linhas:
        return None
    por_mes = {periodo.replace(day=1): float(qtd) for periodo, qtd in linhas}
    fim = max(max(por_mes), periodo_referencia(db, empresa_id) or max(por_mes))
    historico = []
    atual = min(por_mes)
    while atual <= fim:
        historico.append({"periodo": atual, "quantidade": por_mes.get(atual, 0.0)})
        atual += relativedelta(months=1)

    modelo = (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.empresa_id == empresa_id, ModeloTreinado.ativo.is_(True))
        .first()
    )
    previsoes: list[Previsao] = []
    algoritmo = None
    metricas: dict = {}
    if modelo is not None:
        previsoes = (
            db.query(Previsao)
            .filter(
                Previsao.empresa_id == empresa_id,
                Previsao.modelo_id == modelo.id,
                Previsao.item_id == item_id,
            )
            .order_by(Previsao.periodo)
            .limit(HORIZONTE_PADRAO)
            .all()
        )
        if previsoes:
            algoritmo = algoritmo_do_item(modelo, item_id)
            metricas = (modelo.parametros or {}).get("itens", {}).get(str(item_id)) or {}

    return {
        "item_id": item_id,
        "algoritmo": algoritmo,
        "mae": metricas.get("mae"),
        "rmse": metricas.get("rmse"),
        "mape": metricas.get("mape"),
        "historico": historico,
        "previsoes": previsoes,
    }


def resumo_mensal(db: Session, empresa_id: int) -> dict:
    """Previsões do modelo ativo agrupadas por item (o horizonte inteiro, em ordem),
    com o algoritmo escolhido e o erro da validação de cada um, e a referência
    (último mês com dados, a partir do qual as previsões começam)."""
    referencia = periodo_referencia(db, empresa_id)
    modelo = (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.empresa_id == empresa_id, ModeloTreinado.ativo.is_(True))
        .first()
    )
    if modelo is None:
        return {"referencia": referencia, "treinado_em": None, "itens": []}

    metricas = (modelo.parametros or {}).get("itens", {})
    por_item: dict[int, list[Previsao]] = {}
    for previsao in (
        db.query(Previsao)
        .filter(Previsao.empresa_id == empresa_id, Previsao.modelo_id == modelo.id)
        .order_by(Previsao.item_id, Previsao.periodo)
    ):
        por_item.setdefault(previsao.item_id, []).append(previsao)

    itens = []
    for item_id, previsoes in por_item.items():
        # Só o horizonte atual (um modelo treinado antes pode ter gravado mais meses).
        previsoes = previsoes[:HORIZONTE_PADRAO]
        info = metricas.get(str(item_id)) or {}
        itens.append({
            "item_id": item_id,
            "algoritmo": algoritmo_do_item(modelo, item_id),
            "mae": info.get("mae"),
            "mape": info.get("mape"),
            "previsoes": previsoes,
            "total": sum(p.quantidade_prevista for p in previsoes),
        })
    return {"referencia": referencia, "treinado_em": modelo.treinado_em, "itens": itens}
