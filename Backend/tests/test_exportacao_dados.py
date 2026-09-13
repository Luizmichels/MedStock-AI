"""Testes da camada de dados e dos geradores de relatório (RF10, RN04)."""

from datetime import date
from io import BytesIO

import openpyxl
import pandas as pd

from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.services.exportacao import dados
from app.services.exportacao.excel import gerar_xlsx
from app.services.exportacao.pdf import gerar_pdf


def _item(db, empresa, codigo="MED001") -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=f"Item {codigo}")
    db.add(item)
    db.flush()
    return item


def _modelo(db, empresa, algoritmo="sma") -> ModeloTreinado:
    modelo = ModeloTreinado(
        empresa_id=empresa.id, algoritmo=algoritmo, ativo=True, rmse=5.0, mae=3.0, mape=12.0
    )
    db.add(modelo)
    db.flush()
    return modelo


def _previsao(db, empresa, modelo, item, periodo) -> None:
    db.add(Previsao(
        empresa_id=empresa.id, modelo_id=modelo.id, item_id=item.id,
        periodo=periodo, quantidade_prevista=100.0,
        intervalo_inferior=80.0, intervalo_superior=120.0,
    ))


def _tratado(db, empresa, item, periodo, qtd, valor) -> None:
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=periodo,
        quantidade_total=qtd, valor_total=valor, local_estoque="Central",
    ))


# --------------------------------------------------------------------------- #
# Camada de dados
# --------------------------------------------------------------------------- #
def test_montar_relatorio_previsoes_colunas(db_session, empresa):
    df = dados.montar_relatorio_previsoes(db_session, empresa.id)
    assert list(df.columns) == dados.COLUNAS_PREVISOES


def test_montar_relatorio_previsoes_lista_dados(db_session, empresa):
    item = _item(db_session, empresa)
    modelo = _modelo(db_session, empresa)
    _previsao(db_session, empresa, modelo, item, date(2025, 1, 1))
    db_session.commit()
    df = dados.montar_relatorio_previsoes(db_session, empresa.id)
    assert len(df) == 1


def test_montar_relatorio_previsoes_isolado_por_empresa(db_session, empresa, empresa_secundaria):
    item = _item(db_session, empresa)
    modelo = _modelo(db_session, empresa)
    _previsao(db_session, empresa, modelo, item, date(2025, 1, 1))

    item2 = _item(db_session, empresa_secundaria, "OUTRO")
    modelo2 = _modelo(db_session, empresa_secundaria)
    _previsao(db_session, empresa_secundaria, modelo2, item2, date(2025, 1, 1))
    db_session.commit()

    df = dados.montar_relatorio_previsoes(db_session, empresa.id)
    assert len(df) == 1


def test_montar_relatorio_consumo_colunas(db_session, empresa):
    df = dados.montar_relatorio_consumo(db_session, empresa.id)
    assert list(df.columns) == dados.COLUNAS_CONSUMO


def test_montar_relatorio_consumo_filtra_data(db_session, empresa):
    item = _item(db_session, empresa)
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100)
    _tratado(db_session, empresa, item, date(2024, 6, 1), 20, 200)
    db_session.commit()
    df = dados.montar_relatorio_consumo(db_session, empresa.id, data_inicio=date(2024, 3, 1))
    assert len(df) == 1


def test_montar_relatorio_metricas_colunas(db_session, empresa):
    df = dados.montar_relatorio_metricas(db_session, empresa.id)
    assert list(df.columns) == dados.COLUNAS_METRICAS


def test_montar_relatorio_metricas_lista_modelos(db_session, empresa):
    _modelo(db_session, empresa, "sma")
    _modelo(db_session, empresa, "sarima")
    db_session.commit()
    df = dados.montar_relatorio_metricas(db_session, empresa.id)
    assert len(df) == 2


# --------------------------------------------------------------------------- #
# Geradores
# --------------------------------------------------------------------------- #
def test_gerar_pdf_retorna_bytes_com_assinatura_pdf():
    df = pd.DataFrame({"Código": ["A"], "Valor": [10]})
    conteudo = gerar_pdf(df, "Teste")
    assert conteudo[:4] == b"%PDF"


def test_gerar_pdf_vazio_nao_quebra():
    df = pd.DataFrame(columns=["Código", "Valor"])
    conteudo = gerar_pdf(df, "Vazio")
    assert conteudo[:4] == b"%PDF"


def test_gerar_xlsx_abre_com_openpyxl():
    df = pd.DataFrame({"Código": ["A"], "Valor": [10]})
    conteudo = gerar_xlsx({"Aba": df})
    planilha = openpyxl.load_workbook(BytesIO(conteudo))
    assert "Aba" in planilha.sheetnames
