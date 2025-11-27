-- ============================================================================
-- Migration: Adicionar campos campaign_type, tone, briefing à tabela campaigns
-- ============================================================================
-- Data: 2025-11-26
-- Autor: Isaac (via Claude Code)
-- Descrição: Permite criar campanhas flexíveis de diferentes tipos
--            (promocional, reengajamento, evento, pesquisa, informativo, custom)
--            com tom de mensagem configurável e briefing livre.
-- ============================================================================

-- Verificar conexão
SELECT current_database(), current_user, now() as execution_time;

-- ============================================================================
-- 1. ADICIONAR COLUNA campaign_type
-- ============================================================================
-- Tipos: promotional, reengagement, event, survey, informative, custom

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'campaigns' AND column_name = 'campaign_type'
    ) THEN
        ALTER TABLE campaigns
        ADD COLUMN campaign_type VARCHAR(30) DEFAULT 'promotional';

        COMMENT ON COLUMN campaigns.campaign_type IS
            'Tipo da campanha: promotional, reengagement, event, survey, informative, custom';

        RAISE NOTICE 'Coluna campaign_type adicionada';
    ELSE
        RAISE NOTICE 'Coluna campaign_type já existe';
    END IF;
END $$;

-- ============================================================================
-- 2. ADICIONAR COLUNA tone
-- ============================================================================
-- Tons: urgente, amigavel, profissional, empatico, animado, agradecido, curioso, exclusivo, direto

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'campaigns' AND column_name = 'tone'
    ) THEN
        ALTER TABLE campaigns
        ADD COLUMN tone VARCHAR(30) DEFAULT 'profissional';

        COMMENT ON COLUMN campaigns.tone IS
            'Tom da mensagem: urgente, amigavel, profissional, empatico, animado, agradecido, curioso, exclusivo, direto';

        RAISE NOTICE 'Coluna tone adicionada';
    ELSE
        RAISE NOTICE 'Coluna tone já existe';
    END IF;
END $$;

-- ============================================================================
-- 3. ADICIONAR COLUNA briefing
-- ============================================================================
-- Texto livre descrevendo o objetivo e contexto da campanha

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'campaigns' AND column_name = 'briefing'
    ) THEN
        ALTER TABLE campaigns
        ADD COLUMN briefing TEXT;

        COMMENT ON COLUMN campaigns.briefing IS
            'Texto livre descrevendo o objetivo, contexto e instruções especiais da campanha para a IA';

        RAISE NOTICE 'Coluna briefing adicionada';
    ELSE
        RAISE NOTICE 'Coluna briefing já existe';
    END IF;
END $$;

-- ============================================================================
-- 4. CRIAR ÍNDICE PARA campaign_type (otimização de queries)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_campaigns_type
ON campaigns(campaign_type);

CREATE INDEX IF NOT EXISTS idx_campaigns_tenant_type
ON campaigns(tenant_id, campaign_type);

-- ============================================================================
-- 5. VERIFICAÇÃO FINAL
-- ============================================================================

-- Verificar estrutura atualizada
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'campaigns'
AND column_name IN ('campaign_type', 'tone', 'briefing')
ORDER BY ordinal_position;

-- Verificar índices
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'campaigns'
AND indexname LIKE '%type%'
ORDER BY indexname;

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================
-- Para executar:
-- PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -d geniai_analytics \
--     -f sql/migrations/20251126_add_campaign_type_tone_briefing.sql
-- ============================================================================