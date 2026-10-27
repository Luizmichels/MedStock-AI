"""Schemas do dashboard (RF09, RF12)."""

from datetime import date, datetime

from pydantic import BaseModel


class KpisResponse(BaseModel):
    total_itens_ativos: int
    valor_total_consumido: float
    numero_importacoes: int
    itens_classe_a: int
    # % do valor consumido (todo o histórico) de itens que têm previsão diária gerada.
    cobertura_previsao: float


class PontoMensal(BaseModel):
    periodo: date
    quantidade_total: float
    valor_total: float


class CoberturaPrevisao(BaseModel):
    """Quanto do consumo (no filtro) está coberto por previsão diária gerada."""

    itens_consumidos: int
    itens_com_previsao: int
    valor_total: float
    valor_coberto: float
    percentual_valor: float  # meta: 80%
    percentual_itens: float


class PrevisaoProximosDias(BaseModel):
    """Soma da previsão diária dos próximos ``dias`` para os materiais do filtro."""

    dias: int
    quantidade_prevista: float
    # Quantidade prevista x preço médio histórico de cada material.
    valor_estimado: float
    itens_com_previsao: int
    base: date | None = None  # último dia com dados (a previsão começa no dia seguinte)


class ConsumoSetor(BaseModel):
    setor: str | None
    quantidade_total: float
    valor_total: float


class HierarquiaMaterial(BaseModel):
    """Uma combinação existente de grupo / subgrupo / classe do material."""

    grupo_material: str | None
    subgrupo_material: str | None
    classe_material: str | None


class MaterialFiltro(BaseModel):
    """Material com seus atributos, para o filtro em cascata no front."""

    id: int
    codigo_item: str
    descricao_item: str
    grupo_material: str | None
    subgrupo_material: str | None
    classe_material: str | None


class OpcoesFiltroResponse(BaseModel):
    """Valores disponíveis para os filtros do dashboard e das previsões."""

    hierarquia: list[HierarquiaMaterial]
    materiais: list[MaterialFiltro] = []
    setores: list[str]
    periodo_inicio: date | None = None
    periodo_fim: date | None = None


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
