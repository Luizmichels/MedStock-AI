from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.dashboard_schemas import (
    CoberturaPrevisao,
    ConsumoSetor,
    DistribuicaoABC,
    ItemRanking,
    OpcoesFiltroResponse,
    PontoMensal,
    PrevisaoProximoMes,
    ResumoResponse,
)
from app.services import abc_service, dashboard_service
from app.services.dashboard_service import FiltrosDashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def filtros_dashboard(
    data_inicio: date | None = Query(None, description="Competência inicial (AAAA-MM-DD)"),
    data_fim: date | None = Query(None, description="Competência final (AAAA-MM-DD)"),
    item_id: list[int] | None = Query(None, description="Material (pode repetir)"),
    grupo_material: list[str] | None = Query(None, description="Pode repetir"),
    subgrupo_material: list[str] | None = Query(None, description="Pode repetir"),
    classe_material: list[str] | None = Query(None, description="Pode repetir"),
    setor: list[str] | None = Query(None, description="Setor/centro de custo (pode repetir)"),
) -> FiltrosDashboard:
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="A competência inicial é posterior à final.")
    return FiltrosDashboard(
        data_inicio=data_inicio,
        data_fim=data_fim,
        item_ids=item_id or [],
        grupos=grupo_material or [],
        subgrupos=subgrupo_material or [],
        classes=classe_material or [],
        setores=setor or [],
    )


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


@router.get("/opcoes-filtro", response_model=OpcoesFiltroResponse)
def opcoes_filtro(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Grupos/subgrupos/classes do material, setores e o intervalo de competências."""
    return dashboard_service.opcoes_filtro(db, current_user.empresa_id)


@router.get("/consumo-mensal", response_model=list[PontoMensal])
def consumo_mensal(
    meses: int = Query(12, ge=1, le=60),
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.consumo_mensal(
        db, current_user.empresa_id, meses=meses, filtros=filtros
    )


@router.get("/consumo-por-setor", response_model=list[ConsumoSetor])
def consumo_por_setor(
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.consumo_por_setor(db, current_user.empresa_id, filtros)


@router.get("/cobertura-previsao", response_model=CoberturaPrevisao)
def cobertura_previsao(
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Parcela do consumo (no filtro) de itens com previsão do modelo ativo."""
    return dashboard_service.cobertura_previsao(db, current_user.empresa_id, filtros)


@router.get("/previsao-proximo-mes", response_model=PrevisaoProximoMes)
def previsao_proximo_mes(
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Previsão do próximo mês (quantidade e valor estimado) dos materiais do
    filtro. Competência e setor não se aplicam: a previsão é por material."""
    return dashboard_service.previsao_proximo_mes(db, current_user.empresa_id, filtros)


@router.get("/classificacao-abc", response_model=list[DistribuicaoABC])
def classificacao_abc(
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.distribuicao_abc(db, current_user.empresa_id, filtros)


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
    filtros: FiltrosDashboard = Depends(filtros_dashboard),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return dashboard_service.top_itens(
        db, current_user.empresa_id, limite=limite, por=por, filtros=filtros
    )
