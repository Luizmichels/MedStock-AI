"""Schemas de itens (RF03)."""

from pydantic import BaseModel


class ItemResponse(BaseModel):
    id: int
    codigo_item: str
    descricao_item: str
    unidade_medida: str | None = None
    grupo_material: str | None = None
    subgrupo_material: str | None = None
    classe_material: str | None = None
    ativo: bool
    classe_abc: str | None = None

    model_config = {"from_attributes": True}


class ItemDetalheResponse(ItemResponse):
    meses_de_historico: int = 0
