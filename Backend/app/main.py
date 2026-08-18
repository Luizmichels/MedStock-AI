import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine
import app.models  # noqa: F401 — registra todos os modelos no metadata
from app.database import Base

from app.routers import (
    auth_routers,
    usuarios_routers,
    empresas_routers,
    feriados_routers,
    importacoes_routers,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="MedStock AI",
    version="1.0.0",
    description="API de análise preditiva de consumo de insumos hospitalares.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrinja para o domínio do front em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def handler_generico(request: Request, exc: Exception):
    logging.getLogger(__name__).error("Exceção não tratada: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    from app.core.super_user import super_admin
    super_admin()

app.include_router(auth_routers.router)
app.include_router(usuarios_routers.router)
app.include_router(empresas_routers.router)
app.include_router(feriados_routers.router)
app.include_router(importacoes_routers.router)

@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}