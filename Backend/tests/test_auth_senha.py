"""Testes de 'esqueci minha senha', redefinição e reenvio de ativação."""

from unittest.mock import MagicMock

import pytest

from app.core.security import criar_token
from tests.conftest import criar_usuario


@pytest.fixture
def email_auth_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("app.services.auth_service.enviar_email", mock)
    return mock


def test_esqueci_senha_envia_email_para_usuario_ativo(client, db_session, empresa, email_auth_mock):
    usuario = criar_usuario(db_session, empresa, perfil="usuario")
    resposta = client.post("/auth/esqueci-senha", json={"email": usuario.email})
    assert resposta.status_code == 200
    email_auth_mock.assert_called_once()


def test_esqueci_senha_email_inexistente_retorna_200_sem_enviar(client, email_auth_mock):
    resposta = client.post("/auth/esqueci-senha", json={"email": "ninguem@x.com"})
    assert resposta.status_code == 200
    email_auth_mock.assert_not_called()


def test_redefinir_senha_permite_login_com_nova_senha(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, perfil="usuario")
    token = criar_token({"sub": str(usuario.id), "tipo": "redefinir_senha"})

    resposta = client.post("/auth/redefinir-senha", json={"token": token, "senha": "NovaSenha456!"})
    assert resposta.status_code == 200

    login = client.post("/auth/login", json={"email": usuario.email, "senha": "NovaSenha456!"})
    assert login.status_code == 200


def test_redefinir_senha_token_tipo_errado_401(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, perfil="usuario")
    token = criar_token({"sub": str(usuario.id), "tipo": "definir_senha"})
    resposta = client.post("/auth/redefinir-senha", json={"token": token, "senha": "X123456!"})
    assert resposta.status_code == 401


def test_reenviar_ativacao_para_usuario_inativo(client, db_session, empresa, email_auth_mock):
    usuario = criar_usuario(db_session, empresa, perfil="usuario", ativo=False)
    resposta = client.post("/auth/reenviar-ativacao", json={"email": usuario.email})
    assert resposta.status_code == 200
    email_auth_mock.assert_called_once()


def test_reenviar_ativacao_usuario_ativo_nao_envia(client, db_session, empresa, email_auth_mock):
    usuario = criar_usuario(db_session, empresa, perfil="usuario", ativo=True)
    resposta = client.post("/auth/reenviar-ativacao", json={"email": usuario.email})
    assert resposta.status_code == 200
    email_auth_mock.assert_not_called()


def test_redefinir_senha_impede_reuso_de_token(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, perfil="usuario")
    token = criar_token({
        "sub": str(usuario.id),
        "tipo": "redefinir_senha",
        "v": usuario.senha_hash[:10],
    })

    resp1 = client.post("/auth/redefinir-senha", json={"token": token, "senha": "NovaSenha456!"})
    assert resp1.status_code == 200

    resp2 = client.post("/auth/redefinir-senha", json={"token": token, "senha": "OutraSenha789!"})
    assert resp2.status_code == 401
