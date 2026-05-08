"""Simplify lancamentos: single data field, explicit status; add icone to categorias.

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f5g6h7i8j9k0'
down_revision = 'e4f5g6h7i8j9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Adicionar icone a categorias
    with op.batch_alter_table('categorias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icone', sa.String(50), nullable=True))

    # 2. Reestruturar lancamentos (batch para SQLite)
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        # Adicionar novos campos
        batch_op.add_column(sa.Column('data', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(20), nullable=False, server_default='a pagar'))
        # Remover campos obsoletos
        batch_op.drop_column('data_competencia')
        batch_op.drop_column('data_pagamento')
        batch_op.drop_column('forma_pagamento')

    # Preencher data a partir dos registros existentes (fallback: data atual)
    op.execute("UPDATE lancamentos SET data = DATE('now') WHERE data IS NULL")


def downgrade() -> None:
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forma_pagamento', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('data_pagamento', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('data_competencia', sa.Date(), nullable=True))
        batch_op.drop_column('status')
        batch_op.drop_column('data')

    with op.batch_alter_table('categorias', schema=None) as batch_op:
        batch_op.drop_column('icone')
