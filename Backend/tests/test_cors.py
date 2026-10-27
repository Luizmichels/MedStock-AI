"""Preflight de CORS (OPTIONS) para o front aberto por endereços locais."""

import pytest


def _preflight(client, origem: str):
    return client.options(
        "/auth/login",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


@pytest.mark.parametrize(
    "origem",
    ["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.0.15:3000", "http://localhost:3001"],
)
def test_preflight_aceita_front_local(client, origem):
    resposta = _preflight(client, origem)
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == origem


def test_preflight_recusa_origem_externa(client):
    assert _preflight(client, "https://site-qualquer.com").status_code == 400
