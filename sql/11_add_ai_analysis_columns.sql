-- ============================================================================
-- MIGRATION: FASE 8 - Sistema de Análise Inteligente com OpenAI
-- ============================================================================
-- Descrição: Adiciona colunas para análise de IA focada em remarketing de
--            leads inativos há 24+ horas
-- Data: 2025-11-14
-- Autor: Isaac (Dev Lead)
-- Relacionado: docs/private/checkpoints/FASE8_ANALISE_OPENAI.md
-- ============================================================================

-- Conectar ao banco geniai_analytics
\c geniai_analytics

-- ============================================================================
-- PARTE 1: ADICIONAR COLUNAS DE ANÁLISE DE IA
-- ============================================================================

-- Colunas específicas para sistema de remarketing baseado em tempo de inatividade
-- NOTA: As colunas 'analise_ia' e 'sugestao_disparo' já existem no banco,
--       mas vamos garantir que existam e adicionar as novas colunas específicas

-- 1. Tipo de conversa/remarketing (REMARKETING_RECENTE, MEDIO, FRIO)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS tipo_conversa VARCHAR(50);

COMMENT ON COLUMN conversations_analytics.tipo_conversa IS
'Tipo de remarketing baseado em tempo de inatividade: REMARKETING_RECENTE (24-48h), REMARKETING_MEDIO (48h-7d), REMARKETING_FRIO (7d+)';

-- 2. Análise textual gerada pela IA (já existe, garantir que existe)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS analise_ia TEXT;

COMMENT ON COLUMN conversations_analytics.analise_ia IS
'Análise textual detalhada gerada pela OpenAI sobre o contexto da conversa e perfil do lead';

-- 3. Sugestão de mensagem de remarketing (já existe, garantir que existe)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS sugestao_disparo TEXT;

COMMENT ON COLUMN conversations_analytics.sugestao_disparo IS
'Mensagem de remarketing personalizada gerada com base no template e dados extraídos';

-- 4. Score de prioridade (0-5)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS score_prioridade INTEGER;

-- Adicionar constraint de validação para score_prioridade
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_score_prioridade_range'
    ) THEN
        ALTER TABLE conversations_analytics
        ADD CONSTRAINT check_score_prioridade_range
        CHECK (score_prioridade BETWEEN 0 AND 5);
    END IF;
END
$$;

COMMENT ON COLUMN conversations_analytics.score_prioridade IS
'Score de prioridade do lead (0-5) baseado em urgência, interesse e qualidade da conversa';

-- 5. Dados extraídos pela IA em formato estruturado (JSONB)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS dados_extraidos_ia JSONB;

COMMENT ON COLUMN conversations_analytics.dados_extraidos_ia IS
'Dados estruturados extraídos pela IA: objetivo, objeções, urgência, interesses, etc.';

-- 6. Metadados da análise (tokens, custo, modelo, tempo)
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS metadados_analise_ia JSONB;

COMMENT ON COLUMN conversations_analytics.metadados_analise_ia IS
'Metadados técnicos da análise: modelo usado, tokens consumidos, custo BRL, tempo de execução, versão do prompt';

-- 7. Timestamp de quando foi analisado
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS analisado_em TIMESTAMP;

COMMENT ON COLUMN conversations_analytics.analisado_em IS
'Timestamp de quando a análise de IA foi realizada (usado para detectar reabertura de conversa)';

-- ============================================================================
-- PARTE 2: CRIAR ÍNDICES OTIMIZADOS
-- ============================================================================

-- Índice 1: Query principal do Worker IA (buscar leads inativos 24h+ sem análise)
-- Este índice otimiza a query mais crítica do sistema:
-- WHERE tenant_id = X AND is_lead = true AND analise_ia IS NULL
--   AND mc_last_message_at < NOW() - INTERVAL '24 hours'

CREATE INDEX IF NOT EXISTS idx_conversations_inactive_leads_analysis
ON conversations_analytics(tenant_id, is_lead, mc_last_message_at)
WHERE is_lead = true AND analise_ia IS NULL;

COMMENT ON INDEX idx_conversations_inactive_leads_analysis IS
'Índice otimizado para buscar leads inativos 24h+ que ainda não foram analisados pela IA';

-- Índice 2: Detectar conversas reabertas (nova mensagem após análise)
-- Este índice otimiza a query de reset (FASE 3.5 do ETL):
-- WHERE tenant_id = X AND analise_ia IS NOT NULL
--   AND mc_last_message_at > analisado_em

CREATE INDEX IF NOT EXISTS idx_conversations_reopened
ON conversations_analytics(tenant_id, mc_last_message_at, analisado_em)
WHERE analise_ia IS NOT NULL;

COMMENT ON INDEX idx_conversations_reopened IS
'Índice para detectar conversas reabertas (nova mensagem após análise de IA)';

