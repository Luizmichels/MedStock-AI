"""Schemas de modelos treinados e previsões (RF06, RF07, RF08, FA03)."""

from datetime import date, datetime

from pydantic import BaseModel


class ModeloTreinadoResponse(BaseModel):
    id: int
    algoritmo: str
    rmse: float | None = None
    mae: float | None = None
    mape: float | None = None
    ativo: bool
    treinado_em: datetime

    model_config = {"from_attributes": True}


class PrevisaoResponse(BaseModel):
    id: int
    item_id: int
    modelo_id: int
    periodo: date
    quantidade_prevista: float
    intervalo_inferior: float | None = None
    intervalo_superior: float | None = None

    model_config = {"from_attributes": True}


class ItemOmitidoResponse(BaseModel):
    item_id: int
    meses_disponiveis: int
    motivo: str


class StatusTreinoResponse(BaseModel):
    em_andamento: bool
    ultimo_modelo: ModeloTreinadoResponse | None = None
