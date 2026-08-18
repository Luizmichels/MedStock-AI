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
