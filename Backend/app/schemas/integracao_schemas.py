"""Schemas da integração via API (envio de consumo pelo sistema do hospital)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

# Mesmo tamanho do lote da importação por arquivo.
MAX_REGISTROS_POR_ENVIO = 15_000


class RegistroConsumoApi(BaseModel):
    """Uma linha de consumo — os mesmos campos do arquivo CSV."""

    codigo_item: str = Field(min_length=1, max_length=100)
    descricao_item: str = Field(min_length=1, max_length=500)
    data: date
    quantidade: float
    valor: float
    setor: str = Field(min_length=1, max_length=255)
    unidade_medida: str | None = None
    grupo_material: str | None = None
    subgrupo_material: str | None = None
    classe_material: str | None = None


class EnvioConsumosApi(BaseModel):
    registros: list[RegistroConsumoApi] = Field(min_length=1, max_length=MAX_REGISTROS_POR_ENVIO)


class ChaveIntegracaoStatus(BaseModel):
    prefixo: str
    criado_em: datetime
    ultimo_uso_em: datetime | None = None

    model_config = {"from_attributes": True}


class ChaveIntegracaoGerada(ChaveIntegracaoStatus):
    """Resposta da geração: a chave completa só aparece aqui, uma única vez."""

    chave: str
