-- Migration 002: Add conta_id to lancamentos
-- Apply in: Supabase → SQL Editor
-- Revises: c1f2a3b4c5d6 → c2f3a4b5c6d7
-- DEPENDE DA 001 já aplicada.

-- Verifica se já existe uma conta antes de prosseguir:
-- SELECT id, nome FROM contas LIMIT 5;
-- Se não houver conta com id=1, ajuste o UPDATE abaixo para o id correto.

ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS conta_id INTEGER;

ALTER TABLE lancamentos
  ADD CONSTRAINT fk_lancamento_conta_id
  FOREIGN KEY (conta_id) REFERENCES contas(id);

-- Atribui a primeira conta disponível a lançamentos sem conta
UPDATE lancamentos
SET conta_id = (SELECT id FROM contas ORDER BY id LIMIT 1)
WHERE conta_id IS NULL;

ALTER TABLE lancamentos ALTER COLUMN conta_id SET NOT NULL;
