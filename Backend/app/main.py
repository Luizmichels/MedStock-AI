import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
import app.models  # noqa: F401 — registra todos os modelos no metadata
from app.database import Base, engine, get_db

from app.routers import (
    auth_routers,
    usuarios_routers,
    empresas_routers,
    importacoes_routers,
    integracoes_routers,
    itens_routers,
    consumos_routers,
    previsoes_routers,
    dashboard_routers,
    exportacoes_routers,
)

#teste pr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # O schema é gerenciado por migrações Alembic (`alembic upgrade head`).
    # O create_all abaixo é uma rede de segurança para ambientes sem migração.
    Base.metadata.create_all(bind=engine)
    from app.core.super_user import super_admin
    super_admin()
    yield


app = FastAPI(
    title="MedStock AI",
    version="1.0.0",
    description="API de análise preditiva de consumo de insumos hospitalares.",
    lifespan=lifespan,
)

# CORS: o front configurado + extras do .env. Fora de produção também aceita o
# front aberto por localhost, 127.0.0.1 ou IP da rede local (o "Network" do Next),
# em qualquer porta — senão o preflight (OPTIONS) do navegador volta 400.
_ORIGENS_CORS = [settings.FRONTEND_URL] + [
    o.strip() for o in settings.CORS_ORIGINS_EXTRAS.split(",") if o.strip()
]
_REGEX_CORS_DEV = (
    r"https?://(localhost|127\.0\.0\.1|\[::1\]|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGENS_CORS,
    allow_origin_regex=None if settings.AMBIENTE == "producao" else _REGEX_CORS_DEV,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def handler_generico(request: Request, exc: Exception):
    logging.getLogger(__name__).error("Exceção não tratada: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


app.include_router(auth_routers.router)
app.include_router(usuarios_routers.router)
app.include_router(empresas_routers.router)
app.include_router(importacoes_routers.router)
app.include_router(integracoes_routers.router)
app.include_router(itens_routers.router)
app.include_router(consumos_routers.router)
app.include_router(previsoes_routers.router)
app.include_router(dashboard_routers.router)
app.include_router(exportacoes_routers.router)

@app.get("/health", tags=["Sistema"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logging.getLogger(__name__).exception(
            "Falha na conexão com o banco de dados durante o health check"
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
        "database": "ok",
    }
    