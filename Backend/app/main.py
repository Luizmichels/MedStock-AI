import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database import engine
import app.models  # noqa: F401 — registra todos os modelos no metadata
from app.database import Base

from app.routers import (
    auth_routers,
    usuarios_routers,
    empresas_routers,
    importacoes_routers,
    itens_routers,
    consumos_routers,
    previsoes_routers,
    dashboard_routers,
    exportacoes_routers,
)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
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
app.include_router(itens_routers.router)
app.include_router(consumos_routers.router)
app.include_router(previsoes_routers.router)
app.include_router(dashboard_routers.router)
app.include_router(exportacoes_routers.router)

@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}