-- Índice 3: Buscar conversas analisadas por tipo de remarketing (para dashboard)
CREATE INDEX IF NOT EXISTS idx_conversations_tipo_remarketing
ON conversations_analytics(tenant_id, tipo_conversa)
WHERE tipo_conversa IS NOT NULL;

COMMENT ON INDEX idx_conversations_tipo_remarketing IS
'Índice para filtrar conversas por tipo de remarketing no dashboard';

-- Índice 4: Buscar conversas por score de prioridade (para dashboard)
CREATE INDEX IF NOT EXISTS idx_conversations_score_prioridade
ON conversations_analytics(tenant_id, score_prioridade DESC)
WHERE score_prioridade IS NOT NULL;

COMMENT ON INDEX idx_conversations_score_prioridade IS
'Índice para ordenar e filtrar conversas por score de prioridade no dashboard';

-- ============================================================================
-- PARTE 3: ATUALIZAR VALORES DEFAULT PARA COLUNAS EXISTENTES
-- ============================================================================

-- Garantir que colunas antigas de IA tenham valores consistentes
-- (Evita NULLs desnecessários em colunas de texto)

UPDATE conversations_analytics
SET analise_ia = ''
WHERE analise_ia IS NULL;

UPDATE conversations_analytics
SET sugestao_disparo = ''
WHERE sugestao_disparo IS NULL;

-- ============================================================================
-- PARTE 4: VALIDAÇÕES E TESTES
-- ============================================================================

-- Verificar estrutura das novas colunas
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'conversations_analytics'
  AND column_name IN (
      'tipo_conversa',
      'analise_ia',
      'sugestao_disparo',
      'score_prioridade',
      'dados_extraidos_ia',
      'metadados_analise_ia',
      'analisado_em'
  )
ORDER BY ordinal_position;

-- Verificar índices criados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'conversations_analytics'
  AND indexname IN (
      'idx_conversations_inactive_leads_analysis',
      'idx_conversations_reopened',
      'idx_conversations_tipo_remarketing',
      'idx_conversations_score_prioridade'
  );

-- Verificar constraints
SELECT
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'conversations_analytics'::regclass
  AND conname = 'check_score_prioridade_range';

-- ============================================================================
-- PARTE 5: ESTATÍSTICAS E PLANEJAMENTO DE QUERY
-- ============================================================================

-- Atualizar estatísticas das novas colunas para otimizador de queries
ANALYZE conversations_analytics;

-- ============================================================================
-- QUERY DE TESTE: Simular busca de leads inativos 24h+ (FASE 4 do ETL)
-- ============================================================================

-- Esta é a query exata que o Worker IA usará
EXPLAIN ANALYZE
SELECT
    conversation_id,
    display_id,
    message_compiled,
    contact_name,
    inbox_name,
    contact_messages_count,
    mc_last_message_at,
    EXTRACT(EPOCH FROM (NOW() - mc_last_message_at)) / 3600 AS horas_inativo
FROM conversations_analytics
WHERE
    tenant_id = 1  -- AllpFit (exemplo)
    AND is_lead = true
    AND analise_ia IS NULL
    AND mc_last_message_at < NOW() - INTERVAL '24 hours'
    AND contact_messages_count >= 3
    AND message_compiled IS NOT NULL
ORDER BY mc_last_message_at ASC
LIMIT 10;

-- ============================================================================
-- QUERY DE TESTE: Simular detecção de reabertura (FASE 3.5 do ETL)
-- ============================================================================

EXPLAIN ANALYZE
SELECT
    conversation_id,
    display_id,
    mc_last_message_at,
    analisado_em,
    EXTRACT(EPOCH FROM (mc_last_message_at - analisado_em)) / 3600 AS horas_desde_analise
FROM conversations_analytics
WHERE
    tenant_id = 1  -- AllpFit (exemplo)
    AND analise_ia IS NOT NULL
    AND mc_last_message_at > analisado_em
    AND mc_last_message_at > NOW() - INTERVAL '24 hours'
LIMIT 10;

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================

\echo '✅ Migration 11_add_ai_analysis_columns.sql concluída com sucesso!'
\echo ''
\echo '📊 RESUMO:'
\echo '  - 7 colunas adicionadas (tipo_conversa, score_prioridade, dados_extraidos_ia, metadados_analise_ia, analisado_em + 2 existentes)'
\echo '  - 4 índices otimizados criados'
\echo '  - 1 constraint de validação adicionada (score_prioridade 0-5)'
\echo '  - Estatísticas atualizadas'
\echo ''
\echo '🎯 PRÓXIMO PASSO: Criar OpenAILeadAnalyzer'
\echo '   Arquivo: src/multi_tenant/etl_v4/analyzers/openai_lead_analyzer.py'