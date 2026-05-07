"""Add recurrence fields to Lancamento.

Revision ID: c1f2a3b4c5d6
Revises: b3d53bcd6236
Create Date: 2024-05-06 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1f2a3b4c5d6'
down_revision = 'b3d53bcd6236'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar coluna tipo_recorrencia
    op.add_column('lancamentos', sa.Column('tipo_recorrencia', sa.Enum('unico', 'fixo', 'parcelado', name='tiporecorrencia'), nullable=True))
    op.execute("UPDATE lancamentos SET tipo_recorrencia = 'unico' WHERE tipo_recorrencia IS NULL")
    op.alter_column('lancamentos', 'tipo_recorrencia', nullable=False)
    
    # Adicionar coluna frequencia_recorrencia
    op.add_column('lancamentos', sa.Column('frequencia_recorrencia', sa.Enum('diario', 'semanal', 'quinzenal', 'mensal', name='frequenciarecorrencia'), nullable=True))
    
    # Adicionar coluna quantidade_parcelas
    op.add_column('lancamentos', sa.Column('quantidade_parcelas', sa.Integer(), nullable=True))
    
    # Adicionar coluna numero_parcela
    op.add_column('lancamentos', sa.Column('numero_parcela', sa.Integer(), nullable=True))
    
    # Adicionar coluna lancamento_pai_id
    op.add_column('lancamentos', sa.Column('lancamento_pai_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_lancamento_pai_id', 'lancamentos', 'lancamentos', ['lancamento_pai_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_lancamento_pai_id', 'lancamentos', type_='foreignkey')
    op.drop_column('lancamentos', 'lancamento_pai_id')
    op.drop_column('lancamentos', 'numero_parcela')
    op.drop_column('lancamentos', 'quantidade_parcelas')
    op.drop_column('lancamentos', 'frequencia_recorrencia')
    op.drop_column('lancamentos', 'tipo_recorrencia')
