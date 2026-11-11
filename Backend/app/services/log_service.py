import logging

from sqlalchemy.orm import Session

from app.models.logs_execucao import LogExecucao

_logger = logging.getLogger("app.execucao")
_NIVEIS = {"debug": logging.DEBUG, "info": logging.INFO, "aviso": logging.WARNING, "erro": logging.ERROR}


def registrar(
    db: Session,
    modulo: str,
    nivel: str,
    mensagem: str,
    *,
    empresa_id: int | None = None,
    contexto: dict | None = None,
) -> LogExecucao:
    log = LogExecucao(
        empresa_id=empresa_id,
        modulo=modulo,
        nivel=nivel,
        mensagem=mensagem,
        contexto=contexto,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # log da aplicação, para os erros de importação e treino chegarem aos alertas
    _logger.log(
        _NIVEIS.get(nivel, logging.INFO),
        mensagem,
        extra={"dados": {"modulo": modulo, "empresa_id": empresa_id}},
    )
    return log


def listar_logs(
    db: Session,
    empresa_id: int,
    *,
    modulo: str | None = None,
    nivel: str | None = None,
    limite: int = 100,
) -> list[LogExecucao]:
    query = db.query(LogExecucao).filter(LogExecucao.empresa_id == empresa_id)
    if modulo:
        query = query.filter(LogExecucao.modulo == modulo)
    if nivel:
        query = query.filter(LogExecucao.nivel == nivel)
    return query.order_by(LogExecucao.criado_em.desc()).limit(limite).all()
