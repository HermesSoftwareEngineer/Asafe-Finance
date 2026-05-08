-- Migration 004: Conciliação OFX — adicionar tabelas e campos de conciliação
-- Apply in: Supabase → SQL Editor
-- Revises: d3e4f5g6h7i8 → e4f5g6h7i8j9
-- DEPENDE DA MIGRATION 003 já aplicada.

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 1 — Adicionar campos de conciliação em lancamentos
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE statusconciliacao AS ENUM ('pendente', 'conciliado', 'ignorado');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE lancamentos
  ADD COLUMN IF NOT EXISTS status_conciliacao statusconciliacao,
  ADD COLUMN IF NOT EXISTS ofx_transaction_id VARCHAR(100);

-- Lançamentos já realizados (data_pagamento preenchida) ficam como "pendente"
UPDATE lancamentos
SET status_conciliacao = 'pendente'
WHERE data_pagamento IS NOT NULL
  AND status_conciliacao IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 2 — Criar tabela ofx_imports
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ofx_imports (
  id               SERIAL PRIMARY KEY,
  conta_id         INTEGER NOT NULL REFERENCES contas(id),
  arquivo_nome     VARCHAR(200) NOT NULL,
  data_inicio      DATE,
  data_fim         DATE,
  total_registros  INTEGER DEFAULT 0,
  novos_registros  INTEGER DEFAULT 0,
  importado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  usuario_id       INTEGER NOT NULL REFERENCES usuarios(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- PASSO 3 — Criar tabela ofx_transactions
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE statusofxtransaction AS ENUM ('pendente', 'conciliado', 'ignorado');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE tipolancamento AS ENUM ('entrada', 'saida');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS ofx_transactions (
  id                    SERIAL PRIMARY KEY,
  ofx_import_id         INTEGER NOT NULL REFERENCES ofx_imports(id),
  conta_id              INTEGER NOT NULL REFERENCES contas(id),
  data                  DATE NOT NULL,
  valor                 NUMERIC(10,2) NOT NULL,
  tipo                  tipolancamento NOT NULL,
  descricao             VARCHAR(500) NOT NULL,
  ofx_transaction_id    VARCHAR(100) NOT NULL,
  status                statusofxtransaction NOT NULL DEFAULT 'pendente',
  lancamento_id         INTEGER REFERENCES lancamentos(id),
  created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_ofx_tx_conta UNIQUE (conta_id, ofx_transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_ofx_tx_status    ON ofx_transactions(status);
CREATE INDEX IF NOT EXISTS idx_ofx_tx_conta     ON ofx_transactions(conta_id);
CREATE INDEX IF NOT EXISTS idx_ofx_tx_data      ON ofx_transactions(data);

-- ─────────────────────────────────────────────────────────────────────────────
-- VERIFICAÇÃO (opcional)
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
