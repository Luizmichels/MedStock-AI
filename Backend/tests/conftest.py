import re
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import app.models  # noqa: F401 — registra os modelos no metadata antes do create_all
from app.core.config import settings
from app.core.security import criar_token, hash_senha
from app.database import Base, get_db
from app.main import app
from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _test_database_url() -> str:
    if getattr(settings, "TEST_DATABASE_URL", None):
        return settings.TEST_DATABASE_URL
    return re.sub(r"/[^/]+$", "/medstock_test", settings.DATABASE_URL)


TEST_DATABASE_URL = _test_database_url()


def _garantir_banco_teste_existe() -> None:
    admin_url = re.sub(r"/[^/]+$", "/postgres", TEST_DATABASE_URL)
    nome_banco = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": nome_banco}
        ).first()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{nome_banco}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _garantir_banco_teste_existe()
    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transacao = connection.begin()
    SessionTeste = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = SessionTeste()

    yield session

    session.close()
    transacao.rollback()
    connection.close()


@pytest.fixture
def enviar_email_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("app.services.empresa_service.enviar_email", mock)
    return mock


@pytest.fixture
def client(db_session, enviar_email_mock):
    app.router.on_startup.clear()

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def empresa(db_session) -> Empresa:
    empresa = Empresa(
        nome="Hospital de Teste",
        cnpj="00.000.000/0001-00",
        email_responsavel="responsavel@hospitalteste.com",
        nome_responsavel="Responsável Teste",
        endereco="Rua de Teste, 100",
        cidade="Joinville",
        uf="SC",
    )
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)
    return empresa


def criar_usuario(db_session, empresa: Empresa, perfil: str = "admin", ativo: bool = True, senha: str = "Senha123!") -> Usuario:
    usuario = Usuario(
        empresa_id=empresa.id,
        nome=f"Usuário {perfil}",
        email=f"{perfil}.{empresa.id}@hospitalteste.com",
        senha_hash=hash_senha(senha),
        perfil=perfil,
        ativo=ativo,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_admin(db_session, empresa) -> Usuario:
    return criar_usuario(db_session, empresa, perfil="admin")


def token_para(usuario: Usuario) -> str:
    return criar_token(
        {"sub": str(usuario.id), "empresa_id": usuario.empresa_id, "perfil": usuario.perfil}
    )


@pytest.fixture
def token_super_admin() -> str:
    return criar_token({"sub": "0", "perfil": "super_admin"})
