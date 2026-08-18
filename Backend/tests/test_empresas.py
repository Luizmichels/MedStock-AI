from app.models.empresa import Empresa
from app.models.solicitacoes_acesso import SolicitacaoAcesso
from app.models.usuario import Usuario

from tests.conftest import criar_usuario, token_para

SOLICITACAO_VALIDA = {
    "nome_responsavel": "Maria Souza",
    "email": "maria@hospitalnovo.com",
    "nome_hospital": "Hospital Novo",
    "endereco": "Av. Central, 500",
    "uf": "SC",
    "cidade": "Joinville",
}


def _criar_solicitacao_pendente(db_session, **overrides) -> SolicitacaoAcesso:
    dados = {**SOLICITACAO_VALIDA, "status": "pendente"}
    dados.update(overrides)
    solicitacao = SolicitacaoAcesso(**dados)
    db_session.add(solicitacao)
    db_session.commit()
    db_session.refresh(solicitacao)
    return solicitacao


def test_enviar_solicitacao_sucesso(client):
    resposta = client.post("/empresas/enviar/solicitacao", json=SOLICITACAO_VALIDA)

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pendente"


def test_enviar_solicitacao_sem_endereco_da_422(client):
    payload = {k: v for k, v in SOLICITACAO_VALIDA.items() if k != "endereco"}

    resposta = client.post("/empresas/enviar/solicitacao", json=payload)

    assert resposta.status_code == 422


def test_enviar_solicitacao_email_invalido_da_422(client):
    payload = {**SOLICITACAO_VALIDA, "email": "nao-e-um-email"}

    resposta = client.post("/empresas/enviar/solicitacao", json=payload)

    assert resposta.status_code == 422


def test_listar_solicitacoes_sem_token_e_negado(client):
    resposta = client.get("/empresas/solicitacoes/pendentes")

    assert resposta.status_code == 401


def test_listar_solicitacoes_com_usuario_comum_e_negado(client, db_session, empresa):
    usuario = criar_usuario(db_session, empresa, perfil="usuario")
    token = token_para(usuario)

    resposta = client.get(
        "/empresas/solicitacoes/pendentes", headers={"Authorization": f"Bearer {token}"}
    )

    assert resposta.status_code == 403


def test_aprovar_solicitacao_cria_empresa_e_usuario_admin(client, db_session, token_super_admin, enviar_email_mock):
    solicitacao = _criar_solicitacao_pendente(db_session)

    resposta = client.patch(
        f"/empresas/solicitacoes/{solicitacao.id}",
        json={"status": "aprovado"},
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "aprovado"

    empresa_criada = db_session.query(Empresa).filter(Empresa.nome == "Hospital Novo").first()
    assert empresa_criada is not None
    assert empresa_criada.endereco == "Av. Central, 500"

    usuario_criado = db_session.query(Usuario).filter(Usuario.email == "maria@hospitalnovo.com").first()
    assert usuario_criado is not None
    assert usuario_criado.perfil == "admin"
    assert usuario_criado.ativo is False

    enviar_email_mock.assert_called_once()
    assert enviar_email_mock.call_args.kwargs["destinatario"] == "maria@hospitalnovo.com"


def test_aprovar_solicitacao_com_email_ja_cadastrado_da_400(client, db_session, token_super_admin, empresa):
    criar_usuario(db_session, empresa, perfil="admin")
    usuario_existente = db_session.query(Usuario).filter(Usuario.empresa_id == empresa.id).first()
    solicitacao = _criar_solicitacao_pendente(db_session, email=usuario_existente.email)

    resposta = client.patch(
        f"/empresas/solicitacoes/{solicitacao.id}",
        json={"status": "aprovado"},
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 400


def test_aprovar_solicitacao_ja_processada_da_400(client, db_session, token_super_admin):
    solicitacao = _criar_solicitacao_pendente(db_session, status="aprovado")

    resposta = client.patch(
        f"/empresas/solicitacoes/{solicitacao.id}",
        json={"status": "rejeitado"},
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 400


def test_rejeitar_solicitacao_nao_cria_empresa(client, db_session, token_super_admin):
    solicitacao = _criar_solicitacao_pendente(db_session)

    resposta = client.patch(
        f"/empresas/solicitacoes/{solicitacao.id}",
        json={"status": "rejeitado"},
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 200
    assert db_session.query(Empresa).filter(Empresa.nome == "Hospital Novo").first() is None
