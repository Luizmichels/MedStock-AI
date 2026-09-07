"""Testes de contrato das rotas de consumos e série temporal (RF03)."""

from datetime import date

from app.models.consumo import Consumo
from app.models.importacoes import Importacao


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def _consumo(db, empresa, item, imp, data_, *, local="Central") -> None:
    db.add(Consumo(
        empresa_id=empresa.id, importacao_id=imp.id, item_id=item.id,
        data=data_, quantidade=10, valor=100, local_estoque=local,
    ))


def test_listar_consumos_retorna_pagina(client, db_session, token_admin, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item, imp, date(2024, 1, 10))
    db_session.commit()

    resposta = client.get("/consumos/", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1


def test_listar_consumos_filtra_por_item(client, db_session, token_admin, empresa, usuario_admin, item):
    from app.models.itens import Item
    outro = Item(empresa_id=empresa.id, codigo_item="MED999", descricao_item="Outro")
    db_session.add(outro)
    db_session.flush()
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item, imp, date(2024, 1, 10))
    _consumo(db_session, empresa, outro, imp, date(2024, 1, 11))
    db_session.commit()

    resposta = client.get(f"/consumos/?item_id={item.id}", headers=_auth(token_admin))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert corpo["itens"][0]["item_id"] == item.id


def test_listar_consumos_sem_autenticacao_rejeitado(client):
    resposta = client.get("/consumos/")
    assert resposta.status_code in (401, 403)


def test_serie_temporal_retorna_pontos_ordenados(client, db_session, token_admin, empresa, item, serie_consumo):
    resposta = client.get(f"/consumos/serie/{item.id}", headers=_auth(token_admin))
    assert resposta.status_code == 200
    pontos = resposta.json()
    assert len(pontos) == 18
    periodos = [p["periodo"] for p in pontos]
    assert periodos == sorted(periodos)


def test_serie_temporal_item_sem_dados_retorna_lista_vazia(client, db_session, token_admin, empresa, item):
    resposta = client.get(f"/consumos/serie/{item.id}", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json() == []
