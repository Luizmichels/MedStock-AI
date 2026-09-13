"""Geração de previsões multi-step e persistência (RF08, RN06).

Usa o algoritmo do modelo ativo para projetar ``horizonte`` meses à frente para
cada item elegível, de forma recursiva, com um intervalo simples de incerteza.
"""

from __future__ import annotations

from typing import Callable

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.services.ml.elegibilidade import separar_elegiveis
from app.services.ml.estimadores import ALGORITMOS, Estimador, criar
from app.services.ml.treinamento import (
    carregar_series_por_item,
    ultimo_periodo_por_item,
)

HORIZONTE_PADRAO = 6
# Largura do intervalo de incerteza (±20%) — heurística simples e transparente.
_MARGEM_INTERVALO = 0.20


def _algoritmo_do_item(modelo: ModeloTreinado, item_id: int) -> str:
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

    # Regeneração completa: descarta as previsões anteriores da empresa.
    db.query(Previsao).filter(Previsao.empresa_id == empresa_id).delete()

    novas: list[Previsao] = []
    for item_id, serie in elegiveis.items():
        estimador = construir(_algoritmo_do_item(modelo, item_id))
        estimador.fit(serie)
        previsto = estimador.prever(horizonte)

        base = ultimos[item_id]
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
