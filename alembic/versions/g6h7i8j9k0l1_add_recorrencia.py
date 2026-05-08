"""Add recurrence fields to lancamentos (tipo_recorrencia, frequencia, parcelas, pai_id).

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'g6h7i8j9k0l1'
down_revision = 'f5g6h7i8j9k0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo_recorrencia', sa.String(20), nullable=False, server_default='unico'))
        batch_op.add_column(sa.Column('frequencia_recorrencia', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('total_parcelas', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('numero_parcela', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('lancamento_pai_id', sa.Integer(), sa.ForeignKey('lancamentos.id'), nullable=True))

    op.create_index('ix_lancamentos_pai_id', 'lancamentos', ['lancamento_pai_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_lancamentos_pai_id', table_name='lancamentos')

    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.drop_column('lancamento_pai_id')
        batch_op.drop_column('numero_parcela')
        batch_op.drop_column('total_parcelas')
        batch_op.drop_column('frequencia_recorrencia')
        batch_op.drop_column('tipo_recorrencia')
