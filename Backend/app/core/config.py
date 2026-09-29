# Lê as variáveis do .env e as disponibiliza o projeto
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Ambiente de execução: "desenvolvimento" | "producao". Rotas de conveniência
    # para testes (ex.: /importacoes/upload-teste) só respondem fora de produção.
    AMBIENTE: str = "desenvolvimento"
    # Tamanho máximo (MB) aceito no upload de importação. Default conservador
    # para produção; em desenvolvimento pode ser elevado via .env.
    UPLOAD_MAX_MB: int = 50
    DATABASE_URL: str
    # Banco usado pela suíte de testes. Se ausente, o conftest cai para SQLite
    # em memória; defina para um Postgres real no CI para fidelidade de produção.
    TEST_DATABASE_URL: str | None = None
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES: int = 2880
    FRONTEND_URL: str = "http://localhost:3000"
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
