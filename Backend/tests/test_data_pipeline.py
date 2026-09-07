"""Testes do pipeline de importação (RF04 / FA02)."""

from datetime import date
from io import BytesIO

import pandas as pd
import pytest

from app.models.consumo import Consumo
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.services import data_pipeline_service as dp


# --------------------------------------------------------------------------- #
# Leitura de arquivos
# --------------------------------------------------------------------------- #
def test_ler_csv_com_separador_ponto_e_virgula():
    conteudo = "codigo_item;quantidade\nMED001;10".encode("utf-8")
    df = dp._ler_arquivo(conteudo, "consumo.csv")
    assert list(df.columns) == ["codigo_item", "quantidade"]
    assert df.iloc[0]["codigo_item"] == "MED001"


def test_ler_csv_com_separador_virgula_e_latin1():
    conteudo = "codigo_item,descricao\nMED001,Solução".encode("latin-1")
    df = dp._ler_arquivo(conteudo, "consumo.csv")
    # Cai no fallback vírgula+latin-1 (uma única coluna no parse ';').
    assert "descricao" in df.columns
    assert df.iloc[0]["descricao"] == "Solução"


def test_ler_excel_xlsx():
    buffer = BytesIO()
    pd.DataFrame({"codigo_item": ["MED001"], "quantidade": [5]}).to_excel(buffer, index=False)
    df = dp._ler_arquivo(buffer.getvalue(), "consumo.xlsx")
    assert df.iloc[0]["codigo_item"] == "MED001"


def test_ler_arquivo_formato_nao_suportado_levanta_erro():
    with pytest.raises(ValueError):
        dp._ler_arquivo(b"qualquer", "consumo.txt")


# --------------------------------------------------------------------------- #
# Normalização de colunas
# --------------------------------------------------------------------------- #
def test_normalizar_colunas_aplica_aliases():
    df = pd.DataFrame(columns=["cod", "qtd", "valor_total", "setor"])
    resultado = dp._normalizar_colunas(df)
    assert "codigo_item" in resultado.columns
    assert "quantidade" in resultado.columns
    assert "valor" in resultado.columns
    assert "local_estoque" in resultado.columns


def test_normalizar_colunas_remove_espacos_e_maiusculas():
    df = pd.DataFrame(columns=["Codigo Item", "  DATA  "])
    resultado = dp._normalizar_colunas(df)
    assert "codigo_item" in resultado.columns
    assert "data" in resultado.columns


# --------------------------------------------------------------------------- #
# Validação de colunas
# --------------------------------------------------------------------------- #
def test_validar_colunas_faltando_levanta_erro():
    df = pd.DataFrame(columns=["codigo_item", "descricao_item", "quantidade"])
    with pytest.raises(ValueError, match="data"):
        dp._validar_colunas(df)


# --------------------------------------------------------------------------- #
# Parse de data
# --------------------------------------------------------------------------- #
def test_parsear_data_aceita_quatro_formatos():
    esperado = date(2024, 3, 15)
    assert dp._parsear_data("15/03/2024") == esperado
    assert dp._parsear_data("2024-03-15") == esperado
    assert dp._parsear_data("15-03-2024") == esperado
    assert dp._parsear_data("2024/03/15") == esperado


def test_parsear_data_invalida_retorna_none():
    assert dp._parsear_data("bananas") is None


# --------------------------------------------------------------------------- #
# Limpeza de dados
# --------------------------------------------------------------------------- #
def _df_base(linhas: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(linhas)


def test_limpar_dados_remove_duplicatas():
    linha = {
        "codigo_item": "MED001",
        "descricao_item": "Dipirona",
        "data": "01/01/2024",
        "quantidade": "10",
        "valor": "5",
        "local_estoque": "Central",
    }
    df = _df_base([linha, dict(linha)])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 1
    assert erros == []


def test_limpar_dados_rejeita_quantidade_negativa():
    df = _df_base([{
        "codigo_item": "MED001", "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "-3", "valor": "5", "local_estoque": "Central",
    }])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 0
    assert any("quantidade" in e for e in erros)


def test_limpar_dados_rejeita_valor_zero():
    df = _df_base([{
        "codigo_item": "MED001", "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "10", "valor": "0", "local_estoque": "Central",
    }])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 0
    assert any("valor" in e for e in erros)


def test_limpar_dados_reporta_campo_nulo_com_numero_da_linha():
    df = _df_base([{
        "codigo_item": None, "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "10", "valor": "5", "local_estoque": "Central",
    }])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 0
    # header é a linha 1, então a primeira linha de dados é a 2.
    assert any("linha 2" in e for e in erros)


# --------------------------------------------------------------------------- #
# Upsert de item
# --------------------------------------------------------------------------- #
def test_upsert_item_cria_item_novo(db_session, empresa):
    item = dp._upsert_item(db_session, empresa.id, "MED999", "Novo Item")
    assert item.id is not None
    assert item.codigo_item == "MED999"


def test_upsert_item_reutiliza_item_existente(db_session, empresa, item):
    reutilizado = dp._upsert_item(db_session, empresa.id, item.codigo_item, item.descricao_item)
    assert reutilizado.id == item.id


# --------------------------------------------------------------------------- #
# Agregação de consumos tratados
# --------------------------------------------------------------------------- #
def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="consumo.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def _consumo(db, empresa, item, importacao, *, data_, quantidade, valor, local="Central"):
    db.add(Consumo(
        empresa_id=empresa.id, importacao_id=importacao.id, item_id=item.id,
        data=data_, quantidade=quantidade, valor=valor, local_estoque=local,
    ))


def test_agregar_consumos_soma_por_item_e_mes(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item, imp, data_=date(2024, 1, 5), quantidade=10, valor=100)
    _consumo(db_session, empresa, item, imp, data_=date(2024, 1, 20), quantidade=15, valor=150)
    db_session.commit()

    dp._agregar_consumos_tratados(db_session, empresa.id)
    db_session.commit()

    tratados = db_session.query(ConsumoTratado).filter(
        ConsumoTratado.empresa_id == empresa.id
    ).all()
    assert len(tratados) == 1
    assert tratados[0].quantidade_total == 25
    assert tratados[0].periodo == date(2024, 1, 1)


def test_agregar_consumos_preenche_valor_total(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item, imp, data_=date(2024, 2, 1), quantidade=10, valor=100)
    _consumo(db_session, empresa, item, imp, data_=date(2024, 2, 10), quantidade=5, valor=50)
    db_session.commit()

    dp._agregar_consumos_tratados(db_session, empresa.id)
    db_session.commit()

    tratado = db_session.query(ConsumoTratado).filter(
        ConsumoTratado.empresa_id == empresa.id
    ).one()
    assert tratado.valor_total == 150


# --------------------------------------------------------------------------- #
# Orquestração completa
# --------------------------------------------------------------------------- #
def test_processar_arquivo_status_concluido(db_session, empresa, usuario_admin, csv_valido):
    importacao = dp.processar_arquivo(
        db_session, csv_valido, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.status == "concluido"
    assert importacao.registros_validos == 3


def test_processar_arquivo_com_erro_marca_status_erro(db_session, empresa, usuario_admin, csv_invalido):
    importacao = dp.processar_arquivo(
        db_session, csv_invalido, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.status == "erro"
    assert importacao.erros
