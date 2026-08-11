import secrets
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import hash_senha, criar_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.solicitacoes_acesso import SolicitacaoAcesso
from app.schemas.empresa_schemas import EmpresaCreate, EmpresaUpdate
from app.schemas.solicitacao_acesso_schemas import SolicitacaoCreate
from app.services.email_service import enviar_email, montar_email_definicao_senha


def listar_empresas(db: Session) -> list[Empresa]:
    return db.query(Empresa).all()


def buscar_empresa(db: Session, empresa_id: int) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


def criar_empresa(db: Session, dados: EmpresaCreate) -> Empresa:
    empresa = Empresa(**dados.model_dump())
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def atualizar_empresa(db: Session, empresa_id: int, dados: EmpresaUpdate) -> Empresa:
    empresa = buscar_empresa(db, empresa_id)
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa


def desativar_empresa(db: Session, empresa_id: int) -> Empresa:
    empresa = buscar_empresa(db, empresa_id)
    empresa.ativa = False
    db.commit()
    db.refresh(empresa)
    return empresa


def criar_solicitacao(db: Session, dados: SolicitacaoCreate) -> SolicitacaoAcesso:
    solicitacao = SolicitacaoAcesso(**dados.model_dump())
    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


def listar_solicitacoes(db: Session) -> list[SolicitacaoAcesso]:
    return db.query(SolicitacaoAcesso).order_by(SolicitacaoAcesso.criado_em.desc()).all()


def atualizar_status_solicitacao(
    db: Session, solicitacao_id: int, novo_status: str
) -> SolicitacaoAcesso:
    sol = db.query(SolicitacaoAcesso).filter(SolicitacaoAcesso.id == solicitacao_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if sol.status != "pendente":
        raise HTTPException(
            status_code=400, detail="Solicitação já foi processada anteriormente"
        )

    if novo_status == "aprovado":
        if db.query(Usuario).filter(Usuario.email == sol.email).first():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")
        _criar_empresa_e_admin_a_partir_da_solicitacao(db, sol)

    sol.status = novo_status
    sol.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(sol)
    return sol


def _criar_empresa_e_admin_a_partir_da_solicitacao(
    db: Session, sol: SolicitacaoAcesso
) -> None:
    empresa = Empresa(
        nome=sol.nome_hospital,
        endereco=sol.endereco,
        uf=sol.uf,
        cidade=sol.cidade,
        email_responsavel=sol.email,
        nome_responsavel=sol.nome_responsavel,
    )
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome=sol.nome_responsavel,
        email=sol.email,
        senha_hash=hash_senha(secrets.token_urlsafe(32)),
        perfil="admin",
        ativo=False,
    )
    db.add(usuario)
    db.flush()

    token = criar_token(
        {"sub": str(usuario.id), "tipo": "definir_senha"},
        expires_minutes=settings.DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES,
    )
    link = f"{settings.FRONTEND_URL}/definir-senha?token={token}"
    texto, html = montar_email_definicao_senha(usuario.nome, link)
    enviar_email(
        destinatario=usuario.email,
        assunto="Cadastro realizado - Defina sua senha de acesso",
        texto=texto,
        html=html,
    )
