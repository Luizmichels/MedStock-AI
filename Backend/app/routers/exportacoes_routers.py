from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.exportacao import dados
from app.services.exportacao.excel import gerar_xlsx
from app.services.exportacao.pdf import gerar_pdf

router = APIRouter(prefix="/exportacoes", tags=["Exportações"])

_MEDIA_PDF = "application/pdf"
_MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _validar_formato(formato: str) -> None:
    if formato not in ("pdf", "xlsx"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use 'pdf' ou 'xlsx'.")


def _resposta_arquivo(conteudo: bytes, nome: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


def _exportar(df, formato: str, titulo: str, nome_base: str, aba: str) -> StreamingResponse:
    if formato == "pdf":
        return _resposta_arquivo(gerar_pdf(df, titulo), f"{nome_base}.pdf", _MEDIA_PDF)
    return _resposta_arquivo(gerar_xlsx({aba: df}), f"{nome_base}.xlsx", _MEDIA_XLSX)


@router.get("/previsoes")
def exportar_previsoes(
    formato: str = Query("pdf"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _validar_formato(formato)
    df = dados.montar_relatorio_previsoes(db, current_user.empresa_id)
    return _exportar(df, formato, "Relatório de Previsões", "previsoes", "Previsões")


@router.get("/consumo")
def exportar_consumo(
    formato: str = Query("pdf"),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _validar_formato(formato)
    df = dados.montar_relatorio_consumo(
        db, current_user.empresa_id, data_inicio=data_inicio, data_fim=data_fim
    )
    return _exportar(df, formato, "Relatório de Consumo", "consumo", "Consumo")


@router.get("/metricas")
def exportar_metricas(
    formato: str = Query("pdf"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _validar_formato(formato)
    df = dados.montar_relatorio_metricas(db, current_user.empresa_id)
    return _exportar(df, formato, "Métricas dos Modelos", "metricas", "Métricas")
