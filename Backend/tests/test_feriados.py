"""Testes do serviço de feriados (sincronização com feriados.dev via respx)."""

import logging
from datetime import date

from app.models.feriado_sincronizacao import FeriadoSincronizacao
from app.services import feriados_service as fs


# --------------------------------------------------------------------------- #
# Funções puras
# --------------------------------------------------------------------------- #
def test_normalizar_localidade_remove_acentos():
    assert fs._normalizar_localidade("São Paulo") == "SAO-PAULO"


def test_classificar_tipo_mapeia_national_para_nacional():
    assert fs._classificar_tipo({"type": "national"}) == "nacional"


def test_classificar_tipo_desconhecido_gera_warning(caplog):
    with caplog.at_level(logging.WARNING):
        tipo = fs._classificar_tipo({"type": "intergalactico"})
    assert tipo == "intergalactico"
    assert any("desconhecido" in r.message.lower() for r in caplog.records)


def test_extrair_lista_aceita_payload_lista():
    payload = [{"a": 1}, {"a": 2}]
    assert fs._extrair_lista(payload) == payload


def test_extrair_lista_aceita_chave_data():
    itens = [{"a": 1}]
    assert fs._extrair_lista({"data": itens}) == itens


def test_mapear_item_nacional_zera_uf_e_cidade():
    registro = fs._mapear_item(
        {"date": "2024-01-01", "name": "Confraternização", "type": "national"},
        "SC", "Joinville",
    )
    assert registro["uf"] is None
    assert registro["cidade"] is None
    assert registro["tipo"] == "nacional"


def test_mapear_item_municipal_preenche_uf_e_cidade():
    registro = fs._mapear_item(
        {"date": "2024-03-08", "name": "Aniversário", "type": "municipal"},
        "SC", "Joinville",
    )
    assert registro["uf"] == "SC"
    assert registro["cidade"] == "Joinville"


# --------------------------------------------------------------------------- #
# Sincronização e consulta (com rede mockada)
# --------------------------------------------------------------------------- #
def test_sincronizar_nao_repete_chamada_quando_ja_sincronizado(db_session, respx_mock):
    db_session.add(FeriadoSincronizacao(uf="SC", cidade="Joinville", ano=2024))
    db_session.commit()

    # Nenhuma rota mockada: se houvesse chamada HTTP, respx levantaria erro.
    fs.sincronizar_feriados(db_session, "SC", "Joinville", 2024)
    assert not respx_mock.calls


def test_obter_feriados_filtra_por_uf_e_cidade(db_session, feriados_mock):
    feriados = fs.obter_feriados(db_session, "SC", "Joinville", 2024)
    assert len(feriados) == 3
    datas = [f.data for f in feriados]
    assert datas == sorted(datas)


def test_esta_de_feriado_encontra_data(db_session, feriados_mock):
    feriado = fs.esta_de_feriado(db_session, date(2024, 1, 1), "SC", "Joinville")
    assert feriado is not None
    assert feriado.data == date(2024, 1, 1)


def test_esta_de_feriado_dia_comum_retorna_none(db_session, feriados_mock):
    assert fs.esta_de_feriado(db_session, date(2024, 6, 3), "SC", "Joinville") is None
