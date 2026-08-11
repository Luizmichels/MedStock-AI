import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha: str, senha_hashed: str) -> bool:
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hashed.encode('utf-8'))

def criar_token(data: dict, expires_minutes: int | None = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)