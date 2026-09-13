"""Testes do registro de logs de execução (RNF09)."""

from app.models.logs_execucao import LogExecucao
from app.services import data_pipeline_service as dp
from app.services import log_service


def test_registrar_cria_log(db_session, empresa):
    log = log_service.registrar(db_session, "importacao", "info", "ok", empresa_id=empresa.id)
    assert log.id is not None
    assert log.modulo == "importacao"


def test_registrar_com_contexto_json(db_session, empresa):
    log = log_service.registrar(
        db_session, "treino", "info", "treinado", empresa_id=empresa.id,
        contexto={"algoritmo": "sma", "n_itens": 3},
    )
    recuperado = db_session.query(LogExecucao).get(log.id)
    assert recuperado.contexto["algoritmo"] == "sma"


def test_listar_logs_isolado_por_empresa(db_session, empresa, empresa_secundaria):
    log_service.registrar(db_session, "importacao", "info", "a", empresa_id=empresa.id)
    log_service.registrar(db_session, "importacao", "info", "b", empresa_id=empresa_secundaria.id)
    logs = log_service.listar_logs(db_session, empresa.id)
    assert len(logs) == 1


def test_listar_logs_filtra_por_modulo(db_session, empresa):
    log_service.registrar(db_session, "importacao", "info", "a", empresa_id=empresa.id)
    log_service.registrar(db_session, "treino", "info", "b", empresa_id=empresa.id)
    logs = log_service.listar_logs(db_session, empresa.id, modulo="treino")
    assert len(logs) == 1
    assert logs[0].modulo == "treino"


def test_pipeline_registra_log_de_importacao(db_session, empresa, usuario_admin, csv_valido):
    dp.processar_arquivo(db_session, csv_valido, "consumo.csv", empresa.id, usuario_admin.id)
    logs = log_service.listar_logs(db_session, empresa.id, modulo="importacao")
    assert len(logs) == 1
    assert logs[0].nivel == "info"
