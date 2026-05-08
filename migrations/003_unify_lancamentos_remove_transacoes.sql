-- Migration 003: Unificar lançamentos — remover transações, OFX e recorrência
-- Apply in: Supabase → SQL Editor
-- Revises: c2f3a4b5c6d7 → d3e4f5g6h7i8
-- DEPENDE DAS MIGRATIONS 001 e 002 já aplicadas.

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 1 — Remover tabelas dependentes (ordem importa por FK)
-- ─────────────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS lancamento_transacao;
DROP TABLE IF EXISTS transacoes;
DROP TABLE IF EXISTS ofx_imports;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 2 — Remover colunas de recorrência de lancamentos
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE lancamentos
  DROP COLUMN IF EXISTS tipo_recorrencia,
  DROP COLUMN IF EXISTS frequencia_recorrencia,
  DROP COLUMN IF EXISTS quantidade_parcelas,
  DROP COLUMN IF EXISTS numero_parcela,
  DROP COLUMN IF EXISTS lancamento_pai_id;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 3 — Adicionar campos de realização em lancamentos
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE lancamentos
  ADD COLUMN IF NOT EXISTS data_pagamento DATE,
  ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(20);

-- forma_pagamento aceita: pix, boleto, ted, doc, debito, credito, dinheiro, outro

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 4 — Remover tipos ENUM obsoletos (PostgreSQL)
-- ─────────────────────────────────────────────────────────────────────────────

DROP TYPE IF EXISTS tiporecorrencia;
DROP TYPE IF EXISTS frequenciarecorrencia;
DROP TYPE IF EXISTS statusconciliacao;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 5 — Remover colunas não usadas de usuarios e contas (relações extintas)
-- ─────────────────────────────────────────────────────────────────────────────
-- Nota: as FKs de transacoes e ofx_imports em usuarios e contas são removidas
-- automaticamente junto com o DROP TABLE acima.

-- ─────────────────────────────────────────────────────────────────────────────
-- VERIFICAÇÃO (opcional — rode para confirmar o estado final)
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'lancamentos'
-- ORDER BY ordinal_position;
