from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_super_admin
from app.schemas.empresa_schemas import EmpresaCreate, EmpresaUpdate, EmpresaResponse
from app.schemas.solicitacao_acesso_schemas import (
    SolicitacaoCreate,
    SolicitacaoAtualizarStatus,
    SolicitacaoResponse,
)
from app.services import empresa_service

router = APIRouter(prefix="/empresas", tags=["Empresas"])

# Rotas exclusivas do Super Admin
@router.get("/listar/empresas", response_model=list[EmpresaResponse])
def listar(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.listar_empresas(db)

@router.get("/buscar/empresa/{empresa_id}", response_model=EmpresaResponse)
def buscar(
    empresa_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.buscar_empresa(db, empresa_id)

@router.post("/criar/empresa", response_model=EmpresaResponse, status_code=201)
def criar(
    dados: EmpresaCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.criar_empresa(db, dados)

@router.patch("/atualizar/empresa/{empresa_id}", response_model=EmpresaResponse)
def atualizar(
    empresa_id: int,
    dados: EmpresaUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.atualizar_empresa(db, empresa_id, dados)

@router.patch("/desativar/empresa/{empresa_id}", response_model=EmpresaResponse)
def desativar(
    empresa_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.desativar_empresa(db, empresa_id)

# Solicitação de acesso
@router.post("/enviar/solicitacao",
    response_model=SolicitacaoResponse,
    status_code=201,
    summary="Enviar solicitação de acesso (público)",
)
def solicitar_acesso(dados: SolicitacaoCreate, db: Session = Depends(get_db)):
    return empresa_service.criar_solicitacao(db, dados)

@router.get("/solicitacoes/pendentes", response_model=list[SolicitacaoResponse])
def listar_solicitacoes(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.listar_solicitacoes(db)

@router.patch("/solicitacoes/{solicitacao_id}", response_model=SolicitacaoResponse)
def atualizar_solicitacao(
    solicitacao_id: int,
    dados: SolicitacaoAtualizarStatus,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    return empresa_service.atualizar_status_solicitacao(db, solicitacao_id, dados.status)