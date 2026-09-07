"""Testes de contrato das rotas de previsões (RF06, RF07, RF08, RF11, FA03)."""

from datetime import date

import pytest

from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.routers import previsoes_routers
from app.services.ml import predicao, treinamento
from tests.conftest import token_para
from tests.ml.fakes import fabrica_fake


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _limpar_treinos():
    previsoes_routers._TREINOS_EM_ANDAMENTO.clear()
    yield
    previsoes_routers._TREINOS_EM_ANDAMENTO.clear()


def _modelo(db, empresa, algoritmo="sma", *, ativo=False, mape=15.0) -> ModeloTreinado:
    modelo = ModeloTreinado(
        empresa_id=empresa.id, algoritmo=algoritmo, ativo=ativo,
        rmse=5.0, mae=3.0, mape=mape,
    )
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo


def _item_curto(db, empresa, codigo="CURTO") -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item="Curto")
    db.add(item)
    db.flush()
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=date(2024, 1, 1),
        quantidade_total=10.0, valor_total=100.0, local_estoque=None,
    ))
    db.commit()
    return item


# --------------------------------------------------------------------------- #
# Treino
# --------------------------------------------------------------------------- #
def test_treinar_requer_admin(client, usuario_comum):
    resposta = client.post("/previsoes/treinar", headers=_auth(token_para(usuario_comum)))
    assert resposta.status_code == 403


def test_treinar_inicia_em_background_202(
    client, db_session, token_admin, empresa, item, serie_consumo, monkeypatch
):
    def fake_exec(empresa_id):
        modelo = treinamento.treinar_empresa(db_session, empresa_id, fabrica=fabrica_fake)
        predicao.gerar_previsoes(db_session, empresa_id, modelo, fabrica=fabrica_fake)
        previsoes_routers._TREINOS_EM_ANDAMENTO.discard(empresa_id)

    monkeypatch.setattr(previsoes_routers, "_executar_treino", fake_exec)

    resposta = client.post("/previsoes/treinar", headers=_auth(token_admin))
    assert resposta.status_code == 202

    modelos = client.get("/previsoes/modelos", headers=_auth(token_admin)).json()
    assert len(modelos) == 1
    assert modelos[0]["ativo"] is True


def test_treinar_conflito_409(client, token_admin, empresa):
    previsoes_routers._TREINOS_EM_ANDAMENTO.add(empresa.id)
    resposta = client.post("/previsoes/treinar", headers=_auth(token_admin))
    assert resposta.status_code == 409


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
def test_listar_modelos_retorna_metricas(client, db_session, token_admin, empresa):
    _modelo(db_session, empresa, "sarima", ativo=True, mape=12.5)
    resposta = client.get("/previsoes/modelos", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()[0]["mape"] == 12.5


def test_listar_modelos_isolado_por_empresa(client, db_session, token_admin, empresa, empresa_secundaria):
    _modelo(db_session, empresa, "sma")
    _modelo(db_session, empresa_secundaria, "sarima")
    resposta = client.get("/previsoes/modelos", headers=_auth(token_admin))
    assert len(resposta.json()) == 1


def test_ativar_modelo_rf11(client, db_session, token_admin, empresa):
    m1 = _modelo(db_session, empresa, "sma", ativo=True)
    m2 = _modelo(db_session, empresa, "sarima", ativo=False)
    resposta = client.post(f"/previsoes/modelos/{m2.id}/ativar", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True
    db_session.refresh(m1)
    assert m1.ativo is False


def test_ativar_modelo_inexistente_404(client, token_admin):
    resposta = client.post("/previsoes/modelos/99999/ativar", headers=_auth(token_admin))
    assert resposta.status_code == 404


# --------------------------------------------------------------------------- #
# Previsões e itens omitidos
# --------------------------------------------------------------------------- #
def test_listar_previsoes_paginado(client, db_session, token_admin, empresa, item):
    modelo = _modelo(db_session, empresa)
    for mes in range(1, 7):
        db_session.add(Previsao(
            empresa_id=empresa.id, modelo_id=modelo.id, item_id=item.id,
            periodo=date(2025, mes, 1), quantidade_prevista=100.0,
        ))
    db_session.commit()

    resposta = client.get("/previsoes/", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 6


def test_listar_previsoes_filtra_por_item(client, db_session, token_admin, empresa, item):
    outro = Item(empresa_id=empresa.id, codigo_item="X", descricao_item="Outro")
    db_session.add(outro)
    db_session.flush()
    modelo = _modelo(db_session, empresa)
    db_session.add(Previsao(
        empresa_id=empresa.id, modelo_id=modelo.id, item_id=item.id,
        periodo=date(2025, 1, 1), quantidade_prevista=100.0,
    ))
    db_session.add(Previsao(
        empresa_id=empresa.id, modelo_id=modelo.id, item_id=outro.id,
        periodo=date(2025, 1, 1), quantidade_prevista=50.0,
    ))
    db_session.commit()

    resposta = client.get(f"/previsoes/?item_id={item.id}", headers=_auth(token_admin))
    assert resposta.json()["total"] == 1


def test_itens_omitidos_lista_itens_curtos(client, db_session, token_admin, empresa):
    curto = _item_curto(db_session, empresa)
    resposta = client.get("/previsoes/itens-omitidos", headers=_auth(token_admin))
    assert resposta.status_code == 200
    ids = [o["item_id"] for o in resposta.json()]
    assert curto.id in ids


def test_status_treino_reflete_estado(client, token_admin, empresa):
    previsoes_routers._TREINOS_EM_ANDAMENTO.add(empresa.id)
    resposta = client.get("/previsoes/status-treino", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["em_andamento"] is True
