from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app.models.usuario import Usuario
from app.core.security import verificar_senha, criar_token, hash_senha
from app.core.config import settings
from app.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    DefinirSenhaRequest,
    MensagemResponse,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == body.email, Usuario.ativo == True)
        .first()
    )
    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = criar_token(
        {
            "sub": str(usuario.id),
            "empresa_id": usuario.empresa_id,
            "perfil": usuario.perfil,
        }
    )
    return TokenResponse(access_token=token)


@router.post("/definir-senha", response_model=MensagemResponse)
def definir_senha(body: DefinirSenhaRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    if payload.get("tipo") != "definir_senha":
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    usuario = db.query(Usuario).filter(Usuario.id == int(payload["sub"])).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if usuario.ativo:
        raise HTTPException(
            status_code=400, detail="Conta já ativada. Faça login normalmente."
        )

    usuario.senha_hash = hash_senha(body.senha)
    usuario.ativo = True
    db.commit()
    return MensagemResponse(mensagem="Senha definida com sucesso")
