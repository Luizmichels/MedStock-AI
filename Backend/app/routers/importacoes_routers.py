import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.importacoes import Importacao
from app.models.usuario import Usuario
from app.schemas.importacao_schemas import ImportacaoResponse
from app.services.data_pipeline_service import processar_arquivo
from app.services.abc_service import recalcular_abc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importacoes", tags=["Importações"])

TAMANHO_MAXIMO_BYTES = 50 * 1024 * 1024  # 50 MB
EXTENSOES_PERMITIDAS = {"csv", "xls", "xlsx"}


@router.post("/upload", response_model=ImportacaoResponse, status_code=201)
async def upload(
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

    importacao = processar_arquivo(
        db=db,
        conteudo=conteudo,
        nome_arquivo=arquivo.filename,
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
    )

    if importacao.status == "concluido" and importacao.registros_validos > 0:
        recalcular_abc(db, current_user.empresa_id)

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
