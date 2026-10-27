"""chaves de integração (importação de consumo via API)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existe(tabela: str) -> bool:
    return tabela in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    # Idempotente: a aplicação também roda Base.metadata.create_all no startup.
    if _existe("chaves_integracao"):
        return
    op.create_table(
        "chaves_integracao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("criado_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("prefixo", sa.String(length=16), nullable=False),
        sa.Column("hash_chave", sa.String(length=64), nullable=False, unique=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ultimo_uso_em", sa.DateTime(), nullable=True),
        sa.Column("revogada_em", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chaves_integracao_empresa_id", "chaves_integracao", ["empresa_id"])


def downgrade() -> None:
    if _existe("chaves_integracao"):
        op.drop_index("ix_chaves_integracao_empresa_id", table_name="chaves_integracao")
        op.drop_table("chaves_integracao")
