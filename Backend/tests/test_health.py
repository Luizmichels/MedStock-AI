from sqlalchemy.exc import SQLAlchemyError


def test_health_retorna_ok_quando_banco_disponivel(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "status": "ok",
        "database": "ok",
    }


def test_health_retorna_503_quando_banco_indisponivel(
    client,
    db_session,
    monkeypatch,
):
    def simular_falha(*args, **kwargs):
        raise SQLAlchemyError("Banco indisponível")

    monkeypatch.setattr(db_session, "execute", simular_falha)

    resposta = client.get("/health")

    assert resposta.status_code == 503
    assert resposta.json() == {
        "status": "degraded",
        "database": "unavailable",
    }