from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: Literal["admin", "usuario"]


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    perfil: Optional[Literal["admin", "usuario"]] = None
    ativo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool

    model_config = {"from_attributes": True}
