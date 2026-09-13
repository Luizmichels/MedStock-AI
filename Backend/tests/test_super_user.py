"""Testes da criação idempotente do super admin no startup."""

import pytest
from sqlalchemy.orm import sessionmaker

from app.core import super_user
from app.core.config import settings
from app.models.empresa import Empresa
from app.models.usuario import Usuario


@pytest.fixture
def session_local_de_teste(engine, monkeypatch):
    """Faz o super_user usar o engine de teste em vez do SessionLocal de produção."""
    fabrica = sessionmaker(bind=engine)
    monkeypatch.setattr(super_user, "SessionLocal", fabrica)
    return fabrica


def test_super_admin_cria_usuario_quando_nao_existe(db_session, session_local_de_teste):
    super_user.super_admin()

    admin = (
        db_session.query(Usuario)
        .filter(Usuario.email == settings.SUPER_ADMIN_EMAIL)
        .first()
    )
    assert admin is not None
    assert admin.perfil == "super_admin"


def test_super_admin_nao_duplica_se_ja_existe(db_session, session_local_de_teste):
    super_user.super_admin()
    super_user.super_admin()

    total = (
        db_session.query(Usuario)
        .filter(Usuario.email == settings.SUPER_ADMIN_EMAIL)
        .count()
    )
    assert total == 1


def test_super_admin_cria_empresa_sistema(db_session, session_local_de_teste):
    super_user.super_admin()

    empresa = (
        db_session.query(Empresa)
        .filter(Empresa.nome == "Sistema MedStock")
        .first()
    )
    assert empresa is not None
