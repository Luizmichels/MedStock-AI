"""Schemas da previsão diária."""

from datetime import date

from pydantic import BaseModel


class ResumoDiarioItem(BaseModel):
    item_id: int
    metodo: str
    base: date
    proximo_dia: float
    sete_dias: float
    quinze_dias: float
    trinta_dias: float


class PontoDiario(BaseModel):
    data: date
    quantidade_prevista: float


class HorizontesDiarios(BaseModel):
    proximo_dia: float
    sete_dias: float
    quinze_dias: float
    trinta_dias: float


class PrevisaoDiariaDetalhe(BaseModel):
    item_id: int
    metodo: str
    base: date
    horizontes: HorizontesDiarios
    dias: list[PontoDiario]
