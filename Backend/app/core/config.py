# Lê as variáveis do .env e as disponibiliza o projeto
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Ambiente de execução: "desenvolvimento" | "producao". Rotas de conveniência
    AMBIENTE: str = "desenvolvimento"
    # Versão da imagem gravada no build pelo CD e enviada em cada linha de log, para ligar um erro ao deploy que o causou
    VERSAO: str = "local"
    UPLOAD_MAX_MB: int = 50
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES: int = 2880
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS_EXTRAS: str = ""
    SUPER_ADMIN_EMAIL: str
    SUPER_ADMIN_SENHA: str
    EMAIL_REMETENTE: str
    SENHA_EMAIL: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
