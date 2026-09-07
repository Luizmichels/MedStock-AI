"""Montagem dos DataFrames dos relatórios (camada pura, testável) — RF10.

Cada função devolve um ``pd.DataFrame`` já com as colunas em português prontas
para o PDF/Excel. Sempre filtra por ``empresa_id`` (isolamento).
"""

from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao

COLUNAS_PREVISOES = [
    "Código", "Descrição", "Período", "Quantidade Prevista",
    "Intervalo Inferior", "Intervalo Superior",
]
COLUNAS_CONSUMO = ["Código", "Descrição", "Período", "Quantidade", "Valor"]
COLUNAS_METRICAS = ["Algoritmo", "RMSE", "MAE", "MAPE", "Ativo", "Treinado em"]


def montar_relatorio_previsoes(
    db: Session,
    empresa_id: int,
    *,
    item_id: int | None = None,
    periodo_inicio: date | None = None,
    periodo_fim: date | None = None,
) -> pd.DataFrame:
    query = (
        db.query(
            Item.codigo_item, Item.descricao_item, Previsao.periodo,
            Previsao.quantidade_prevista, Previsao.intervalo_inferior,
            Previsao.intervalo_superior,
        )
        .join(Item, Item.id == Previsao.item_id)
        .filter(Previsao.empresa_id == empresa_id)
    )
    if item_id is not None:
        query = query.filter(Previsao.item_id == item_id)
    if periodo_inicio is not None:
        query = query.filter(Previsao.periodo >= periodo_inicio)
    if periodo_fim is not None:
        query = query.filter(Previsao.periodo <= periodo_fim)

    linhas = query.order_by(Item.codigo_item, Previsao.periodo).all()
    return pd.DataFrame(linhas, columns=COLUNAS_PREVISOES)


def montar_relatorio_consumo(
    db: Session,
    empresa_id: int,
    *,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> pd.DataFrame:
    query = (
        db.query(
            Item.codigo_item, Item.descricao_item, ConsumoTratado.periodo,
            ConsumoTratado.quantidade_total, ConsumoTratado.valor_total,
        )
        .join(Item, Item.id == ConsumoTratado.item_id)
        .filter(ConsumoTratado.empresa_id == empresa_id)
    )
    if data_inicio is not None:
        query = query.filter(ConsumoTratado.periodo >= data_inicio)
    if data_fim is not None:
        query = query.filter(ConsumoTratado.periodo <= data_fim)

    linhas = query.order_by(Item.codigo_item, ConsumoTratado.periodo).all()
    return pd.DataFrame(linhas, columns=COLUNAS_CONSUMO)


def montar_relatorio_metricas(db: Session, empresa_id: int) -> pd.DataFrame:
    linhas = (
        db.query(
            ModeloTreinado.algoritmo, ModeloTreinado.rmse, ModeloTreinado.mae,
            ModeloTreinado.mape, ModeloTreinado.ativo, ModeloTreinado.treinado_em,
        )
        .filter(ModeloTreinado.empresa_id == empresa_id)
        .order_by(ModeloTreinado.treinado_em.desc())
        .all()
    )
    return pd.DataFrame(linhas, columns=COLUNAS_METRICAS)
