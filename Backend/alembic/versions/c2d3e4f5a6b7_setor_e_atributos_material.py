"""setor no lugar de local_estoque e atributos do material

- consumos.local_estoque          -> consumos.setor (renomeia, preserva os dados)
- consumos_tratados.local_estoque -> consumos_tratados.setor
- itens: grupo_material, subgrupo_material, classe_material

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_CONSUMO = ("consumos", "consumos_tratados")
ATRIBUTOS_MATERIAL = ("grupo_material", "subgrupo_material", "classe_material")


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(tabela)}


def upgrade() -> None:
    # Idempotente: a aplicação também roda Base.metadata.create_all no startup.
    for tabela in TABELAS_CONSUMO:
        colunas = _colunas(tabela)
        if "local_estoque" in colunas and "setor" not in colunas:
            op.alter_column(tabela, "local_estoque", new_column_name="setor")

    colunas_itens = _colunas("itens")
    for nome in ATRIBUTOS_MATERIAL:
        if nome not in colunas_itens:
            op.add_column("itens", sa.Column(nome, sa.String(length=255), nullable=True))


def downgrade() -> None:
    colunas_itens = _colunas("itens")
    for nome in ATRIBUTOS_MATERIAL:
        if nome in colunas_itens:
            op.drop_column("itens", nome)

    for tabela in TABELAS_CONSUMO:
        colunas = _colunas(tabela)
        if "setor" in colunas and "local_estoque" not in colunas:
            op.alter_column(tabela, "setor", new_column_name="local_estoque")
