import logging
from app.database import SessionLocal
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.core.security import hash_senha
from app.core.config import settings

logger = logging.getLogger(__name__)

def super_admin() -> None:
    db = SessionLocal()
    try:
        existe = db.query(Usuario).filter(Usuario.email == settings.SUPER_ADMIN_EMAIL).first()
        if existe:
            logger.info("Super admin já existe")
            return
        
        empresa = db.query(Empresa).filter(Empresa.nome == "Sistema MedStock").first()
        if not empresa:
            empresa = Empresa(
                nome='Sistema MedStock',
                email_responsavel=settings.SUPER_ADMIN_EMAIL,
                nome_responsavel='Super Admin',
                cnpj='00.000.000/0000-00',
                endereco='Rua do Super Admin, 123',
                cidade='Joinville',
                uf='SC',
            )
            db.add(empresa)
            db.flush()  # para garantir que o ID da empresa seja gerado

        admin = Usuario(
            empresa_id=empresa.id,
            nome="Super Admin",
            email=settings.SUPER_ADMIN_EMAIL,
            senha_hash=hash_senha(settings.SUPER_ADMIN_SENHA),
            perfil="super_admin",
            ativo=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Super admin criado com sucesso")
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar super admin: {e}")
    finally:
        db.close()