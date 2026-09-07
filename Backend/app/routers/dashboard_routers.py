from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.dashboard_schemas import (
    ConsumoLocal,
    DistribuicaoABC,
    ItemRanking,
    PontoMensal,
    ResumoResponse,
)
from app.services import abc_service, dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumo", response_model=ResumoResponse)
def resumo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresa_id = current_user.empresa_id
    return ResumoResponse(
        possui_dados=dashboard_service.possui_dados(db, empresa_id),
        kpis=dashboard_service.calcular_kpis(db, empresa_id),
        ultima_importacao=dashboard_service.ultima_importacao(db, empresa_id),
    )


@router.get("/consumo-mensal", response_model=list[PontoMensal])
def consumo_mensal(
    meses: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.consumo_mensal(db, current_user.empresa_id, meses=meses)


@router.get("/consumo-por-local", response_model=list[ConsumoLocal])
def consumo_por_local(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.consumo_por_local(db, current_user.empresa_id)


@router.get("/classificacao-abc", response_model=list[DistribuicaoABC])
def classificacao_abc(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.distribuicao_abc(db, current_user.empresa_id)


@router.get("/abc-xyz", response_model=dict[str, int])
def abc_xyz(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Matriz combinada ABC/XYZ (RF05): contagem de itens por classe (ex.: 'AX')."""
    return abc_service.matriz_abc_xyz(db, current_user.empresa_id)


@router.get("/top-itens", response_model=list[ItemRanking])
def top_itens(
    limite: int = Query(10, ge=1, le=50),
    por: str = Query("valor", pattern="^(valor|quantidade)$"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.top_itens(db, current_user.empresa_id, limite=limite, por=por)
