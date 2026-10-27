"""modo da importação (incremental | completa)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(tabela)}


def upgrade() -> None:
    # Idempotente: a aplicação também roda Base.metadata.create_all no startup.
    if "modo" not in _colunas("importacoes"):
        op.add_column(
            "importacoes",
            sa.Column("modo", sa.String(length=20), nullable=False, server_default="incremental"),
        )


def downgrade() -> None:
    if "modo" in _colunas("importacoes"):
        op.drop_column("importacoes", "modo")
