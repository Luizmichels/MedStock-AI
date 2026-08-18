from app.core.security import criar_token, verificar_senha
from app.models.usuario import Usuario

from tests.conftest import criar_usuario


def test_login_sucesso(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, senha="Senha123!")

    resposta = client.post("/auth/login", json={"email": usuario.email, "senha": "Senha123!"})

    assert resposta.status_code == 200
    assert "access_token" in resposta.json()


def test_login_senha_errada(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, senha="Senha123!")

    resposta = client.post("/auth/login", json={"email": usuario.email, "senha": "SenhaErrada"})

    assert resposta.status_code == 401


def test_login_usuario_inativo(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, senha="Senha123!", ativo=False)

    resposta = client.post("/auth/login", json={"email": usuario.email, "senha": "Senha123!"})

    assert resposta.status_code == 401


def test_definir_senha_fluxo_completo(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, ativo=False)
    token = criar_token({"sub": str(usuario.id), "tipo": "definir_senha"})

    resposta = client.post("/auth/definir-senha", json={"token": token, "senha": "NovaSenha123!"})
    assert resposta.status_code == 200

    db_session.refresh(usuario)
    assert usuario.ativo is True
    assert verificar_senha("NovaSenha123!", usuario.senha_hash)

    login = client.post("/auth/login", json={"email": usuario.email, "senha": "NovaSenha123!"})
    assert login.status_code == 200


def test_definir_senha_token_reutilizado_e_bloqueado(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, ativo=False)
    token = criar_token({"sub": str(usuario.id), "tipo": "definir_senha"})

    client.post("/auth/definir-senha", json={"token": token, "senha": "NovaSenha123!"})
    resposta = client.post("/auth/definir-senha", json={"token": token, "senha": "OutraSenha456!"})

    assert resposta.status_code == 400


def test_definir_senha_com_tipo_errado_e_rejeitado(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, ativo=False)
    token = criar_token({"sub": str(usuario.id), "tipo": "acesso"})

    resposta = client.post("/auth/definir-senha", json={"token": token, "senha": "NovaSenha123!"})

    assert resposta.status_code == 401


def test_definir_senha_com_token_invalido_e_rejeitado(client):
    resposta = client.post("/auth/definir-senha", json={"token": "token-invalido", "senha": "NovaSenha123!"})

    assert resposta.status_code == 401
