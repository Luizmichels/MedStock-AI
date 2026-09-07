"""Testes de contrato das rotas de itens (RF03)."""

from app.models.classificacao_abc import ClassificacaoABC
from app.models.itens import Item


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _item(db, empresa, codigo, descricao="Item") -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=descricao)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_listar_itens_retorna_pagina(client, db_session, token_admin, empresa):
    _item(db_session, empresa, "MED001")
    resposta = client.get("/itens/", headers=_auth(token_admin))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert corpo["itens"][0]["codigo_item"] == "MED001"


def test_listar_itens_sem_autenticacao_rejeitado(client):
    resposta = client.get("/itens/")
    assert resposta.status_code in (401, 403)


def test_detalhe_item_inclui_meses_de_historico(client, db_session, token_admin, empresa, item, serie_consumo):
    resposta = client.get(f"/itens/{item.id}", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["meses_de_historico"] == 18


def test_detalhe_item_inexistente_404(client, token_admin):
    resposta = client.get("/itens/99999", headers=_auth(token_admin))
    assert resposta.status_code == 404


def test_detalhe_item_de_outra_empresa_404(client, db_session, token_admin, empresa_secundaria):
    alheio = _item(db_session, empresa_secundaria, "OUTRO")
    resposta = client.get(f"/itens/{alheio.id}", headers=_auth(token_admin))
    assert resposta.status_code == 404
