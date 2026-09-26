import re
from datetime import date
from unittest.mock import MagicMock

import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models  # noqa: F401 — registra os modelos no metadata antes do create_all
from app.core.config import settings
from app.core.security import criar_token, hash_senha
from app.database import Base, get_db
from app.main import app
from app.models.consumo_tratado import ConsumoTratado
from app.models.empresa import Empresa
from app.models.itens import Item
from app.models.usuario import Usuario


def _test_database_url() -> str:
    # SQLite em memória é o padrão: zero setup, rápido e determinístico.
    # Para rodar contra um Postgres real (ex.: CI), defina TEST_DATABASE_URL.
    return getattr(settings, "TEST_DATABASE_URL", None) or "sqlite+pysqlite:///:memory:"


TEST_DATABASE_URL = _test_database_url()
_USA_SQLITE = TEST_DATABASE_URL.startswith("sqlite")


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
    if _USA_SQLITE:
        # StaticPool + check_same_thread mantêm o banco em memória vivo e
        # compartilhado entre a sessão de teste e o TestClient.
        test_engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        _garantir_banco_teste_existe()
        test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine):
    if _USA_SQLITE:
        # StaticPool compartilha uma única conexão em memória, então recriar o
        # schema a cada teste é a forma mais robusta de isolar (e é instantâneo).
        # O reset fica no setup para que o schema permaneça disponível entre
        # testes (ex.: os que inspecionam o `engine` diretamente).
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        SessionTeste = sessionmaker(bind=engine)
        session = SessionTeste()
        try:
            yield session
        finally:
            session.close()
    else:
        # Postgres: isolamento por transação externa + savepoints (mais rápido).
        connection = engine.connect()
        transacao = connection.begin()
        SessionTeste = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
        session = SessionTeste()
        try:
            yield session
        finally:
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


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    # Zera o limitador em memória entre testes para não vazar estado.
    from app.core.rate_limit import limitador_solicitacoes

    limitador_solicitacoes.reset()
    yield


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


@pytest.fixture
def token_admin(usuario_admin) -> str:
    return token_para(usuario_admin)


@pytest.fixture
def usuario_comum(db_session, empresa) -> Usuario:
    return criar_usuario(db_session, empresa, perfil="usuario")


@pytest.fixture
def empresa_secundaria(db_session) -> Empresa:
    """Segunda empresa, para os testes de isolamento (RF16)."""
    empresa = Empresa(
        nome="Hospital Secundário",
        cnpj="11.111.111/0001-11",
        email_responsavel="responsavel@hospital2.com",
        nome_responsavel="Responsável Dois",
        endereco="Avenida de Teste, 200",
        cidade="Curitiba",
        uf="PR",
    )
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)
    return empresa


@pytest.fixture
def item(db_session, empresa) -> Item:
    item = Item(
        empresa_id=empresa.id,
        codigo_item="MED001",
        descricao_item="Dipirona 500mg",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def serie_consumo(db_session, empresa, item):
    """18 meses de ConsumoTratado com tendência + sazonalidade determinística."""
    base = date(2024, 1, 1)
    registros = []
    for i in range(18):
        periodo = base + relativedelta(months=i)
        sazonal = 20 if periodo.month in (11, 12) else 0
        quantidade = 100 + 5 * i + sazonal
        tratado = ConsumoTratado(
            empresa_id=empresa.id,
            item_id=item.id,
            periodo=periodo,
            quantidade_total=float(quantidade),
            valor_total=float(quantidade) * 10.0,
            local_estoque="Almoxarifado Central",
        )
        db_session.add(tratado)
        registros.append(tratado)
    db_session.commit()
    return registros


@pytest.fixture
def csv_valido() -> bytes:
    """CSV mínimo com as 6 colunas obrigatórias e 3 linhas boas."""
    linhas = [
        "codigo_item;descricao_item;data;quantidade;valor;local_estoque",
        "MED001;Dipirona 500mg;01/01/2024;100;250.50;Almoxarifado Central",
        "MED002;Soro Fisiológico 500ml;15/01/2024;50;120.00;Farmácia",
        "MED001;Dipirona 500mg;10/02/2024;80;200.00;Almoxarifado Central",
    ]
    return "\n".join(linhas).encode("utf-8")


@pytest.fixture
def csv_invalido() -> bytes:
    """CSV sem a coluna 'data' — dispara o FA02."""
    linhas = [
        "codigo_item;descricao_item;quantidade;valor;local_estoque",
        "MED001;Dipirona 500mg;100;250.50;Almoxarifado Central",
    ]
    return "\n".join(linhas).encode("utf-8")
