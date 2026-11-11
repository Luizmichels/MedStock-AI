"""Logs da aplicação: uma linha JSON por evento em produção

Toda linha registrada durante uma requisição recebe o contexto dela
(`request_id`, `usuario_id`, `empresa_id`), inclusive as escritas pelas
BackgroundTasks (importação e treino), que rodam depois da resposta.

Os logs saem do sistema CloudWatch. Só entram identificadores
numéricos e dados técnicos. Nunca registrar e-mail, nome, senha, token,
cabeçalhos
"""
import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

_contexto: ContextVar[dict | None] = ContextVar("contexto_log", default=None)

_logger_acesso = logging.getLogger("app.acesso")


def iniciar_contexto(request_id: str) -> dict:
    contexto = {"request_id": request_id}
    _contexto.set(contexto)
    return contexto


def atualizar_contexto(**campos) -> None:
    """Acrescenta campos ao contexto da requisição atual"""
    contexto = _contexto.get()
    if contexto is not None:
        contexto.update({k: v for k, v in campos.items() if v is not None})


def _campos(record: logging.LogRecord) -> dict:
    campos = dict(_contexto.get() or {})
    dados = getattr(record, "dados", None)
    if isinstance(dados, dict):
        campos.update(dados)
    return campos


class FormatoJson(logging.Formatter):
    """Uma linha JSON por evento, para filtrar e gerar métricas no CloudWatch"""

    def __init__(self, versao: str):
        super().__init__()
        self.versao = versao

    def format(self, record: logging.LogRecord) -> str:
        linha = {
            "momento": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
            **_campos(record),
            "versao": self.versao,
        }
        if record.exc_info:
            linha["excecao"] = self.formatException(record.exc_info)
        return json.dumps(linha, ensure_ascii=False, default=str)


class FormatoTexto(logging.Formatter):
    """Texto legível para desenvolvimento, com os campos no fim da linha"""

    def __init__(self):
        super().__init__("%(asctime)s | %(levelname)s | %(name)s | %(message)s%(campos)s")

    def format(self, record: logging.LogRecord) -> str:
        campos = _campos(record)
        record.campos = (
            " | " + " ".join(f"{k}={v}" for k, v in campos.items()) if campos else ""
        )
        return super().format(record)


def configurar_logs(*, json_: bool, versao: str, nivel: int = logging.INFO) -> None:
    """Aplica o formato à raiz e faz o Uvicorn usar o mesmo formato"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatoJson(versao) if json_ else FormatoTexto())
    handler._medstock = True  # marca para a troca acima

    raiz = logging.getLogger()
    for antigo in [h for h in raiz.handlers if getattr(h, "_medstock", False)]:
        raiz.removeHandler(antigo)
    raiz.addHandler(handler)
    raiz.setLevel(nivel)

    # O Uvicorn configura os próprios handlers antes de importar a API
    for nome in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(nome)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True

    # O httpx (API de feriados) registra a URL completa de cada chamada em INFO.
    for nome in ("httpx", "httpcore"):
        logging.getLogger(nome).setLevel(logging.WARNING)


class MiddlewareLogs:
    """Uma linha por requisição, com `request_id` devolvido em `X-Request-ID`"""

    def __init__(self, app, ignorar: tuple[str, ...] = ("/health",)):
        self.app = app
        self.ignorar = ignorar

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        iniciar_contexto(request_id)
        inicio = time.perf_counter()
        estado = {"status": 500, "registrado": False}

        def registrar() -> None:
            if estado["registrado"] or scope["path"] in self.ignorar:
                return
            estado["registrado"] = True
            status = estado["status"]
            # Rota com parâmetros (/itens/{item_id}), nunca a URL real
            rota = getattr(scope.get("route"), "path", None)
            _logger_acesso.log(
                logging.ERROR if status >= 500 else logging.INFO,
                "requisicao",
                extra={
                    "dados": {
                        "metodo": scope["method"],
                        "rota": rota,
                        "status": status,
                        "duracao_ms": round((time.perf_counter() - inicio) * 1000),
                    }
                },
            )

        async def enviar(message):
            if message["type"] == "http.response.start":
                estado["status"] = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", request_id.encode()),
                    ],
                }
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body"):
                registrar()

        try:
            await self.app(scope, receive, enviar)
        except Exception:
            # Exceção não tratada o handler genérico responde 500 por fora daqui.
            estado["status"] = 500
            registrar()
            raise
        registrar()
