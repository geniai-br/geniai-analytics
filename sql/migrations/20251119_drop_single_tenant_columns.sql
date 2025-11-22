-- Migration: Drop Single-Tenant Specific Columns (AllpFit)
-- Data: 2025-11-19
-- Descrição: Remove colunas específicas do contexto single-tenant AllpFit
--            que não são mais usadas no sistema multi-tenant genérico
--
-- Colunas removidas:
--   - condicao_fisica: Específica para academias (Sedentário, Iniciante, etc)
--   - objetivo: Específica para fitness (Perda de peso, Ganho de massa, etc)
--   - probabilidade_conversao: Score antigo 0-5 (substituído por score_prioridade no remarketing)
--
-- Índices removidos:
--   - idx_conv_analytics_condicao_fisica
--   - idx_conv_analytics_objetivo
--   - idx_conv_analytics_prob_conversao

BEGIN;

-- 1. Dropar índices primeiro (referências às colunas)
DROP INDEX IF EXISTS idx_conv_analytics_condicao_fisica;
DROP INDEX IF EXISTS idx_conv_analytics_objetivo;
DROP INDEX IF EXISTS idx_conv_analytics_prob_conversao;

-- 2. Dropar colunas obsoletas
ALTER TABLE conversations_analytics
  DROP COLUMN IF EXISTS condicao_fisica,
  DROP COLUMN IF EXISTS objetivo,
  DROP COLUMN IF EXISTS probabilidade_conversao;

-- 3. Verificar que as colunas foram removidas
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'conversations_analytics'
      AND column_name IN ('condicao_fisica', 'objetivo', 'probabilidade_conversao');

    IF col_count > 0 THEN
        RAISE EXCEPTION 'Falha ao remover colunas obsoletas. % colunas ainda existem', col_count;
    END IF;

    RAISE NOTICE 'Migração concluída com sucesso! Colunas single-tenant removidas.';
END $$;

COMMIT;

-- Rollback (se necessário):
--
-- BEGIN;
--
-- ALTER TABLE conversations_analytics
--   ADD COLUMN condicao_fisica TEXT DEFAULT 'Não mencionado',
--   ADD COLUMN objetivo TEXT DEFAULT 'Não mencionado',
--   ADD COLUMN probabilidade_conversao INTEGER DEFAULT 0;
--
-- CREATE INDEX idx_conv_analytics_condicao_fisica
--   ON conversations_analytics(condicao_fisica)
--   WHERE condicao_fisica <> 'Não mencionado';
--
-- CREATE INDEX idx_conv_analytics_objetivo
--   ON conversations_analytics(objetivo)
--   WHERE objetivo <> 'Não mencionado';
--
-- CREATE INDEX idx_conv_analytics_prob_conversao
--   ON conversations_analytics(probabilidade_conversao)
--   WHERE probabilidade_conversao > 0;
--
-- COMMIT;