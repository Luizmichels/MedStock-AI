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


# --------------------------------------------------------------------------- #
# Hospital desativado pelo super admin
# --------------------------------------------------------------------------- #
def _desativar(db_session, empresa):
    empresa.ativa = False
    db_session.commit()


def test_login_de_hospital_desativado_da_403_com_o_motivo(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, senha="Senha123!")
    _desativar(db_session, empresa)

    resposta = client.post("/auth/login", json={"email": usuario.email, "senha": "Senha123!"})

    assert resposta.status_code == 403
    assert "desativado" in resposta.json()["detail"]


def test_hospital_desativado_com_senha_errada_continua_401(client, db_session, empresa):
    # Sem a senha certa, a resposta não revela que o hospital foi desativado.
    usuario = criar_usuario(db_session, empresa, senha="Senha123!")
    _desativar(db_session, empresa)

    resposta = client.post("/auth/login", json={"email": usuario.email, "senha": "Errada123!"})

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Credenciais inválidas"


def test_sessao_aberta_para_de_valer_quando_o_hospital_e_desativado(client, db_session, empresa):
    from tests.conftest import token_para

    usuario = criar_usuario(db_session, empresa)
    cabecalho = {"Authorization": f"Bearer {token_para(usuario)}"}
    assert client.get("/usuarios/me", headers=cabecalho).status_code == 200

    _desativar(db_session, empresa)

    resposta = client.get("/usuarios/me", headers=cabecalho)
    assert resposta.status_code == 401
    assert "desativado" in resposta.json()["detail"]


def test_super_admin_nao_e_barrado_pela_empresa_tecnica(client, db_session, empresa):
    # A empresa do super admin é só um registro técnico ("Sistema MedStock").
    super_admin = criar_usuario(db_session, empresa, perfil="super_admin", senha="Senha123!")
    _desativar(db_session, empresa)

    resposta = client.post("/auth/login", json={"email": super_admin.email, "senha": "Senha123!"})

    assert resposta.status_code == 200
