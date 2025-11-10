-- Migration: Add OpenAI Support to Multi-Tenant
-- Date: 2025-11-09
-- Fase: 5.6 - OpenAI Integration
-- Descrição: Adiciona configuração use_openai e rastreamento de custos

-- ============================================================================
-- 1. ADICIONAR CAMPO use_openai EM tenant_configs.features
-- ============================================================================

-- Adicionar use_openai: false (default) para todos os tenants existentes
UPDATE tenant_configs
SET features = features || '{"use_openai": false}'::jsonb
WHERE features->>'use_openai' IS NULL;

-- Verificação
-- SELECT tenant_id, features->>'use_openai' as use_openai FROM tenant_configs;

-- ============================================================================
-- 2. ADICIONAR CAMPOS DE RASTREAMENTO DE CUSTOS EM etl_control
-- ============================================================================

-- Adicionar colunas para rastrear uso da API OpenAI
ALTER TABLE etl_control
ADD COLUMN IF NOT EXISTS openai_api_calls INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS openai_total_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS openai_cost_brl NUMERIC(10,4) DEFAULT 0.0000;

-- Comentários
COMMENT ON COLUMN etl_control.openai_api_calls IS 'Total de chamadas à API OpenAI nesta execução ETL';
COMMENT ON COLUMN etl_control.openai_total_tokens IS 'Total de tokens consumidos (input + output)';
COMMENT ON COLUMN etl_control.openai_cost_brl IS 'Custo estimado em R$ (baseado em pricing da OpenAI)';

-- ============================================================================
-- 3. CRIAR VIEW PARA MONITORAMENTO DE CUSTOS OPENAI
-- ============================================================================

CREATE OR REPLACE VIEW v_openai_usage_by_tenant AS
SELECT
    tc.tenant_id,
    tc.tenant_name,
    tc.features->>'use_openai' as openai_enabled,
    COUNT(*) FILTER (WHERE ec.openai_api_calls > 0) as etl_runs_with_openai,
    COALESCE(SUM(ec.openai_api_calls), 0) as total_api_calls,
    COALESCE(SUM(ec.openai_total_tokens), 0) as total_tokens,
    COALESCE(SUM(ec.openai_cost_brl), 0.0) as total_cost_brl,
    COALESCE(AVG(ec.openai_cost_brl) FILTER (WHERE ec.openai_api_calls > 0), 0.0) as avg_cost_per_run,
    MAX(ec.started_at) FILTER (WHERE ec.openai_api_calls > 0) as last_openai_run
FROM tenant_configs tc
LEFT JOIN etl_control ec ON tc.tenant_id = ec.tenant_id
WHERE ec.started_at >= DATE_TRUNC('month', CURRENT_DATE)  -- Apenas mês atual
GROUP BY tc.tenant_id, tc.tenant_name, tc.features->>'use_openai'
ORDER BY total_cost_brl DESC;

COMMENT ON VIEW v_openai_usage_by_tenant IS 'Monitoramento de uso e custos OpenAI por tenant (mês atual)';

-- ============================================================================
-- 4. CRIAR VIEW PARA HISTÓRICO MENSAL DE CUSTOS
-- ============================================================================

CREATE OR REPLACE VIEW v_openai_monthly_costs AS
SELECT
    tc.tenant_id,
    tc.tenant_name,
    DATE_TRUNC('month', ec.started_at)::date as mes,
    COUNT(*) FILTER (WHERE ec.openai_api_calls > 0) as etl_runs,
    COALESCE(SUM(ec.openai_api_calls), 0) as total_calls,
    COALESCE(SUM(ec.openai_total_tokens), 0) as total_tokens,
    COALESCE(SUM(ec.openai_cost_brl), 0.0) as total_cost_brl,
    COALESCE(MAX(ec.conversations_processed), 0) as conversations_processed
