"""adiciona tabela previsoes_diarias

Revision ID: b1c2d3e4f5a6
Revises: 8215c192798c
Create Date: 2026-09-27 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "8215c192798c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = "previsoes_diarias"
INDICE = "ix_prev_diaria_empresa_item_data"


def upgrade() -> None:
    # Idempotente: a aplicação também roda Base.metadata.create_all no startup,
    # então a tabela pode já existir. Só cria se ainda não houver.
    inspetor = inspect(op.get_bind())
    if TABELA in inspetor.get_table_names():
        return
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("quantidade_prevista", sa.Float(), nullable=False),
        sa.Column("metodo", sa.String(length=30), nullable=False),
        sa.Column(
            "gerado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["itens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(INDICE, TABELA, ["empresa_id", "item_id", "data"])


def downgrade() -> None:
    inspetor = inspect(op.get_bind())
    if TABELA not in inspetor.get_table_names():
        return
    op.drop_index(INDICE, table_name=TABELA)
    op.drop_table(TABELA)
