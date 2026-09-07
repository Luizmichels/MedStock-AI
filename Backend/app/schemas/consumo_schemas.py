"""Schemas de consumos e séries temporais (RF03)."""

from datetime import date

from pydantic import BaseModel


class ConsumoResponse(BaseModel):
    id: int
    item_id: int
    data: date
    quantidade: float
    valor: float
    local_estoque: str | None = None

    model_config = {"from_attributes": True}


class PontoSerie(BaseModel):
    """Um ponto da série mensal agregada de um item (base dos gráficos)."""

    periodo: date
    quantidade_total: float
    valor_total: float
