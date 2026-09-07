from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.comuns import Pagina
from app.schemas.item_schemas import ItemDetalheResponse, ItemResponse
from app.services import consulta_service

router = APIRouter(prefix="/itens", tags=["Itens"])


@router.get("/", response_model=Pagina[ItemResponse])
def listar(
    busca: str | None = Query(None),
    classe_abc: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return consulta_service.listar_itens(
        db,
        current_user.empresa_id,
        busca=busca,
        classe_abc=classe_abc,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/{item_id}", response_model=ItemDetalheResponse)
def detalhe(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    item = consulta_service.obter_item(db, current_user.empresa_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    resposta = ItemDetalheResponse.model_validate(item)
    resposta.classe_abc = consulta_service.classe_abc_do_item(
        db, current_user.empresa_id, item_id
    )
    resposta.meses_de_historico = consulta_service.contar_meses_de_historico(
        db, current_user.empresa_id, item_id
    )
    return resposta
