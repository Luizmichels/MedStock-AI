"""Logs estruturados: formato, contexto da requisição e LGPD (app/core/logs.py)."""

import json
import logging
import sys

import pytest
from fastapi.testclient import TestClient

from app.core.logs import FormatoJson, FormatoTexto, configurar_logs
from app.database import get_db
from app.main import app
from app.models.importacoes import Importacao


class _Coletor(logging.Handler):
    """Formata cada linha no momento em que é escrita, como o handler real."""

    def __init__(self):
        super().__init__()
        self.setFormatter(FormatoJson("teste"))
        self.linhas: list[str] = []

    def emit(self, record):
        self.linhas.append(self.format(record))


@pytest.fixture
def linhas():
    coletor = _Coletor()
    raiz = logging.getLogger()
    raiz.addHandler(coletor)
    yield coletor.linhas
    raiz.removeHandler(coletor)


def _eventos(linhas: list[str]) -> list[dict]:
    return [json.loads(linha) for linha in linhas]


def _acessos(linhas: list[str]) -> list[dict]:
    return [e for e in _eventos(linhas) if e["logger"] == "app.acesso"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Formato ---------------------------------------------------------------


def test_formato_json_gera_uma_linha_valida_com_os_campos():
    record = logging.makeLogRecord(
        {"name": "app.x", "levelname": "INFO", "levelno": logging.INFO,
         "msg": "importou %s itens", "args": (3,), "dados": {"modulo": "importacao"}}
    )
    linha = FormatoJson("sha-abc1234").format(record)

    assert "\n" not in linha
    evento = json.loads(linha)
    assert evento["mensagem"] == "importou 3 itens"
    assert evento["nivel"] == "INFO"
    assert evento["logger"] == "app.x"
    assert evento["modulo"] == "importacao"
    assert evento["versao"] == "sha-abc1234"
    assert "momento" in evento


def test_formato_json_inclui_o_stack_trace():
    try:
        raise ValueError("falhou")
    except ValueError:
        record = logging.makeLogRecord(
            {"name": "app.x", "levelname": "ERROR", "levelno": logging.ERROR,
             "msg": "erro", "exc_info": sys.exc_info()}
        )
    evento = json.loads(FormatoJson("t").format(record))
    assert "ValueError: falhou" in evento["excecao"]


def test_formato_texto_continua_legivel():
    record = logging.makeLogRecord(
        {"name": "app.x", "levelname": "INFO", "levelno": logging.INFO,
         "msg": "ola", "dados": {"status": 200}}
    )
    linha = FormatoTexto().format(record)
    assert "| INFO | app.x | ola | status=200" in linha
    with pytest.raises(json.JSONDecodeError):
        json.loads(linha)


def test_configurar_logs_nao_duplica_handler_e_desliga_o_acesso_do_uvicorn():
    try:
        configurar_logs(json_=True, versao="t")
        configurar_logs(json_=True, versao="t")
        nossos = [h for h in logging.getLogger().handlers if getattr(h, "_medstock", False)]
        assert len(nossos) == 1
        assert isinstance(nossos[0].formatter, FormatoJson)
        assert logging.getLogger("uvicorn.access").disabled
        assert logging.getLogger("uvicorn.error").propagate
    finally:
        configurar_logs(json_=False, versao="local")


# --- Linha por requisição --------------------------------------------------


def test_requisicao_gera_linha_com_request_id_igual_ao_cabecalho(client, linhas):
    resposta = client.get("/nao-existe/123")

    request_id = resposta.headers["x-request-id"]
    assert len(request_id) == 32
    [acesso] = _acessos(linhas)
    assert acesso["request_id"] == request_id
    assert acesso["metodo"] == "GET"
    assert acesso["status"] == 404
    assert acesso["rota"] is None  # sem rota: a URL real não entra
    assert isinstance(acesso["duracao_ms"], int)
    assert "nao-existe" not in "".join(linhas)


def test_cada_requisicao_tem_um_request_id_novo(client):
    a = client.get("/nao-existe").headers["x-request-id"]
    b = client.get("/nao-existe").headers["x-request-id"]
    assert a != b


def test_health_nao_entra_no_log(client, linhas):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert "x-request-id" in resposta.headers
    assert _acessos(linhas) == []


def test_rota_com_parametros_usuario_e_empresa(client, linhas, token_admin, usuario_admin, item):
    resposta = client.get(f"/itens/{item.id}?busca=segredo-na-url", headers=_auth(token_admin))
    assert resposta.status_code == 200

    [acesso] = _acessos(linhas)
    assert acesso["rota"] == "/itens/{item_id}"
    assert acesso["status"] == 200
    assert acesso["usuario_id"] == usuario_admin.id
    assert acesso["empresa_id"] == usuario_admin.empresa_id
    assert "segredo-na-url" not in "".join(linhas)


def test_email_e_corpo_da_requisicao_nao_entram_no_log(client, linhas):
    resposta = client.post(
        "/auth/login", json={"email": "pessoa@exemplo.com", "senha": "SenhaSecreta1!"}
    )
    assert resposta.status_code == 401
    texto = "".join(linhas)
    assert "pessoa@exemplo.com" not in texto
    assert "SenhaSecreta1!" not in texto
    assert _acessos(linhas)[0]["rota"] == "/auth/login"


def test_excecao_nao_tratada_devolve_500_generico_e_registra_stack_trace(client, linhas, token_admin):
    def _falha():
        raise RuntimeError("banco caiu")

    app.dependency_overrides[get_db] = _falha
    cliente = TestClient(app, raise_server_exceptions=False)
    resposta = cliente.get("/itens/", headers=_auth(token_admin))

    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno do servidor."}
    eventos = _eventos(linhas)
    [acesso] = [e for e in eventos if e["logger"] == "app.acesso"]
    assert acesso["status"] == 500
    assert acesso["nivel"] == "ERROR"
    [erro] = [e for e in eventos if e["mensagem"].startswith("Exceção não tratada")]
    assert erro["mensagem"] == "Exceção não tratada: RuntimeError"
    assert "RuntimeError: banco caiu" in erro["excecao"]
    assert erro["request_id"] == acesso["request_id"]


# --- Contexto nas tarefas em segundo plano e no log_service ----------------


def test_importacao_em_segundo_plano_herda_o_request_id(
    client, db_session, token_admin, csv_valido, monkeypatch, linhas
):
    from app.routers import importacoes_routers
    from app.services.data_pipeline_service import executar_pipeline

    def fake_bg(importacao_id, conteudo, nome_arquivo, empresa_id):
        importacao = db_session.query(Importacao).filter(Importacao.id == importacao_id).first()
        executar_pipeline(db_session, importacao, conteudo, nome_arquivo, empresa_id)

    monkeypatch.setattr(importacoes_routers, "_processar_importacao_background", fake_bg)

    resposta = client.post(
        "/importacoes/upload",
        headers=_auth(token_admin),
        files={"arquivo": ("planilha-do-hospital.csv", csv_valido, "text/csv")},
    )
    assert resposta.status_code == 202
    request_id = resposta.headers["x-request-id"]

    eventos = _eventos(linhas)
    pipeline = [e for e in eventos if e["logger"] == "app.services.data_pipeline_service"]
    assert pipeline and all(e["request_id"] == request_id for e in pipeline)

    # O log_service também escreve no log da aplicação, sem o nome do arquivo.
    [execucao] = [e for e in eventos if e["logger"] == "app.execucao"]
    assert execucao["modulo"] == "importacao"
    assert execucao["request_id"] == request_id
    assert "planilha-do-hospital" not in "".join(linhas)


def test_email_enviado_nao_registra_o_destinatario(monkeypatch, linhas):
    from app.services import email_service

    class _SmtpFalso:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, *args):
            pass

        def send_message(self, *args):
            pass

    monkeypatch.setattr(email_service.smtplib, "SMTP", _SmtpFalso)
    email_service.enviar_email("pessoa@exemplo.com", "Ative sua conta - MedStock AI", "t", "<p>t</p>")

    texto = "".join(linhas)
    assert "Ative sua conta" in texto
    assert "pessoa@exemplo.com" not in texto
