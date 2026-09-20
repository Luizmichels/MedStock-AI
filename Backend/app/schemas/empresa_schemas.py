from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

from app.core.validadores import cnpj_valido

class EmpresaCreate(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    email_responsavel: EmailStr
    nome_responsavel: str
    endereco: str
    cidade: str
    uf: str

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, valor: Optional[str]) -> Optional[str]:
        if valor is not None and not cnpj_valido(valor):
            raise ValueError("CNPJ inválido.")
        return valor


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    email_responsavel: Optional[EmailStr] = None
    nome_responsavel: Optional[str] = None
    ativa: Optional[bool] = None
    endereco: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, valor: Optional[str]) -> Optional[str]:
        if valor is not None and not cnpj_valido(valor):
            raise ValueError("CNPJ inválido.")
        return valor


class EmpresaResponse(BaseModel):
    id: int
    nome: str
    cnpj: Optional[str]
    email_responsavel: str
    nome_responsavel: str
    ativa: bool
    endereco: str
    uf: str
    cidade: str
    criado_em: datetime

    model_config = {"from_attributes": True}
