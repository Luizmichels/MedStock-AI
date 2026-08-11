from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.database import get_db
from app.models.usuario import Usuario
from app.core.config import settings

bearer_scheme = HTTPBearer()

def _decodificar_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    payload = _decodificar_token(credentials)
    usuario_id = payload.get("sub")
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Token sem identificação de usuário")

    usuario = db.query(Usuario).filter(
        Usuario.id == int(usuario_id), Usuario.ativo == True
    ).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return usuario

def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.perfil != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem realizar esta ação",
        )
    return current_user

def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    payload = _decodificar_token(credentials)
    if payload.get("perfil") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Super Admin",
        )
    return payload
