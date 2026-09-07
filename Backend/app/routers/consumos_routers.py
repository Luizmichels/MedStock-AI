from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.comuns import Pagina
from app.schemas.consumo_schemas import ConsumoResponse, PontoSerie
from app.services import consulta_service

router = APIRouter(prefix="/consumos", tags=["Consumos"])


@router.get("/", response_model=Pagina[ConsumoResponse])
def listar(
    item_id: int | None = Query(None),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    local: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return consulta_service.listar_consumos(
        db,
        current_user.empresa_id,
        item_id=item_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        local=local,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/serie/{item_id}", response_model=list[PontoSerie])
def serie_temporal(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return consulta_service.obter_serie_temporal(db, current_user.empresa_id, item_id)
