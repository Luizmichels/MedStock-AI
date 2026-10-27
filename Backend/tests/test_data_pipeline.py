"""Testes do pipeline de importação."""

from datetime import date
from io import BytesIO

import pandas as pd
import pytest

from app.models.consumo import Consumo
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item
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


def test_ler_csv_virgula_utf8_multicoluna():
    # Layout do sistema de origem: vírgula + aspas + utf-8 (não deve colapsar
    # numa coluna só ao testar ';').
    conteudo = '"CD_MATERIAL","DT_MES","QT_CONSUMO"\n"MED001","2024-01","10"'.encode("utf-8")
    df = dp._ler_arquivo(conteudo, "consumo.csv")
    assert list(df.columns) == ["CD_MATERIAL", "DT_MES", "QT_CONSUMO"]
    assert df.iloc[0]["CD_MATERIAL"] == "MED001"


def test_normalizar_colunas_layout_origem():
    df = pd.DataFrame(columns=[
        "CD_MATERIAL", "DS_MATERIAL", "DT_MES",
        "QT_CONSUMO", "VL_CONSUMO", "DS_CENTRO_CUSTO",
    ])
    dp._normalizar_colunas(df)
    dp._validar_colunas(df)  # não deve levantar
    assert dp.COLUNAS_OBRIGATORIAS <= set(df.columns)


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
    assert "setor" in resultado.columns


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


@pytest.mark.parametrize("valor,esperado", [
    ("2024-01", date(2024, 1, 1)),
    ("01/2024", date(2024, 1, 1)),
    ("2024/01", date(2024, 1, 1)),
    ("202401", date(2024, 1, 1)),
])
def test_parsear_data_aceita_competencia_mensal(valor, esperado):
    assert dp._parsear_data(valor) == esperado


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
        "setor": "Central",
    }
    df = _df_base([linha, dict(linha)])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 1
    assert erros == []


def test_limpar_dados_rejeita_quantidade_negativa():
    df = _df_base([{
        "codigo_item": "MED001", "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "-3", "valor": "5", "setor": "Central",
    }])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 0
    assert any("quantidade" in e for e in erros)


def test_limpar_dados_rejeita_valor_zero():
    df = _df_base([{
        "codigo_item": "MED001", "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "10", "valor": "0", "setor": "Central",
    }])
    df_valido, erros = dp._limpar_dados(df)
    assert len(df_valido) == 0
    assert any("valor" in e for e in erros)


