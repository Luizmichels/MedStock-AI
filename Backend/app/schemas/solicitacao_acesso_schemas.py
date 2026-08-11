from pydantic import BaseModel, EmailStr
from typing import Literal
from datetime import datetime


class SolicitacaoCreate(BaseModel):
    nome_responsavel: str
    email: EmailStr
    nome_hospital: str
    endereco: str
    uf: str
    cidade: str


class SolicitacaoAtualizarStatus(BaseModel):
    status: Literal["aprovado", "rejeitado"]


class SolicitacaoResponse(BaseModel):
    id: int
    nome_responsavel: str
    email: str
    nome_hospital: str
    endereco: str
    uf: str
    cidade: str
    status: str
    criado_em: datetime

    model_config = {"from_attributes": True}
