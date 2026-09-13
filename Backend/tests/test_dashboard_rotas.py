"""Testes de contrato das rotas do dashboard (RF09, RF12)."""

from datetime import date

from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _com_dados(db, empresa) -> Item:
    item = Item(empresa_id=empresa.id, codigo_item="MED001", descricao_item="Dipirona")
    db.add(item)
    db.flush()
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=date(2024, 1, 1),
        quantidade_total=10.0, valor_total=100.0, local_estoque="Central",
    ))
    db.commit()
    return item


def test_resumo_sem_dados_retorna_possui_dados_false(client, token_admin, empresa):
    resposta = client.get("/dashboard/resumo", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json()["possui_dados"] is False


def test_resumo_com_dados_retorna_kpis(client, db_session, token_admin, empresa):
    _com_dados(db_session, empresa)
    resposta = client.get("/dashboard/resumo", headers=_auth(token_admin))
    corpo = resposta.json()
    assert corpo["possui_dados"] is True
    assert corpo["kpis"]["valor_total_consumido"] == 100.0


def test_consumo_mensal_retorna_lista(client, db_session, token_admin, empresa):
    _com_dados(db_session, empresa)
    resposta = client.get("/dashboard/consumo-mensal", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert len(resposta.json()) >= 1


def test_top_itens_formato_invalido_da_422(client, token_admin):
    resposta = client.get("/dashboard/top-itens?por=xpto", headers=_auth(token_admin))
    assert resposta.status_code == 422


def test_classificacao_abc_rota(client, db_session, token_admin, empresa):
    resposta = client.get("/dashboard/classificacao-abc", headers=_auth(token_admin))
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_dashboard_sem_autenticacao_rejeitado(client):
    resposta = client.get("/dashboard/resumo")
    assert resposta.status_code in (401, 403)
