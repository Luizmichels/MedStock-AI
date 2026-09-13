"""Testes de contrato das rotas de exportação (RF10, RN04)."""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_exportacao_pdf_define_content_disposition(client, token_admin, empresa):
    resposta = client.get("/exportacoes/previsoes?formato=pdf", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/pdf"
    assert "attachment" in resposta.headers["content-disposition"]


def test_exportacao_xlsx_retorna_planilha(client, token_admin, empresa):
    resposta = client.get("/exportacoes/consumo?formato=xlsx", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert "spreadsheetml" in resposta.headers["content-type"]


def test_exportacao_formato_invalido_da_400(client, token_admin):
    resposta = client.get("/exportacoes/previsoes?formato=txt", headers=_auth(token_admin))
    assert resposta.status_code == 400


def test_exportacao_disponivel_para_perfil_usuario(client, usuario_comum):
    from tests.conftest import token_para
    resposta = client.get(
        "/exportacoes/metricas?formato=pdf", headers=_auth(token_para(usuario_comum))
    )
    assert resposta.status_code == 200


def test_exportacao_sem_autenticacao_rejeitado(client):
    resposta = client.get("/exportacoes/previsoes")
    assert resposta.status_code in (401, 403)


def test_exportacao_metricas_xlsx(client, token_admin, empresa):
    resposta = client.get("/exportacoes/metricas?formato=xlsx", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert "spreadsheetml" in resposta.headers["content-type"]
