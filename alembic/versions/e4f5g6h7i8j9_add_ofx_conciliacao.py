"""Add OFX reconciliation: status_conciliacao in lancamentos, ofx_imports, ofx_transactions.

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5g6h7i8j9'
down_revision = 'd3e4f5g6h7i8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Campos em lancamentos
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status_conciliacao', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('ofx_transaction_id', sa.String(100), nullable=True))

    # Preenche lançamentos já realizados como "pendente"
    op.execute(
        "UPDATE lancamentos SET status_conciliacao = 'pendente' "
        "WHERE data_pagamento IS NOT NULL AND status_conciliacao IS NULL"
    )

    # 2. Tabela ofx_imports
    op.create_table(
        'ofx_imports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('contas.id'), nullable=False),
        sa.Column('arquivo_nome', sa.String(200), nullable=False),
        sa.Column('data_inicio', sa.Date(), nullable=True),
        sa.Column('data_fim', sa.Date(), nullable=True),
        sa.Column('total_registros', sa.Integer(), server_default='0'),
        sa.Column('novos_registros', sa.Integer(), server_default='0'),
        sa.Column('importado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
    )

    # 3. Tabela ofx_transactions
    op.create_table(
        'ofx_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ofx_import_id', sa.Integer(), sa.ForeignKey('ofx_imports.id'), nullable=False),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('contas.id'), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('valor', sa.Numeric(10, 2), nullable=False),
        sa.Column('tipo', sa.String(10), nullable=False),
        sa.Column('descricao', sa.String(500), nullable=False),
        sa.Column('ofx_transaction_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pendente'),
        sa.Column('lancamento_id', sa.Integer(), sa.ForeignKey('lancamentos.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('conta_id', 'ofx_transaction_id', name='uq_ofx_tx_conta'),
    )


def downgrade() -> None:
    op.drop_table('ofx_transactions')
    op.drop_table('ofx_imports')
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.drop_column('ofx_transaction_id')
        batch_op.drop_column('status_conciliacao')
