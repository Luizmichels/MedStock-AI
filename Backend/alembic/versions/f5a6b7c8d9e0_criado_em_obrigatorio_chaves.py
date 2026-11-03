"""criado_em obrigatório em chaves_integracao

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-11-02 10:00:00.000000

A migração e4f5a6b7c8d9 criou a coluna como anulável, mas o modelo a declara
obrigatória (como o criado_em das demais tabelas). Detectado pelo `alembic
check` do CI.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE chaves_integracao SET criado_em = CURRENT_TIMESTAMP WHERE criado_em IS NULL"
    )
    with op.batch_alter_table("chaves_integracao") as batch:
        batch.alter_column("criado_em", existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("chaves_integracao") as batch:
        batch.alter_column("criado_em", existing_type=sa.DateTime(), nullable=True)
