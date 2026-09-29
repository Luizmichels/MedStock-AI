"""Testes de contrato das rotas de previsão diária."""

from datetime import date, timedelta

from app.models.consumo import Consumo
from app.models.importacoes import Importacao


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_consumo_denso(db, empresa, usuario, item, dias=40):
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    inicio = date(2024, 1, 1)
    for i in range(dias):
        db.add(Consumo(
            empresa_id=empresa.id, importacao_id=imp.id, item_id=item.id,
            data=inicio + timedelta(days=i), quantidade=10, valor=10, local_estoque="Central",
        ))
    db.commit()


def test_gerar_diaria_e_consultar_resumo_e_detalhe(
    client, db_session, token_admin, empresa, usuario_admin, item, monkeypatch
):
    _seed_consumo_denso(db_session, empresa, usuario_admin, item)

    # Faz o worker de background rodar na sessão de teste.
    from app.routers import previsoes_routers
    from app.services.ml import previsao_diaria as diaria

    def fake_worker(empresa_id):
        diaria.gerar_previsoes_diarias(db_session, empresa_id)

    monkeypatch.setattr(previsoes_routers, "_executar_previsao_diaria", fake_worker)

    resp = client.post("/previsoes/diaria/gerar", headers=_auth(token_admin))
    assert resp.status_code == 202

    resumo = client.get("/previsoes/diaria/resumo", headers=_auth(token_admin))
    assert resumo.status_code == 200
    corpo = resumo.json()
    assert len(corpo) == 1
    assert corpo[0]["item_id"] == item.id
    assert corpo[0]["trinta_dias"] >= corpo[0]["sete_dias"]

    detalhe = client.get(f"/previsoes/diaria/{item.id}", headers=_auth(token_admin))
    assert detalhe.status_code == 200
    d = detalhe.json()
    assert len(d["dias"]) == diaria.HORIZONTE_DIARIO
    assert d["horizontes"]["proximo_dia"] >= 0


def test_detalhe_diario_sem_previsao_404(client, token_admin, empresa):
    resp = client.get("/previsoes/diaria/99999", headers=_auth(token_admin))
    assert resp.status_code == 404


def test_gerar_diaria_exige_admin(client, usuario_comum):
    from tests.conftest import token_para

    resp = client.post("/previsoes/diaria/gerar", headers=_auth(token_para(usuario_comum)))
    assert resp.status_code == 403