def test_limpar_dados_reporta_campo_nulo_com_numero_da_linha():
    df = _df_base([{
        "codigo_item": None, "descricao_item": "Dipirona", "data": "01/01/2024",
        "quantidade": "10", "valor": "5", "setor": "Central",
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


def _consumo(db, empresa, item, importacao, *, data_, quantidade, valor, setor="Central"):
    db.add(Consumo(
        empresa_id=empresa.id, importacao_id=importacao.id, item_id=item.id,
        data=data_, quantidade=quantidade, valor=valor, setor=setor,
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


def test_processar_arquivo_layout_origem_virgula_e_mes(db_session, empresa, usuario_admin):
    # CSV real: vírgula, aspas, cabeçalho CD_/DS_/QT_/VL_ e DT_MES mensal.
    conteudo = (
        '"CD_MATERIAL","DS_MATERIAL","DT_MES","QT_CONSUMO","VL_CONSUMO","DS_CENTRO_CUSTO"\n'
        '"MED001","Dipirona 500mg","2024-01","100","250.50","Farmacia"\n'
        '"MED001","Dipirona 500mg","2024-02","80","200.00","Farmacia"\n'
    ).encode("utf-8")
    importacao = dp.processar_arquivo(
        db_session, conteudo, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.status == "concluido"
    assert importacao.registros_validos == 2
    consumos = db_session.query(Consumo).filter(Consumo.empresa_id == empresa.id).all()
    assert {c.data for c in consumos} == {date(2024, 1, 1), date(2024, 2, 1)}


def test_processar_arquivo_em_lotes_grava_tudo_e_reusa_item(
    db_session, empresa, usuario_admin, monkeypatch
):
    # Força 3 lotes (5 linhas / lote de 2) para exercitar o streaming.
    monkeypatch.setattr(dp, "TAMANHO_LOTE", 2)
    linhas = ["codigo_item;descricao_item;data;quantidade;valor;setor"]
    for i in range(5):
        linhas.append(f"MED001;Dipirona;0{i + 1}/01/2024;{10 + i};{100 + i};Central")
    conteudo = "\n".join(linhas).encode("utf-8")

    importacao = dp.processar_arquivo(
        db_session, conteudo, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.status == "concluido"
    assert importacao.registros_validos == 5
    assert db_session.query(Consumo).filter(Consumo.empresa_id == empresa.id).count() == 5
    # Mesmo código em todos os lotes -> um único item (cache em memória).
    assert db_session.query(Item).filter(Item.empresa_id == empresa.id).count() == 1


def test_processar_arquivo_em_lotes_preserva_numero_de_linha_global(
    db_session, empresa, usuario_admin, monkeypatch
):
    monkeypatch.setattr(dp, "TAMANHO_LOTE", 2)
    linhas = [
        "codigo_item;descricao_item;data;quantidade;valor;setor",
        "MED001;A;01/01/2024;10;100;Central",   # linha 2 (válida)
        "MED002;B;02/01/2024;-5;100;Central",   # linha 3 (quantidade negativa)
        "MED003;C;03/01/2024;10;100;Central",   # linha 4 (válida)
        "MED004;D;data_ruim;10;100;Central",    # linha 5 (data inválida) - outro lote
    ]
    conteudo = "\n".join(linhas).encode("utf-8")

    importacao = dp.processar_arquivo(
        db_session, conteudo, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.registros_validos == 2
    assert importacao.registros_invalidos == 2
    assert any("linha 3" in e for e in importacao.erros)
    assert any("linha 5" in e for e in importacao.erros)


def test_processar_arquivo_com_erro_marca_status_erro(db_session, empresa, usuario_admin, csv_invalido):
    importacao = dp.processar_arquivo(
        db_session, csv_invalido, "consumo.csv", empresa.id, usuario_admin.id
    )
    assert importacao.status == "erro"
    assert importacao.erros


# --------------------------------------------------------------------------- #
# Setor e atributos complementares do material
# --------------------------------------------------------------------------- #
def _consumos_da_empresa(db, empresa):
    return db.query(Consumo).filter(Consumo.empresa_id == empresa.id).all()


def _item_por_codigo(db, empresa, codigo) -> Item:
    return db.query(Item).filter(Item.empresa_id == empresa.id, Item.codigo_item == codigo).one()


def test_importa_atributos_do_material_e_setor_do_layout_de_origem(db_session, empresa, usuario_admin):
    conteudo = (
        '"CD_MATERIAL","DS_MATERIAL","DS_GRUPO_MATERIAL","DS_SUBGRUPO_MATERIAL",'
        '"DS_CLASSE_MATERIAL","CD_UNID","DT_MES","QT_CONSUMO","VL_CONSUMO","DS_CENTRO_CUSTO"\n'
        '"MED001","Dipirona 500mg","Medicamentos","Analgésicos","Injetáveis","AMP",'
        '"2024-01","100","250.50","UTI Adulto"\n'
    ).encode("utf-8")
    importacao = dp.processar_arquivo(db_session, conteudo, "consumo.csv", empresa.id, usuario_admin.id)

    assert importacao.status == "concluido"
    assert importacao.registros_validos == 1
    item = _item_por_codigo(db_session, empresa, "MED001")
    assert (item.grupo_material, item.subgrupo_material, item.classe_material, item.unidade_medida) == (
        "Medicamentos", "Analgésicos", "Injetáveis", "AMP",
    )
    assert [c.setor for c in _consumos_da_empresa(db_session, empresa)] == ["UTI Adulto"]


def test_cabecalho_antigo_local_estoque_continua_aceito(db_session, empresa, usuario_admin):
    conteudo = (
        "codigo_item;descricao_item;data;quantidade;valor;local_estoque\n"
        "MED001;Dipirona;01/01/2024;10;20;Farmácia\n"
    ).encode("utf-8")
    importacao = dp.processar_arquivo(db_session, conteudo, "consumo.csv", empresa.id, usuario_admin.id)

    assert importacao.status == "concluido"
    assert [c.setor for c in _consumos_da_empresa(db_session, empresa)] == ["Farmácia"]


def test_reimportacao_atualiza_atributos_do_item_existente(db_session, empresa, usuario_admin):
    sem_grupo = (
        "codigo_item;descricao_item;data;quantidade;valor;setor\n"
        "MED001;Dipirona;01/01/2024;10;20;UTI\n"
    ).encode("utf-8")
    com_grupo = (
        "codigo_item;descricao_item;data;quantidade;valor;setor;grupo_material\n"
        "MED001;Dipirona;01/02/2024;10;20;UTI;Medicamentos\n"
    ).encode("utf-8")
    dp.processar_arquivo(db_session, sem_grupo, "a.csv", empresa.id, usuario_admin.id)
    assert _item_por_codigo(db_session, empresa, "MED001").grupo_material is None

    dp.processar_arquivo(db_session, com_grupo, "b.csv", empresa.id, usuario_admin.id)
    assert _item_por_codigo(db_session, empresa, "MED001").grupo_material == "Medicamentos"


def test_atributo_vazio_nao_apaga_o_valor_existente(db_session, empresa, usuario_admin):
    com_grupo = (
        "codigo_item;descricao_item;data;quantidade;valor;setor;grupo_material\n"
        "MED001;Dipirona;01/01/2024;10;20;UTI;Medicamentos\n"
    ).encode("utf-8")
    grupo_vazio = (
        "codigo_item;descricao_item;data;quantidade;valor;setor;grupo_material\n"
        "MED001;Dipirona;01/02/2024;10;20;UTI;\n"
    ).encode("utf-8")
    dp.processar_arquivo(db_session, com_grupo, "a.csv", empresa.id, usuario_admin.id)
    dp.processar_arquivo(db_session, grupo_vazio, "b.csv", empresa.id, usuario_admin.id)

    assert _item_por_codigo(db_session, empresa, "MED001").grupo_material == "Medicamentos"


# --------------------------------------------------------------------------- #
# Modos de importação: incremental x completa
# --------------------------------------------------------------------------- #
def _csv(*linhas: str) -> bytes:
    return "\n".join(["codigo_item;descricao_item;data;quantidade;valor;setor", *linhas]).encode()


def _total_consumos(db, empresa) -> int:
    return db.query(Consumo).filter(Consumo.empresa_id == empresa.id).count()


def test_importacao_incremental_acrescenta_sem_apagar(db_session, empresa, usuario_admin, csv_valido):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id)
    segunda = dp.processar_arquivo(db_session, csv_valido, "b.csv", empresa.id, usuario_admin.id)
    assert segunda.modo == "incremental"
    assert _total_consumos(db_session, empresa) == 6


def test_importacao_completa_substitui_a_base(db_session, empresa, usuario_admin, csv_valido):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id)
    nova = dp.processar_arquivo(
        db_session, _csv("MED009;Luva;05/03/2024;7;14.00;UTI"), "b.csv",
        empresa.id, usuario_admin.id, modo="completa",
    )
    assert nova.status == "concluido" and nova.modo == "completa"
    consumos = db_session.query(Consumo).filter(Consumo.empresa_id == empresa.id).all()
    assert [c.importacao_id for c in consumos] == [nova.id]
    tratados = db_session.query(ConsumoTratado).filter(ConsumoTratado.empresa_id == empresa.id).all()
    assert [(t.quantidade_total, t.setor) for t in tratados] == [(7.0, "UTI")]


def test_importacao_completa_nao_afeta_outras_empresas(
    db_session, empresa, empresa_secundaria, usuario_admin, csv_valido
):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa_secundaria.id, usuario_admin.id)
    dp.processar_arquivo(db_session, csv_valido, "b.csv", empresa.id, usuario_admin.id, modo="completa")
    assert _total_consumos(db_session, empresa_secundaria) == 3


def test_importacao_completa_com_erro_preserva_a_base(
    db_session, empresa, usuario_admin, csv_valido, csv_invalido
):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id)
    falha = dp.processar_arquivo(
        db_session, csv_invalido, "b.csv", empresa.id, usuario_admin.id, modo="completa"
    )
    assert falha.status == "erro"
    assert _total_consumos(db_session, empresa) == 3


def test_importacao_sem_linhas_validas_nao_apaga_a_base(db_session, empresa, usuario_admin, csv_valido):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id)
    vazia = dp.processar_arquivo(
        db_session, _csv("MED001;Dipirona;data-ruim;1;1.00;UTI"), "b.csv",
        empresa.id, usuario_admin.id, modo="completa",
    )
    assert vazia.status == "concluido" and vazia.registros_validos == 0
    assert _total_consumos(db_session, empresa) == 3


def test_erro_no_meio_remove_linhas_parciais_da_importacao(
    db_session, empresa, usuario_admin, csv_valido, monkeypatch
):
    dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id)

    def explode(*_args, **_kwargs):
        raise RuntimeError("falha simulada na agregação")

    monkeypatch.setattr(dp, "_agregar_consumos_tratados", explode)
    falha = dp.processar_arquivo(db_session, csv_valido, "b.csv", empresa.id, usuario_admin.id)
    assert falha.status == "erro"
    assert _total_consumos(db_session, empresa) == 3  # só a primeira importação


def test_modo_invalido_levanta_erro(db_session, empresa, usuario_admin, csv_valido):
    with pytest.raises(ValueError):
        dp.processar_arquivo(db_session, csv_valido, "a.csv", empresa.id, usuario_admin.id, modo="tudo")
