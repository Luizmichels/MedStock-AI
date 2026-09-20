"""Fluxos de senha: redefinição ("esqueci minha senha") e reenvio de ativação.

As rotas devolvem sempre uma mensagem genérica para não permitir enumeração de
e-mails cadastrados; o envio efetivo acontece só quando o usuário existe.
"""

import logging

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import criar_token, hash_senha
from app.models.usuario import Usuario
from app.services.email_service import enviar_email, montar_email_definicao_senha

logger = logging.getLogger(__name__)


def _link(token: str, caminho: str) -> str:
    return f"{settings.FRONTEND_URL}/{caminho}?token={token}"


def solicitar_redefinicao_senha(db: Session, email: str) -> None:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email, Usuario.ativo == True)  # noqa: E712
        .first()
    )
    if not usuario:
        return
    token = criar_token(
        {
            "sub": str(usuario.id),
            "tipo": "redefinir_senha",
            "v": usuario.senha_hash[:10],
        },
        expires_minutes=settings.DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES,
    )
    texto, html = montar_email_definicao_senha(usuario.nome, _link(token, "redefinir-senha"))
    enviar_email(usuario.email, "Redefinição de senha - MedStock AI", texto, html)


def redefinir_senha(db: Session, token: str, nova_senha: str) -> None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    if payload.get("tipo") != "redefinir_senha":
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    usuario = db.query(Usuario).filter(Usuario.id == int(payload["sub"])).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    versao = payload.get("v")
    if versao and versao != usuario.senha_hash[:10]:
        raise HTTPException(
            status_code=401, detail="Token já utilizado ou expirado. Solicite uma nova redefinição."
        )

    usuario.senha_hash = hash_senha(nova_senha)
    db.commit()


def reenviar_ativacao(db: Session, email: str) -> None:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email, Usuario.ativo == False)  # noqa: E712
        .first()
    )
    if not usuario:
        return
    token = criar_token(
        {"sub": str(usuario.id), "tipo": "definir_senha"},
        expires_minutes=settings.DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES,
    )
    texto, html = montar_email_definicao_senha(usuario.nome, _link(token, "definir-senha"))
    enviar_email(usuario.email, "Ative sua conta - MedStock AI", texto, html)
