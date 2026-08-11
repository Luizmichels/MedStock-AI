from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.usuario import Usuario
from app.core.security import hash_senha
from app.schemas.usuario_schemas import UsuarioCreate, UsuarioUpdate


def listar_usuarios(db: Session, empresa_id: int) -> list[Usuario]:
    return db.query(Usuario).filter(Usuario.empresa_id == empresa_id).all()


def buscar_usuario(db: Session, usuario_id: int, empresa_id: int) -> Usuario:
    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id, Usuario.empresa_id == empresa_id
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


def criar_usuario(db: Session, dados: UsuarioCreate, empresa_id: int) -> Usuario:
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    usuario = Usuario(
        empresa_id=empresa_id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        perfil=dados.perfil,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def atualizar_usuario(
    db: Session, usuario_id: int, empresa_id: int, dados: UsuarioUpdate
) -> Usuario:
    usuario = buscar_usuario(db, usuario_id, empresa_id)
    if dados.nome is not None:
        usuario.nome = dados.nome
    if dados.email is not None:
        if db.query(Usuario).filter(
            Usuario.email == dados.email, Usuario.id != usuario_id
        ).first():
            raise HTTPException(status_code=400, detail="E-mail já utilizado por outro usuário")
        usuario.email = dados.email
    if dados.senha is not None:
        usuario.senha_hash = hash_senha(dados.senha)
    if dados.perfil is not None:
        usuario.perfil = dados.perfil
    if dados.ativo is not None:
        usuario.ativo = dados.ativo
    db.commit()
    db.refresh(usuario)
    return usuario


def desativar_usuario(db: Session, usuario_id: int, empresa_id: int) -> Usuario:
    usuario = buscar_usuario(db, usuario_id, empresa_id)
    usuario.ativo = False
    db.commit()
    db.refresh(usuario)
    return usuario
