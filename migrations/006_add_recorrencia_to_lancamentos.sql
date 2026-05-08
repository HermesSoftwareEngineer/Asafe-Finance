  -- Migration 006: Adicionar campos de recorrência a lançamentos
  -- Apply in: Supabase → SQL Editor
  -- Revises: f5g6h7i8j9k0 → g6h7i8j9k0l1
  -- DEPENDE DA MIGRATION 005 já aplicada.

  -- ─────────────────────────────────────────────────────────────────────────────
  -- PASSO 1 — Adicionar campos de recorrência
  -- ─────────────────────────────────────────────────────────────────────────────

  ALTER TABLE lancamentos
    ADD COLUMN IF NOT EXISTS tipo_recorrencia   VARCHAR(20) NOT NULL DEFAULT 'unico',
    ADD COLUMN IF NOT EXISTS frequencia_recorrencia VARCHAR(20),
    ADD COLUMN IF NOT EXISTS total_parcelas     INTEGER,
    ADD COLUMN IF NOT EXISTS numero_parcela     INTEGER,
    ADD COLUMN IF NOT EXISTS lancamento_pai_id  INTEGER REFERENCES lancamentos(id) ON DELETE SET NULL;

  -- ─────────────────────────────────────────────────────────────────────────────
  -- PASSO 2 — Índice para consulta de série (pai → filhos)
  -- ─────────────────────────────────────────────────────────────────────────────

  CREATE INDEX IF NOT EXISTS ix_lancamentos_pai_id ON lancamentos(lancamento_pai_id);

  -- ─────────────────────────────────────────────────────────────────────────────
  -- VERIFICAÇÃO (opcional)
  -- ─────────────────────────────────────────────────────────────────────────────
  -- SELECT column_name, data_type, is_nullable, column_default
  -- FROM information_schema.columns
  -- WHERE table_name = 'lancamentos'
  --   AND column_name IN ('tipo_recorrencia','frequencia_recorrencia','total_parcelas','numero_parcela','lancamento_pai_id')
  -- ORDER BY ordinal_position;
