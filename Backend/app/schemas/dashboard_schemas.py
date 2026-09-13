"""Schemas do dashboard (RF09, RF12)."""

from datetime import date, datetime

from pydantic import BaseModel


class KpisResponse(BaseModel):
    total_itens_ativos: int
    valor_total_consumido: float
    numero_importacoes: int
    itens_classe_a: int
    cobertura_previsao: float  # % de itens elegíveis para previsão (meta 80%)


class PontoMensal(BaseModel):
    periodo: date
    quantidade_total: float
    valor_total: float


class ConsumoLocal(BaseModel):
    local_estoque: str | None
    quantidade_total: float
    valor_total: float


class DistribuicaoABC(BaseModel):
    classe: str
    quantidade_itens: int
    valor_total: float


class ItemRanking(BaseModel):
    item_id: int
    codigo_item: str
    descricao_item: str
    quantidade_total: float
    valor_total: float


class ResumoResponse(BaseModel):
    possui_dados: bool
    kpis: KpisResponse
    ultima_importacao: datetime | None = None
