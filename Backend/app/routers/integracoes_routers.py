"""Integração via API: o sistema do hospital envia o consumo sem login.

- Gestão da chave (admin logado, JWT): consultar, gerar e revogar.
- Envio de consumo (sistema do hospital, cabeçalho ``X-API-Key``): sempre
  incremental, em lotes de até 15.000 registros, processado em segundo plano.
  A carga completa (substituir a base) continua sendo feita pelo arquivo.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import require_admin
from app.models.chave_integracao import ChaveIntegracao
from app.models.importacoes import Importacao
from app.models.usuario import Usuario
from app.schemas.importacao_schemas import ImportacaoResponse
from app.schemas.integracao_schemas import (
    ChaveIntegracaoGerada,
    ChaveIntegracaoStatus,
    EnvioConsumosApi,
)
from app.services import integracao_service
from app.services.abc_service import recalcular_abc
from app.services.data_pipeline_service import (
    criar_importacao_processando,
    dataframe_de_registros,
    executar_pipeline,
)

router = APIRouter(prefix="/integracoes", tags=["Integração via API"])


def chave_da_requisicao(
    x_api_key: str | None = Header(None, description="Chave de integração do hospital"),
    db: Session = Depends(get_db),
) -> ChaveIntegracao:
    return integracao_service.autenticar(db, x_api_key)


# --------------------------------------------------------------------------- #
# Gestão da chave (tela "Importar dados")
# --------------------------------------------------------------------------- #
@router.get("/chave", response_model=ChaveIntegracaoStatus | None)
def consultar_chave(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Chave ativa do hospital (só o prefixo), ou null se não houver."""
    return integracao_service.chave_ativa(db, current_user.empresa_id)


@router.post("/chave", response_model=ChaveIntegracaoGerada, status_code=201)
def gerar_chave(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    """Gera uma nova chave. A anterior para de funcionar imediatamente.
    A chave completa só é devolvida nesta resposta."""
    texto, registro = integracao_service.gerar_chave(db, current_user.empresa_id, current_user.id)
    return ChaveIntegracaoGerada(
        chave=texto,
        prefixo=registro.prefixo,
        criado_em=registro.criado_em,
        ultimo_uso_em=registro.ultimo_uso_em,
    )


@router.delete("/chave", status_code=204)
def revogar_chave(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    if not integracao_service.revogar_chave(db, current_user.empresa_id):
        raise HTTPException(status_code=404, detail="Não há chave de integração ativa.")
    return Response(status_code=204)


# --------------------------------------------------------------------------- #
# Envio de consumo pelo sistema do hospital
# --------------------------------------------------------------------------- #
def _processar_envio_background(importacao_id: int, registros: list[dict], empresa_id: int) -> None:
    db = SessionLocal()
    try:
        importacao = db.query(Importacao).filter(Importacao.id == importacao_id).first()
        if importacao is None:  # pragma: no cover - defensivo
            return
        executar_pipeline(
            db, importacao, b"", importacao.nome_arquivo, empresa_id,
            blocos=[dataframe_de_registros(registros)],
        )
        if importacao.status == "concluido" and importacao.registros_validos > 0:
            recalcular_abc(db, empresa_id)
    finally:
        db.close()


@router.post("/consumos", response_model=ImportacaoResponse, status_code=202)
def enviar_consumos(
    envio: EnvioConsumosApi,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    chave: ChaveIntegracao = Depends(chave_da_requisicao),
):
    """Recebe até 15.000 registros de consumo e os processa em segundo plano.

    Responde 202 com a importação criada; acompanhe o resultado (linhas válidas,
    inválidas e erros) em ``GET /integracoes/importacoes/{id}``."""
    registros = [r.model_dump() for r in envio.registros]
    importacao = criar_importacao_processando(
        db,
        f"API · {len(registros)} registros",
        chave.empresa_id,
        chave.criado_por,
        modo="incremental",
        tipo="api",
    )
    tarefas.add_task(_processar_envio_background, importacao.id, registros, chave.empresa_id)
    return importacao


@router.get("/importacoes/{importacao_id}", response_model=ImportacaoResponse)
def status_envio(
    importacao_id: int,
    db: Session = Depends(get_db),
    chave: ChaveIntegracao = Depends(chave_da_requisicao),
):
    importacao = (
        db.query(Importacao)
        .filter(Importacao.id == importacao_id, Importacao.empresa_id == chave.empresa_id)
        .first()
    )
    if importacao is None:
        raise HTTPException(status_code=404, detail="Importação não encontrada.")
    return importacao
