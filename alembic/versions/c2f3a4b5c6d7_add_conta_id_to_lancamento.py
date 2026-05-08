"""Add conta_id to Lancamento (required for account tracking).

Revision ID: c2f3a4b5c6d7
Revises: c1f2a3b4c5d6
Create Date: 2024-05-06 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c2f3a4b5c6d7'
down_revision = 'c1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar coluna conta_id
    op.add_column('lancamentos', sa.Column('conta_id', sa.Integer(), nullable=True))
    
    # Criar FK (temporariamente nullable para dados existentes)
    op.create_foreign_key('fk_lancamento_conta_id', 'lancamentos', 'contas', ['conta_id'], ['id'])
    
    # Se houver registros existentes, atribuir a primeira conta
    op.execute("UPDATE lancamentos SET conta_id = 1 WHERE conta_id IS NULL")
    
    # Agora fazer NOT NULL
    op.alter_column('lancamentos', 'conta_id', nullable=False)


def downgrade() -> None:
    op.drop_constraint('fk_lancamento_conta_id', 'lancamentos', type_='foreignkey')
    op.drop_column('lancamentos', 'conta_id')
