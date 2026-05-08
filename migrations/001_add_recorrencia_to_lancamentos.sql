-- Migration 001: Add recurrence fields to lancamentos
-- Apply in: Supabase → SQL Editor
-- Revises: b3d53bcd6236 → c1f2a3b4c5d6

-- Enums (cria apenas se não existir)
DO $$ BEGIN
  CREATE TYPE tiporecorrencia AS ENUM ('unico', 'fixo', 'parcelado');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE frequenciarecorrencia AS ENUM ('diario', 'semanal', 'quinzenal', 'mensal');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Colunas
ALTER TABLE lancamentos
  ADD COLUMN IF NOT EXISTS tipo_recorrencia tiporecorrencia,
  ADD COLUMN IF NOT EXISTS frequencia_recorrencia frequenciarecorrencia,
  ADD COLUMN IF NOT EXISTS quantidade_parcelas INTEGER,
  ADD COLUMN IF NOT EXISTS numero_parcela INTEGER,
  ADD COLUMN IF NOT EXISTS lancamento_pai_id INTEGER;

-- Preenche valor padrão nos existentes
UPDATE lancamentos SET tipo_recorrencia = 'unico' WHERE tipo_recorrencia IS NULL;

-- NOT NULL após o UPDATE
ALTER TABLE lancamentos ALTER COLUMN tipo_recorrencia SET NOT NULL;

-- FK para recorrência pai
ALTER TABLE lancamentos
  ADD CONSTRAINT fk_lancamento_pai_id
  FOREIGN KEY (lancamento_pai_id) REFERENCES lancamentos(id);
