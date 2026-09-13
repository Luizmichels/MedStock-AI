"""Schemas comuns reutilizados entre módulos (ex.: paginação)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    """Envelope de resposta paginada."""

    itens: list[T]
    total: int
    pagina: int
    tamanho: int
