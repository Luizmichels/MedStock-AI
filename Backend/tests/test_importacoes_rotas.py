"""Testes de contrato das rotas de importação."""

from app.models.importacoes import Importacao


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _importacao(db, empresa, usuario, nome="arquivo.csv") -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo=nome, tipo="csv", status="concluido",
    )
    db.add(imp)
    db.commit()
    db.refresh(imp)
    return imp


def test_upload_csv_valido_processa_em_background(client, db_session, token_admin, csv_valido, monkeypatch):
    from app.routers import importacoes_routers
    from app.services.abc_service import recalcular_abc
    from app.services.data_pipeline_service import executar_pipeline

    def fake_bg(importacao_id, conteudo, nome_arquivo, empresa_id):
        importacao = db_session.query(Importacao).filter(Importacao.id == importacao_id).first()
        executar_pipeline(db_session, importacao, conteudo, nome_arquivo, empresa_id)
        if importacao.status == "concluido" and importacao.registros_validos > 0:
            recalcular_abc(db_session, empresa_id)

    monkeypatch.setattr(importacoes_routers, "_processar_importacao_background", fake_bg)

    resposta = client.post(
        "/importacoes/upload",
        headers=_auth(token_admin),
        files={"arquivo": ("consumo.csv", csv_valido, "text/csv")},
    )
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "processando"
    importacao_id = resposta.json()["id"]

    detalhe = client.get(f"/importacoes/{importacao_id}", headers=_auth(token_admin))
    assert detalhe.json()["status"] == "concluido"
    assert detalhe.json()["registros_validos"] == 3


def test_upload_formato_invalido_da_400(client, token_admin):
    resposta = client.post(
        "/importacoes/upload",
        headers=_auth(token_admin),
        files={"arquivo": ("consumo.txt", b"qualquer", "text/plain")},
    )
    assert resposta.status_code == 400


def test_upload_sem_permissao_de_admin_403(client, usuario_comum, csv_valido):
    from tests.conftest import token_para
    token = token_para(usuario_comum)
    resposta = client.post(
        "/importacoes/upload",
        headers=_auth(token),
        files={"arquivo": ("consumo.csv", csv_valido, "text/csv")},
    )
    assert resposta.status_code == 403


def test_upload_sem_autenticacao_rejeitado(client, csv_valido):
    resposta = client.post(
        "/importacoes/upload",
        files={"arquivo": ("consumo.csv", csv_valido, "text/csv")},
    )
    assert resposta.status_code in (401, 403)


def test_listar_importacoes_isolado_por_empresa(
    client, db_session, token_admin, empresa, usuario_admin, empresa_secundaria
):
    _importacao(db_session, empresa, usuario_admin, nome="minha.csv")
    outro_usuario = usuario_admin  # fk usuario só precisa existir
    _importacao(db_session, empresa_secundaria, outro_usuario, nome="outra.csv")

    resposta = client.get("/importacoes/", headers=_auth(token_admin))
    assert resposta.status_code == 200
    nomes = [i["nome_arquivo"] for i in resposta.json()]
    assert "minha.csv" in nomes
    assert "outra.csv" not in nomes


def test_detalhe_importacao_existente(client, db_session, token_admin, empresa, usuario_admin):
    imp = _importacao(db_session, empresa, usuario_admin)
    resposta = client.get(f"/importacoes/{imp.id}", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["id"] == imp.id


def test_detalhe_importacao_inexistente_404(client, token_admin):
    resposta = client.get("/importacoes/99999", headers=_auth(token_admin))
    assert resposta.status_code == 404
