"""Integração via API: chave do hospital e envio de consumo (X-API-Key)."""

from app.models.chave_integracao import ChaveIntegracao
from app.models.consumo import Consumo
from app.models.importacoes import Importacao
from app.schemas.integracao_schemas import MAX_REGISTROS_POR_ENVIO
from tests.conftest import criar_usuario, token_para


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _registro(**extra) -> dict:
    return {
        "codigo_item": "MED001", "descricao_item": "Dipirona 500mg", "data": "2026-10-20",
        "quantidade": 10, "valor": 25.5, "setor": "UTI Adulto", **extra,
    }


def _processar_no_teste(monkeypatch, db_session):
    """Roda o processamento em segundo plano na sessão do teste."""
    from app.routers import integracoes_routers
    from app.services.data_pipeline_service import dataframe_de_registros, executar_pipeline

    def fake(importacao_id, registros, empresa_id):
        importacao = db_session.query(Importacao).filter(Importacao.id == importacao_id).first()
        executar_pipeline(
            db_session, importacao, b"", importacao.nome_arquivo, empresa_id,
            blocos=[dataframe_de_registros(registros)],
        )

    monkeypatch.setattr(integracoes_routers, "_processar_envio_background", fake)


def _gerar_chave(client, token) -> str:
    resposta = client.post("/integracoes/chave", headers=_auth(token))
    assert resposta.status_code == 201
    return resposta.json()["chave"]


# --------------------------------------------------------------------------- #
# Gestão da chave
# --------------------------------------------------------------------------- #
def test_gerar_consultar_e_revogar_chave(client, db_session, token_admin):
    assert client.get("/integracoes/chave", headers=_auth(token_admin)).json() is None

    chave = _gerar_chave(client, token_admin)
    assert chave.startswith("msk_")
    status = client.get("/integracoes/chave", headers=_auth(token_admin)).json()
    assert chave.startswith(status["prefixo"])
    assert "chave" not in status  # a chave completa só aparece na geração
    # Só o hash fica no banco.
    assert db_session.query(ChaveIntegracao).filter(ChaveIntegracao.hash_chave == chave).first() is None

    assert client.delete("/integracoes/chave", headers=_auth(token_admin)).status_code == 204
    assert client.get("/integracoes/chave", headers=_auth(token_admin)).json() is None
    assert client.delete("/integracoes/chave", headers=_auth(token_admin)).status_code == 404


def test_gerar_nova_chave_invalida_a_anterior(client, token_admin):
    antiga = _gerar_chave(client, token_admin)
    _gerar_chave(client, token_admin)
    resposta = client.post("/integracoes/consumos", headers={"X-API-Key": antiga}, json={"registros": [_registro()]})
    assert resposta.status_code == 401


def test_usuario_comum_nao_gerencia_chave(client, usuario_comum):
    assert client.post("/integracoes/chave", headers=_auth(token_para(usuario_comum))).status_code == 403


# --------------------------------------------------------------------------- #
# Envio de consumo
# --------------------------------------------------------------------------- #
def test_envio_sem_chave_ou_com_chave_invalida_da_401(client):
    corpo = {"registros": [_registro()]}
    assert client.post("/integracoes/consumos", json=corpo).status_code == 401
    assert client.post("/integracoes/consumos", headers={"X-API-Key": "msk_falsa"}, json=corpo).status_code == 401


def test_envio_processa_os_registros(client, db_session, empresa, token_admin, monkeypatch):
    _processar_no_teste(monkeypatch, db_session)
    chave = _gerar_chave(client, token_admin)
    resposta = client.post(
        "/integracoes/consumos",
        headers={"X-API-Key": chave},
        json={"registros": [_registro(), _registro(codigo_item="MED002", valor=-1)]},
    )
    assert resposta.status_code == 202
    corpo = resposta.json()
    assert (corpo["tipo"], corpo["modo"]) == ("api", "incremental")

    status = client.get(f"/integracoes/importacoes/{corpo['id']}", headers={"X-API-Key": chave}).json()
    assert status["status"] == "concluido"
    assert (status["registros_validos"], status["registros_invalidos"]) == (1, 1)
    assert any("linha 2" in e for e in status["erros"])  # 2º registro do envio
    assert db_session.query(Consumo).filter(Consumo.empresa_id == empresa.id).count() == 1

    registro = db_session.query(ChaveIntegracao).filter(ChaveIntegracao.empresa_id == empresa.id).first()
    assert registro.ultimo_uso_em is not None


def test_envio_valida_campos_e_limite(client, token_admin):
    chave = _gerar_chave(client, token_admin)
    cabecalho = {"X-API-Key": chave}
    sem_setor = {k: v for k, v in _registro().items() if k != "setor"}
    assert client.post("/integracoes/consumos", headers=cabecalho, json={"registros": [sem_setor]}).status_code == 422
    assert client.post("/integracoes/consumos", headers=cabecalho, json={"registros": []}).status_code == 422
    excesso = {"registros": [_registro()] * (MAX_REGISTROS_POR_ENVIO + 1)}
    assert client.post("/integracoes/consumos", headers=cabecalho, json=excesso).status_code == 422


def test_status_de_importacao_de_outro_hospital_da_404(
    client, db_session, empresa, empresa_secundaria, token_admin, monkeypatch
):
    _processar_no_teste(monkeypatch, db_session)
    chave = _gerar_chave(client, token_admin)
    admin_outro = criar_usuario(db_session, empresa_secundaria, perfil="admin")
    chave_outro = _gerar_chave(client, token_para(admin_outro))
    envio = client.post("/integracoes/consumos", headers={"X-API-Key": chave}, json={"registros": [_registro()]})
    resposta = client.get(f"/integracoes/importacoes/{envio.json()['id']}", headers={"X-API-Key": chave_outro})
    assert resposta.status_code == 404