FROM tenant_configs tc
LEFT JOIN etl_control ec ON tc.tenant_id = ec.tenant_id
WHERE ec.started_at IS NOT NULL
GROUP BY tc.tenant_id, tc.tenant_name, DATE_TRUNC('month', ec.started_at)
ORDER BY mes DESC, total_cost_brl DESC;

COMMENT ON VIEW v_openai_monthly_costs IS 'Histórico mensal de custos OpenAI por tenant';

-- ============================================================================
-- 5. FUNÇÃO HELPER PARA CALCULAR CUSTO ESTIMADO
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_openai_cost_brl(
    total_tokens INTEGER,
    model_name TEXT DEFAULT 'gpt-4o-mini'
)
RETURNS NUMERIC(10,4) AS $$
DECLARE
    cost_per_1k_tokens NUMERIC(10,6);
    cost_usd NUMERIC(10,4);
    cost_brl NUMERIC(10,4);
    usd_to_brl NUMERIC(6,4) := 5.50;  -- Taxa de câmbio aproximada
BEGIN
    -- Pricing OpenAI (2025-01)
    -- gpt-4o-mini: $0.00015 per 1K input tokens, $0.0006 per 1K output tokens
    -- Simplificação: usar média de $0.0004 per 1K tokens
    IF model_name = 'gpt-4o-mini' THEN
        cost_per_1k_tokens := 0.0004;
    ELSIF model_name = 'gpt-4o' THEN
        cost_per_1k_tokens := 0.01;  -- Aproximado
    ELSE
        cost_per_1k_tokens := 0.0004;  -- Default: gpt-4o-mini
    END IF;

    -- Calcular custo USD
    cost_usd := (total_tokens::NUMERIC / 1000.0) * cost_per_1k_tokens;

    -- Converter para BRL
    cost_brl := cost_usd * usd_to_brl;

    RETURN ROUND(cost_brl, 4);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_openai_cost_brl IS 'Calcula custo estimado em R$ baseado em tokens consumidos';

-- Exemplo de uso:
-- SELECT calculate_openai_cost_brl(10000, 'gpt-4o-mini');  -- ~R$ 0.0220

-- ============================================================================
-- 6. VERIFICAÇÕES E EXEMPLOS DE QUERIES
-- ============================================================================

-- Verificar configuração de todos os tenants
-- SELECT
--     tenant_id,
--     tenant_name,
--     features->>'use_openai' as openai_enabled,
--     features->>'chatwoot_account_id' as chatwoot_id
-- FROM tenant_configs
-- ORDER BY tenant_id;

-- Verificar custos do mês atual
-- SELECT * FROM v_openai_usage_by_tenant;

-- Verificar histórico mensal
-- SELECT * FROM v_openai_monthly_costs WHERE tenant_id = 1;

-- Habilitar OpenAI para tenant específico (exemplo)
-- UPDATE tenant_configs
-- SET features = features || '{"use_openai": true}'::jsonb
-- WHERE tenant_id = 1;

-- Calcular custo de um ETL run específico
-- SELECT
--     ec.id,
--     ec.started_at,
--     ec.conversations_processed,
--     ec.openai_total_tokens,
--     calculate_openai_cost_brl(ec.openai_total_tokens, 'gpt-4o-mini') as custo_estimado_brl
-- FROM etl_control ec
-- WHERE ec.tenant_id = 1 AND ec.openai_total_tokens > 0
-- ORDER BY ec.started_at DESC
-- LIMIT 10;

-- ============================================================================
-- ROLLBACK (se necessário)
-- ============================================================================

-- Para reverter esta migration:
--
-- DROP VIEW IF EXISTS v_openai_monthly_costs;
-- DROP VIEW IF EXISTS v_openai_usage_by_tenant;
-- DROP FUNCTION IF EXISTS calculate_openai_cost_brl;
--
-- ALTER TABLE etl_control
-- DROP COLUMN IF EXISTS openai_api_calls,
-- DROP COLUMN IF EXISTS openai_total_tokens,
-- DROP COLUMN IF EXISTS openai_cost_brl;
--
-- UPDATE tenant_configs
-- SET features = features - 'use_openai';
