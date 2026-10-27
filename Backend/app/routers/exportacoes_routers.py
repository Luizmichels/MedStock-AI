from datetime import date, datetime, timedelta, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.exportacao import dados
from app.services.exportacao.dados import Relatorio
from app.services.exportacao.excel import gerar_xlsx
from app.services.exportacao.pdf import ContextoExportacao, gerar_pdf

router = APIRouter(prefix="/exportacoes", tags=["Exportações"])

_MEDIA_PDF = "application/pdf"
_MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Horário de Brasília (sem horário de verão desde 2019) para o "gerado em".
_FUSO_BRASILIA = timezone(timedelta(hours=-3))


def _validar_formato(formato: str) -> None:
    if formato not in ("pdf", "xlsx"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use 'pdf' ou 'xlsx'.")


def _resposta_arquivo(conteudo: bytes, nome: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


def _contexto(usuario: Usuario) -> ContextoExportacao:
    return ContextoExportacao(
        hospital=usuario.empresa.nome if usuario.empresa else "—",
        usuario=usuario.nome,
        gerado_em=datetime.now(_FUSO_BRASILIA),
    )


def _exportar(
    relatorio: Relatorio, formato: str, nome_base: str, usuario: Usuario
) -> StreamingResponse:
    contexto = _contexto(usuario)
    nome = f"{nome_base}_{contexto.gerado_em:%Y-%m-%d}"
    if formato == "pdf":
        return _resposta_arquivo(gerar_pdf(relatorio, contexto), f"{nome}.pdf", _MEDIA_PDF)
    return _resposta_arquivo(gerar_xlsx(relatorio, contexto), f"{nome}.xlsx", _MEDIA_XLSX)


@router.get("/previsoes")
def exportar_previsoes(
    formato: str = Query("pdf"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Previsão diária por material (próximos 7, 15 e 30 dias)."""
    _validar_formato(formato)
    relatorio = dados.montar_relatorio_previsoes(db, current_user.empresa_id)
    return _exportar(relatorio, formato, "previsoes", current_user)


@router.get("/consumo")
def exportar_consumo(
    formato: str = Query("pdf"),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Consumo do período resumido por material e por setor (Excel: + detalhe mensal)."""
    _validar_formato(formato)
    relatorio = dados.montar_relatorio_consumo(
        db, current_user.empresa_id, data_inicio=data_inicio, data_fim=data_fim
    )
    return _exportar(relatorio, formato, "consumo", current_user)
