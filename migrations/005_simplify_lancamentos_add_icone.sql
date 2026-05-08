-- Migration 005: Simplificar lançamentos + ícone em categorias
-- Apply in: Supabase → SQL Editor
-- Revises: e4f5g6h7i8j9 → f5g6h7i8j9k0
-- DEPENDE DA MIGRATION 004 já aplicada.

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 1 — Remover campos obsoletos de lancamentos
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE lancamentos
  DROP COLUMN IF EXISTS data_competencia,
  DROP COLUMN IF EXISTS data_pagamento,
  DROP COLUMN IF EXISTS forma_pagamento;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 2 — Adicionar campo data unificado e status explícito
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE lancamentos
  ADD COLUMN IF NOT EXISTS data DATE,
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'a pagar';

-- Para dados existentes: data = hoje (fallback seguro para migração)
-- Ajuste manualmente se necessário após a migração.
UPDATE lancamentos SET data = CURRENT_DATE WHERE data IS NULL;

-- Definir como NOT NULL após o preenchimento
ALTER TABLE lancamentos ALTER COLUMN data SET NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 3 — Remover enum de forma_pagamento (se existir)
-- ─────────────────────────────────────────────────────────────────────────────

DROP TYPE IF EXISTS formapagamento;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 4 — Adicionar ícone às categorias
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE categorias ADD COLUMN IF NOT EXISTS icone VARCHAR(50);

-- ─────────────────────────────────────────────────────────────────────────────
-- VERIFICAÇÃO (opcional)
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name IN ('lancamentos', 'categorias')
-- ORDER BY table_name, ordinal_position;
