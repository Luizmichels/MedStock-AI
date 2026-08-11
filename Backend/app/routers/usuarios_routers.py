from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.usuario import Usuario
from app.schemas.usuario_schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.services import usuario_service

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

@router.get("/me", response_model=UsuarioResponse)
def me(current_user: Usuario = Depends(get_current_user)):
    return current_user

@router.get("/listar/usuarios", response_model=list[UsuarioResponse])
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return usuario_service.listar_usuarios(db, current_user.empresa_id)


@router.get("/buscar/usuario/{usuario_id}", response_model=UsuarioResponse)
def buscar(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return usuario_service.buscar_usuario(db, usuario_id, current_user.empresa_id)


@router.post("/criar/usuario", response_model=UsuarioResponse, status_code=201)
def criar(
    dados: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return usuario_service.criar_usuario(db, dados, current_user.empresa_id)


@router.patch("/atualizar/usuario/{usuario_id}", response_model=UsuarioResponse)
def atualizar(
    usuario_id: int,
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return usuario_service.atualizar_usuario(db, usuario_id, current_user.empresa_id, dados)


@router.delete("/desativar/usuario/{usuario_id}", response_model=UsuarioResponse)
def desativar(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    return usuario_service.desativar_usuario(db, usuario_id, current_user.empresa_id)
