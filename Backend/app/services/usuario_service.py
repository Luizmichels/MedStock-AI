from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.usuario import Usuario
from app.core.security import hash_senha, verificar_senha
from app.schemas.usuario_schemas import (
    MeuPerfilUpdate,
    TrocarSenhaRequest,
    UsuarioCreate,
    UsuarioUpdate,
)

PERFIL_SUPER_ADMIN = "super_admin"


def listar_usuarios(db: Session, empresa_id: int) -> list[Usuario]:
    """Usuários da empresa. O super admin é da plataforma e nunca aparece aqui."""
    return (
        db.query(Usuario)
        .filter(Usuario.empresa_id == empresa_id, Usuario.perfil != PERFIL_SUPER_ADMIN)
        .all()
    )


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


def _email_em_uso(db: Session, email: str, usuario_id: int) -> bool:
    return (
        db.query(Usuario).filter(Usuario.email == email, Usuario.id != usuario_id).first()
        is not None
    )


def atualizar_meu_perfil(db: Session, usuario: Usuario, dados: MeuPerfilUpdate) -> Usuario:
    """O próprio usuário altera nome e/ou e-mail. O e-mail é o login, então
    trocá-lo exige confirmar a senha atual."""
    if dados.nome is not None:
        nome = dados.nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Informe o nome.")
        usuario.nome = nome
    if dados.email is not None and dados.email != usuario.email:
        if not dados.senha_atual or not verificar_senha(dados.senha_atual, usuario.senha_hash):
            raise HTTPException(status_code=400, detail="Senha atual incorreta.")
        if _email_em_uso(db, dados.email, usuario.id):
            raise HTTPException(status_code=400, detail="E-mail já utilizado por outro usuário")
        usuario.email = dados.email
    db.commit()
    db.refresh(usuario)
    return usuario


def trocar_senha(db: Session, usuario: Usuario, dados: TrocarSenhaRequest) -> None:
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    if dados.senha_atual == dados.nova_senha:
        raise HTTPException(status_code=400, detail="A nova senha deve ser diferente da atual.")
    usuario.senha_hash = hash_senha(dados.nova_senha)
    db.commit()


def desativar_usuario(db: Session, usuario_id: int, empresa_id: int) -> Usuario:
    usuario = buscar_usuario(db, usuario_id, empresa_id)
    usuario.ativo = False
    db.commit()
    db.refresh(usuario)
    return usuario
