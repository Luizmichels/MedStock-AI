from app.models.empresa import Empresa

from tests.conftest import criar_usuario, token_para


def test_criar_usuario_sem_token_e_negado(client):
    resposta = client.post(
        "/usuarios/criar/usuario",
        json={"nome": "Novo", "email": "novo@teste.com", "senha": "Senha123!", "perfil": "usuario"},
    )

    assert resposta.status_code == 401


def test_criar_usuario_como_usuario_comum_e_negado(client, db_session, empresa):
    usuario_comum = criar_usuario(db_session, empresa, perfil="usuario")
    token = token_para(usuario_comum)

    resposta = client.post(
        "/usuarios/criar/usuario",
        json={"nome": "Novo", "email": "novo@teste.com", "senha": "Senha123!", "perfil": "usuario"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403


def test_criar_usuario_como_admin_funciona(client, db_session, usuario_admin):
    token = token_para(usuario_admin)

    resposta = client.post(
        "/usuarios/criar/usuario",
        json={"nome": "Novo", "email": "novo@teste.com", "senha": "Senha123!", "perfil": "usuario"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["email"] == "novo@teste.com"


def test_listar_usuarios_e_isolado_por_empresa(client, db_session, empresa):
    admin_empresa_a = criar_usuario(db_session, empresa, perfil="admin")
    outro_usuario_empresa_a = criar_usuario(db_session, empresa, perfil="usuario")

    empresa_b = Empresa(
        nome="Hospital B",
        email_responsavel="respb@hospitalb.com",
        nome_responsavel="Resp B",
        endereco="Rua B, 200",
        cidade="Blumenau",
        uf="SC",
    )
    db_session.add(empresa_b)
    db_session.commit()
    db_session.refresh(empresa_b)
    criar_usuario(db_session, empresa_b, perfil="usuario")

    token = token_para(admin_empresa_a)
    resposta = client.get("/usuarios/listar/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    emails_retornados = {u["email"] for u in resposta.json()}
    assert admin_empresa_a.email in emails_retornados
    assert outro_usuario_empresa_a.email in emails_retornados
    assert not any(e.endswith("hospitalb.com") for e in emails_retornados)


def test_atualizar_usuario_com_email_duplicado_da_400(client, db_session, empresa, usuario_admin):
    outro = criar_usuario(db_session, empresa, perfil="usuario")
    token = token_para(usuario_admin)

    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{outro.id}",
        json={"email": usuario_admin.email},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 400


def test_desativar_usuario(client, db_session, empresa, usuario_admin):
    alvo = criar_usuario(db_session, empresa, perfil="usuario")
    token = token_para(usuario_admin)

    resposta = client.delete(
        f"/usuarios/desativar/usuario/{alvo.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert resposta.status_code == 200
    db_session.refresh(alvo)
    assert alvo.ativo is False


# --------------------------------------------------------------------------- #
# Perfil do próprio usuário (/usuarios/me)
# --------------------------------------------------------------------------- #
def _auth_de(usuario) -> dict:
    return {"Authorization": f"Bearer {token_para(usuario)}"}


def test_usuario_altera_o_proprio_nome(client, db_session, usuario_comum):
    resposta = client.patch("/usuarios/me", headers=_auth_de(usuario_comum), json={"nome": "  Novo Nome  "})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Novo Nome"


def test_trocar_email_exige_senha_atual(client, db_session, usuario_comum):
    novo = "novo@hospitalteste.com"
    sem_senha = client.patch("/usuarios/me", headers=_auth_de(usuario_comum), json={"email": novo})
    assert sem_senha.status_code == 400
    errada = client.patch(
        "/usuarios/me", headers=_auth_de(usuario_comum), json={"email": novo, "senha_atual": "errada"}
    )
    assert errada.status_code == 400
    certa = client.patch(
        "/usuarios/me", headers=_auth_de(usuario_comum), json={"email": novo, "senha_atual": "Senha123!"}
    )
    assert certa.status_code == 200
    assert certa.json()["email"] == novo


def test_trocar_email_para_um_ja_usado_da_400(client, db_session, empresa, usuario_comum, usuario_admin):
    resposta = client.patch(
        "/usuarios/me", headers=_auth_de(usuario_comum),
        json={"email": usuario_admin.email, "senha_atual": "Senha123!"},
    )
    assert resposta.status_code == 400


def test_trocar_a_propria_senha(client, db_session, usuario_comum):
    def trocar(atual, nova):
        return client.post(
            "/usuarios/me/senha", headers=_auth_de(usuario_comum),
            json={"senha_atual": atual, "nova_senha": nova},
        )

    assert trocar("errada", "NovaSenha456!").status_code == 400
    assert trocar("Senha123!", "curta").status_code == 422
    assert trocar("Senha123!", "Senha123!").status_code == 400
    assert trocar("Senha123!", "NovaSenha456!").status_code == 200
    login = client.post("/auth/login", json={"email": usuario_comum.email, "senha": "NovaSenha456!"})
    assert login.status_code == 200


def test_super_admin_nao_aparece_na_lista_de_usuarios(client, db_session, empresa, usuario_admin):
    criar_usuario(db_session, empresa, perfil="super_admin")
    resposta = client.get("/usuarios/listar/usuarios", headers=_auth_de(usuario_admin))
    assert "super_admin" not in {u["perfil"] for u in resposta.json()}
