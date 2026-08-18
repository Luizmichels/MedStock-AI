from sqlalchemy import inspect, text

from app.models import __all__ as nomes_modelos
from app.database import Base


def test_conexao_com_banco(engine):
    with engine.connect() as conn:
        resultado = conn.execute(text("SELECT 1")).scalar()
    assert resultado == 1


def test_todas_as_tabelas_sao_criadas(engine):
    inspetor = inspect(engine)
    tabelas_existentes = set(inspetor.get_table_names())
    tabelas_esperadas = set(Base.metadata.tables.keys())

    assert tabelas_esperadas.issubset(tabelas_existentes)
    assert len(tabelas_esperadas) == len(nomes_modelos)


def test_coluna_endereco_de_empresa_existe_e_e_obrigatoria(engine):
    inspetor = inspect(engine)
    colunas = {c["name"]: c for c in inspetor.get_columns("empresas")}
    assert "endereco" in colunas
    assert colunas["endereco"]["nullable"] is False


def test_coluna_endereco_de_solicitacao_existe_e_e_obrigatoria(engine):
    inspetor = inspect(engine)
    colunas = {c["name"]: c for c in inspetor.get_columns("solicitacoes_acesso")}
    assert "endereco" in colunas
    assert colunas["endereco"]["nullable"] is False


def test_email_de_usuario_e_unico(engine):
    inspetor = inspect(engine)
    constraints = inspetor.get_unique_constraints("usuarios")
    colunas_unicas = {coluna for c in constraints for coluna in c["column_names"]}
    indices_unicos = {
        coluna
        for idx in inspetor.get_indexes("usuarios")
        if idx["unique"]
        for coluna in idx["column_names"]
    }
    assert "email" in colunas_unicas or "email" in indices_unicos
