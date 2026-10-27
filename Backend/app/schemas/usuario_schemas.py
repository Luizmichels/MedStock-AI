from pydantic import BaseModel, EmailStr, Field
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


class MeuPerfilUpdate(BaseModel):
    """Dados que o próprio usuário pode alterar. Trocar o e-mail exige a senha atual."""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    senha_atual: Optional[str] = None


class TrocarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=128)


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool

    model_config = {"from_attributes": True}
