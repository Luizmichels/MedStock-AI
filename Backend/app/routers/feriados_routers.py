from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.feriado_schemas import FeriadoResponse
from app.services import feriados_service

router = APIRouter(prefix="/feriados", tags=["Feriados"])


@router.get("/", response_model=list[FeriadoResponse])
def listar(
    ano: int = date.today().year,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresa = current_user.empresa
    return feriados_service.obter_feriados(db, empresa.uf, empresa.cidade, ano)
