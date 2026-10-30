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


class PontoHistoricoMensal(BaseModel):
    periodo: date
    quantidade: float


class PrevisaoMensalDetalhe(BaseModel):
    """Histórico e previsão mensal de um item, com o algoritmo escolhido para ele
    no treino e as métricas da validação walk-forward."""

    item_id: int
    algoritmo: str | None = None
    mae: float | None = None
    rmse: float | None = None
    mape: float | None = None
    historico: list[PontoHistoricoMensal]
    previsoes: list[PrevisaoResponse]


class ResumoPrevisaoItem(BaseModel):
    item_id: int
    algoritmo: str
    mae: float | None = None
    mape: float | None = None
    previsoes: list[PrevisaoResponse]  # os meses do horizonte, em ordem
    total: float


class ResumoPrevisoesResponse(BaseModel):
    """Previsões mensais do modelo ativo, uma entrada por item."""

    referencia: date | None = None  # último mês com dados; a previsão começa no seguinte
    treinado_em: datetime | None = None
    itens: list[ResumoPrevisaoItem]


class ItemOmitidoResponse(BaseModel):
    item_id: int
    meses_disponiveis: int
    motivo: str


class StatusTreinoResponse(BaseModel):
    em_andamento: bool
    ultimo_modelo: ModeloTreinadoResponse | None = None
