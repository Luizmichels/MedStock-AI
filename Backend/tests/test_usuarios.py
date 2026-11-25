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


# --------------------------------------------------------------------------- #
# Proteções: ninguém desativa a si mesmo e o hospital não fica sem admin
# --------------------------------------------------------------------------- #
def _outro_admin(db_session, admin, ativo=True):
    """Segundo admin do mesmo hospital (o criar_usuario gera o e-mail pelo perfil)."""
    from app.core.security import hash_senha
    from app.models.usuario import Usuario

    outro = Usuario(
        empresa_id=admin.empresa_id, nome="Outro admin", email="outro.admin@hospitalteste.com",
        senha_hash=hash_senha("Senha123!"), perfil="admin", ativo=ativo,
    )
    db_session.add(outro)
    db_session.commit()
    db_session.refresh(outro)
    return outro


def test_admin_nao_desativa_a_propria_conta(client, db_session, usuario_admin):
    _outro_admin(db_session, usuario_admin)  # há outro admin
    resposta = client.delete(
        f"/usuarios/desativar/usuario/{usuario_admin.id}", headers=_auth_de(usuario_admin)
    )
    assert resposta.status_code == 400
    assert "própria conta" in resposta.json()["detail"]
    db_session.refresh(usuario_admin)
    assert usuario_admin.ativo is True


def test_admin_nao_se_desativa_pela_edicao(client, db_session, usuario_admin):
    _outro_admin(db_session, usuario_admin)
    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{usuario_admin.id}",
        json={"ativo": False},
        headers=_auth_de(usuario_admin),
    )
    assert resposta.status_code == 400


def test_unico_admin_nao_pode_deixar_de_ser_admin(client, db_session, usuario_admin):
    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{usuario_admin.id}",
        json={"perfil": "usuario"},
        headers=_auth_de(usuario_admin),
    )
    assert resposta.status_code == 400
    assert "pelo menos um administrador" in resposta.json()["detail"]
    db_session.refresh(usuario_admin)
    assert usuario_admin.perfil == "admin"


def test_admin_inativo_nao_conta_como_administrador(client, db_session, usuario_admin):
    _outro_admin(db_session, usuario_admin, ativo=False)
    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{usuario_admin.id}",
        json={"perfil": "usuario"},
        headers=_auth_de(usuario_admin),
    )
    assert resposta.status_code == 400


def test_com_outro_admin_ativo_pode_deixar_de_ser_admin(client, db_session, usuario_admin):
    _outro_admin(db_session, usuario_admin)
    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{usuario_admin.id}",
        json={"perfil": "usuario"},
        headers=_auth_de(usuario_admin),
    )
    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "usuario"


def test_desativar_outro_admin_quando_ha_dois(client, db_session, usuario_admin):
    outro_admin = _outro_admin(db_session, usuario_admin)
    resposta = client.delete(
        f"/usuarios/desativar/usuario/{outro_admin.id}", headers=_auth_de(usuario_admin)
    )
    assert resposta.status_code == 200
    db_session.refresh(outro_admin)
    assert outro_admin.ativo is False


def test_reativar_usuario_nao_e_bloqueado(client, db_session, usuario_admin):
    inativo = criar_usuario(db_session, usuario_admin.empresa, perfil="usuario", ativo=False)
    resposta = client.patch(
        f"/usuarios/atualizar/usuario/{inativo.id}",
        json={"ativo": True},
        headers=_auth_de(usuario_admin),
    )
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True
