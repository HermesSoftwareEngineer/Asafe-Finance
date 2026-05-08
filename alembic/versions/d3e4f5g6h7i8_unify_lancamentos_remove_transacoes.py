"""Unify: add realization fields to lancamentos, drop transacoes/vinculos/ofx tables.

Revision ID: d3e4f5g6h7i8
Revises: c2f3a4b5c6d7
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd3e4f5g6h7i8'
down_revision = 'c2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop dependent tables first (ordem importa por FK)
    op.drop_table('lancamento_transacao')
    op.drop_table('transacoes')
    op.drop_table('ofx_imports')

    # 2. Adicionar campos de realização em lancamentos (batch para compat. SQLite)
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_pagamento', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('forma_pagamento', sa.String(50), nullable=True))

    # 3. Remover colunas de recorrência (batch para compat. SQLite)
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.drop_column('tipo_recorrencia')
        batch_op.drop_column('frequencia_recorrencia')
        batch_op.drop_column('quantidade_parcelas')
        batch_op.drop_column('numero_parcela')
        batch_op.drop_column('lancamento_pai_id')


def downgrade() -> None:
    # Restaurar colunas de recorrência
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lancamento_pai_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('numero_parcela', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('quantidade_parcelas', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('frequencia_recorrencia', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('tipo_recorrencia', sa.String(20), nullable=False, server_default='unico'))

    # Remover campos de realização
    with op.batch_alter_table('lancamentos', schema=None) as batch_op:
        batch_op.drop_column('forma_pagamento')
        batch_op.drop_column('data_pagamento')

    # Recriar tabelas (estrutura simplificada para downgrade)
    op.create_table(
        'transacoes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('descricao', sa.String(200), nullable=False),
        sa.Column('tipo', sa.String(10), nullable=False),
        sa.Column('valor', sa.Numeric(10, 2), nullable=False),
        sa.Column('data_pagamento', sa.Date(), nullable=False),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('contas.id'), nullable=False),
        sa.Column('forma_pagamento', sa.String(50), nullable=False),
        sa.Column('status_conciliacao', sa.String(20), nullable=False, server_default='pendente'),
        sa.Column('ofx_transaction_id', sa.String(100), nullable=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'lancamento_transacao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lancamento_id', sa.Integer(), sa.ForeignKey('lancamentos.id'), nullable=False),
        sa.Column('transacao_id', sa.Integer(), sa.ForeignKey('transacoes.id'), nullable=False),
        sa.Column('valor_vinculado', sa.Numeric(10, 2), nullable=False),
    )
    op.create_table(
        'ofx_imports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('conta_id', sa.Integer(), sa.ForeignKey('contas.id'), nullable=False),
        sa.Column('arquivo_nome', sa.String(200), nullable=False),
        sa.Column('data_inicio', sa.Date(), nullable=True),
        sa.Column('data_fim', sa.Date(), nullable=True),
        sa.Column('total_registros', sa.Integer(), server_default='0'),
        sa.Column('importado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
    )
