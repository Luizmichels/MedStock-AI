import logging
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, require_admin
from app.models.importacoes import Importacao
from app.models.usuario import Usuario
from app.schemas.importacao_schemas import ImportacaoResponse
from app.services.data_pipeline_service import criar_importacao_processando, executar_pipeline
from app.services.abc_service import recalcular_abc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importacoes", tags=["Importações"])

TAMANHO_MAXIMO_BYTES = 50 * 1024 * 1024  # 50 MB
EXTENSOES_PERMITIDAS = {"csv", "xls", "xlsx"}


def _processar_importacao_background(
    importacao_id: int, conteudo: bytes, nome_arquivo: str, empresa_id: int
) -> None:
    """Executa o pipeline fora do request (RNF01/RNF02), com sessão própria."""
    db = SessionLocal()
    try:
        importacao = db.query(Importacao).filter(Importacao.id == importacao_id).first()
        if importacao is None:  # pragma: no cover - defensivo
            return
        executar_pipeline(db, importacao, conteudo, nome_arquivo, empresa_id)
        if importacao.status == "concluido" and importacao.registros_validos > 0:
            recalcular_abc(db, empresa_id)
    finally:
        db.close()


@router.post("/upload", response_model=ImportacaoResponse, status_code=202)
async def upload(
    tarefas: BackgroundTasks,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    extensao = arquivo.filename.rsplit(".", 1)[-1].lower() if arquivo.filename else ""
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: .{extensao}. Use CSV ou Excel (.xls, .xlsx).",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 50 MB.")

    importacao = criar_importacao_processando(
        db, arquivo.filename, current_user.empresa_id, current_user.id
    )
    tarefas.add_task(
        _processar_importacao_background,
        importacao.id, conteudo, arquivo.filename, current_user.empresa_id,
    )
    return importacao


@router.get("/", response_model=list[ImportacaoResponse])
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return (
        db.query(Importacao)
        .filter(Importacao.empresa_id == current_user.empresa_id)
        .order_by(Importacao.criado_em.desc())
        .all()
    )


@router.get("/{importacao_id}", response_model=ImportacaoResponse)
def detalhe(
    importacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    importacao = db.query(Importacao).filter(
        Importacao.id == importacao_id,
        Importacao.empresa_id == current_user.empresa_id,
    ).first()
    if not importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return importacao
