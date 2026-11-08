"""Testes de proxy headers e validação de IP real (X-Forwarded-For)."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.rate_limit import LimitadorDeTaxa


def test_proxy_headers_reflete_ip_em_request_client_host():
    """Valida que requisições contendo X-Forwarded-For refletem o IP correto

    no objeto request.client.host quando sob o ProxyHeadersMiddleware.
    """
    app_teste = FastAPI()
    captura_ip = {}

    @app_teste.get("/teste-ip")
    def rota(request: Request):
        captura_ip["host"] = request.client.host if request.client else None
        return {"ip": captura_ip["host"]}

    app_com_proxy = ProxyHeadersMiddleware(app_teste, trusted_hosts="*")
    client = TestClient(app_com_proxy)

    ip_esperado = "203.0.113.195"
    resposta = client.get("/teste-ip", headers={"X-Forwarded-For": ip_esperado})

    assert resposta.status_code == 200
    assert resposta.json()["ip"] == ip_esperado
    assert captura_ip["host"] == ip_esperado


def test_proxy_headers_com_multiplos_proxies_em_cadeia():
    """Quando o cabeçalho X-Forwarded-For contém múltiplos IPs (cliente, proxy1),

    o ProxyHeadersMiddleware deve atribuir o IP do cliente original a request.client.host.
    """
    app_teste = FastAPI()
    captura_ip = {}

    @app_teste.get("/teste-multiplos-ips")
    def rota(request: Request):
        captura_ip["host"] = request.client.host if request.client else None
        return {"ip": captura_ip["host"]}

    app_com_proxy = ProxyHeadersMiddleware(app_teste, trusted_hosts="*")
    client = TestClient(app_com_proxy)

    ip_cliente = "198.51.100.42"
    resposta = client.get(
        "/teste-multiplos-ips",
        headers={"X-Forwarded-For": f"{ip_cliente}, 172.18.0.2"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["ip"] == ip_cliente
    assert captura_ip["host"] == ip_cliente


def test_rate_limit_independente_por_ip_com_proxy_headers():
    """Valida que clientes distintos com IPs diferentes via X-Forwarded-For

    não compartilham o rate limit sob ProxyHeadersMiddleware.
    """
    app_teste = FastAPI()
    limitador = LimitadorDeTaxa(limite=2, janela_segundos=60)

    @app_teste.get("/teste-rate-limit")
    def rota(request: Request):
        limitador(request)
        return {"status": "ok"}

    app_com_proxy = ProxyHeadersMiddleware(app_teste, trusted_hosts="*")
    client = TestClient(app_com_proxy)

    ip_a = "203.0.113.1"
    ip_b = "203.0.113.2"

    # Cliente A atinge o limite de 2 requisições
    assert client.get("/teste-rate-limit", headers={"X-Forwarded-For": ip_a}).status_code == 200
    assert client.get("/teste-rate-limit", headers={"X-Forwarded-For": ip_a}).status_code == 200
    assert client.get("/teste-rate-limit", headers={"X-Forwarded-For": ip_a}).status_code == 429

    # Cliente B faz requisição e não é bloqueado pelo consumo do Cliente A
    assert client.get("/teste-rate-limit", headers={"X-Forwarded-For": ip_b}).status_code == 200

