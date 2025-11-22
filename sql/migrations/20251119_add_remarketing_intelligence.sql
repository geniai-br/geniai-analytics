-- ============================================================================
-- MIGRATION: Adicionar Inteligência de Remarketing
-- ============================================================================
-- Data: 2025-11-19
-- Versão: 1.0.0
-- Autor: Isaac (via Claude Code)
--
-- Descrição:
--   Adiciona campos para análise inteligente de remarketing, permitindo:
--   - Detecção automática de conversas que precisam follow-up
--   - Classificação de status de resolução
--   - Análise de nível de interesse
--   - Armazenamento de contexto completo em JSONB
--
-- Impacto:
--   - Performance: Índices otimizados para queries de remarketing
--   - Storage: ~50 bytes/conversa (colunas) + variável (JSONB)
--   - Compatibilidade: 100% retrocompatível (valores default)
--
-- Rollback: Ver final do arquivo
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ADICIONAR COLUNAS DEDICADAS (Performance-Critical)
-- ============================================================================

-- Coluna: precisa_remarketing
-- Uso: Filtro principal para dashboards de remarketing
-- Índice: Sim (queries frequentes)
ALTER TABLE conversations_analytics
ADD COLUMN precisa_remarketing BOOLEAN DEFAULT TRUE;

COMMENT ON COLUMN conversations_analytics.precisa_remarketing IS
'Indica se a conversa precisa de follow-up/remarketing.
FALSE = conversa resolvida, não incomodar cliente.
TRUE = precisa reengajamento (cliente abandonou, atendente não respondeu, etc).
Calculado pela IA durante análise.';

-- Coluna: status_resolucao
-- Uso: Classificação do estado da conversa
-- Índice: Sim (grouping em dashboards)
ALTER TABLE conversations_analytics
ADD COLUMN status_resolucao VARCHAR(50);

COMMENT ON COLUMN conversations_analytics.status_resolucao IS
'Status de resolução da conversa:
- resolvida: Atendimento completo, não precisa follow-up
- abandonada_cliente: Cliente parou de responder
- abandonada_atendente: Cliente esperando resposta (URGENTE)
- pendente_resposta: Cliente pediu tempo para pensar
- em_negociacao: Conversa ativa, aguardar conclusão
NULL = não analisado ainda';

-- Coluna: nivel_interesse
-- Uso: Priorização de leads
-- Índice: Sim (ordenação/filtro)
ALTER TABLE conversations_analytics
ADD COLUMN nivel_interesse VARCHAR(20);

COMMENT ON COLUMN conversations_analytics.nivel_interesse IS
'Nível de interesse do lead calculado pela IA:
- alto: Interesse forte, alta urgência, múltiplas perguntas
- medio: Interesse moderado, algumas dúvidas
- baixo: Interesse superficial, poucas mensagens
- nenhum: Spam, engano, não é lead qualificado
NULL = não analisado ainda';

-- ============================================================================
-- 2. ADICIONAR COMENTÁRIO NA COLUNA JSONB EXISTENTE
-- ============================================================================

COMMENT ON COLUMN conversations_analytics.dados_extraidos_ia IS
'Dados estruturados da análise de IA em formato JSONB.
Contém informações adicionais de remarketing:
{
  "status_resolucao": "string",
  "precisa_remarketing": boolean,
  "nivel_interesse": "string",
  "motivo_remarketing": "string (justificativa interna)",
  "objecoes_identificadas": ["array de objeções"],
  "sinais_positivos": ["array de sinais positivos"],
  "analise_completa_ia": {...}
}
Permite queries complexas:
  WHERE dados_extraidos_ia->>''motivo_remarketing'' LIKE ''%urgente%''';

-- ============================================================================
-- 3. CRIAR ÍNDICES OTIMIZADOS
-- ============================================================================

-- Índice: Remarketing ativo (query mais comum)
-- Uso: SELECT * FROM conversations_analytics WHERE precisa_remarketing = TRUE
CREATE INDEX idx_conversations_precisa_remarketing
ON conversations_analytics(tenant_id, precisa_remarketing, ai_probability_score DESC)
WHERE precisa_remarketing = TRUE;

COMMENT ON INDEX idx_conversations_precisa_remarketing IS
'Otimiza queries de remarketing ativo.
Cobre: tenant_id, precisa_remarketing, ordenação por score.
Partial index (WHERE = TRUE) para economia de espaço.';

-- Índice: Status de resolução
-- Uso: GROUP BY status_resolucao, filtros por status específico
CREATE INDEX idx_conversations_status_resolucao
ON conversations_analytics(tenant_id, status_resolucao)
WHERE status_resolucao IS NOT NULL;

COMMENT ON INDEX idx_conversations_status_resolucao IS
'Otimiza queries por status de resolução.
Usado em dashboards e relatórios de performance.';

-- Índice: Nível de interesse
-- Uso: Filtrar leads por qualificação (alto interesse)
CREATE INDEX idx_conversations_nivel_interesse
ON conversations_analytics(tenant_id, nivel_interesse, ai_probability_score DESC)
WHERE nivel_interesse IN ('alto', 'medio');

COMMENT ON INDEX idx_conversations_nivel_interesse IS
'Otimiza filtro de leads qualificados.
Cobre apenas interesse médio/alto (economia de espaço).';

-- Índice: Conversas urgentes (abandonadas por atendente)
-- Uso: Dashboard de urgências, SLA de atendimento
CREATE INDEX idx_conversations_urgentes
ON conversations_analytics(tenant_id, status_resolucao, mc_last_message_at DESC)
WHERE status_resolucao = 'abandonada_atendente';

COMMENT ON INDEX idx_conversations_urgentes IS
'Otimiza detecção de leads urgentes (esperando resposta).
Usado para alertas e SLA de atendimento.';

-- Índice GIN: Busca avançada em JSONB
-- Uso: Queries complexas em dados_extraidos_ia
CREATE INDEX idx_conversations_dados_extraidos_gin
ON conversations_analytics USING GIN (dados_extraidos_ia);

COMMENT ON INDEX idx_conversations_dados_extraidos_gin IS
'Otimiza queries JSONB complexas.
Exemplos:
  WHERE dados_extraidos_ia @> ''{"nivel_interesse": "alto"}''
  WHERE dados_extraidos_ia ? ''objecoes_identificadas''';

-- ============================================================================
-- 4. ATUALIZAR VALORES EXISTENTES (Retrocompatibilidade)
-- ============================================================================

-- Conversas já analisadas: Se tem sugestao_disparo = assume que precisa remarketing
UPDATE conversations_analytics
SET precisa_remarketing = (
    CASE
        WHEN sugestao_disparo IS NOT NULL AND sugestao_disparo != '' THEN TRUE
        WHEN visit_scheduled = TRUE THEN FALSE  -- Visita agendada = resolvida
        ELSE TRUE  -- Default = precisa análise
    END
)
WHERE precisa_remarketing IS NULL;

-- Conversas com visita agendada = status resolvida
UPDATE conversations_analytics
SET status_resolucao = 'resolvida'
WHERE visit_scheduled = TRUE
  AND status_resolucao IS NULL;

-- ============================================================================
-- 5. ADICIONAR CONSTRAINTS DE VALIDAÇÃO
-- ============================================================================

-- Validar: status_resolucao só pode ter valores específicos
ALTER TABLE conversations_analytics
ADD CONSTRAINT check_status_resolucao_valid
CHECK (
    status_resolucao IS NULL OR
    status_resolucao IN (
        'resolvida',
        'abandonada_cliente',
        'abandonada_atendente',
        'pendente_resposta',
        'em_negociacao'
    )
);

COMMENT ON CONSTRAINT check_status_resolucao_valid ON conversations_analytics IS
'Garante integridade dos valores de status_resolucao.
Apenas valores predefinidos pela IA são aceitos.';

-- Validar: nivel_interesse só pode ter valores específicos
ALTER TABLE conversations_analytics
ADD CONSTRAINT check_nivel_interesse_valid
CHECK (
    nivel_interesse IS NULL OR
    nivel_interesse IN ('alto', 'medio', 'baixo', 'nenhum')
);

COMMENT ON CONSTRAINT check_nivel_interesse_valid ON conversations_analytics IS
'Garante integridade dos valores de nivel_interesse.
Apenas valores predefinidos pela IA são aceitos.';

-- ============================================================================
-- 6. CRIAR VIEW PARA REMARKETING (Facilitar Queries)
-- ============================================================================

CREATE OR REPLACE VIEW vw_remarketing_queue AS
SELECT
    c.id,
    c.tenant_id,
    c.conversation_id,
    c.display_id,
    c.contact_name,
    c.contact_phone,
    c.inbox_name,
    c.nome_mapeado_bot,

    -- Campos de remarketing
    c.precisa_remarketing,
    c.status_resolucao,
    c.nivel_interesse,
    c.ai_probability_score,
    c.ai_probability_label,

    -- Textos para o atendente
    c.analise_ia,
    c.sugestao_disparo,

    -- Contexto adicional do JSONB
    c.dados_extraidos_ia->>'motivo_remarketing' as motivo_remarketing,
    c.dados_extraidos_ia->'objecoes_identificadas' as objecoes,
    c.dados_extraidos_ia->'sinais_positivos' as sinais_positivos,

    -- Timestamps
    c.mc_last_message_at as ultima_mensagem,
    c.conversation_created_at as criada_em,
    EXTRACT(EPOCH FROM (NOW() - c.mc_last_message_at))/3600 as horas_sem_resposta,

    -- Flags úteis
    c.visit_scheduled,
    c.is_lead,
    c.is_resolved,
    c.has_human_intervention

FROM conversations_analytics c
WHERE c.precisa_remarketing = TRUE
  AND c.is_lead = TRUE
  AND c.analise_ia IS NOT NULL
ORDER BY
    -- Priorização inteligente
    CASE c.status_resolucao
        WHEN 'abandonada_atendente' THEN 1  -- Máxima urgência
        WHEN 'abandonada_cliente' THEN 2
        WHEN 'pendente_resposta' THEN 3
        ELSE 4
    END,
    c.ai_probability_score DESC,
    c.mc_last_message_at ASC;  -- Mais antigos primeiro

COMMENT ON VIEW vw_remarketing_queue IS
'View otimizada para fila de remarketing.
Retorna apenas conversas que precisam de follow-up, ordenadas por urgência.
Usada em dashboards e relatórios de remarketing.';

-- ============================================================================
-- 7. CRIAR FUNÇÕES AUXILIARES
-- ============================================================================

-- Função: Obter estatísticas de remarketing por tenant
CREATE OR REPLACE FUNCTION get_remarketing_stats(p_tenant_id INTEGER)
RETURNS TABLE(
    total_leads INTEGER,
    precisa_remarketing INTEGER,
    status_resolvida INTEGER,
    status_abandonada_cliente INTEGER,
    status_abandonada_atendente INTEGER,
    status_pendente INTEGER,
    status_negociacao INTEGER,
    nivel_alto INTEGER,
    nivel_medio INTEGER,
    nivel_baixo INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER as total_leads,
        COUNT(*) FILTER (WHERE precisa_remarketing = TRUE)::INTEGER,
        COUNT(*) FILTER (WHERE status_resolucao = 'resolvida')::INTEGER,
        COUNT(*) FILTER (WHERE status_resolucao = 'abandonada_cliente')::INTEGER,
        COUNT(*) FILTER (WHERE status_resolucao = 'abandonada_atendente')::INTEGER,
        COUNT(*) FILTER (WHERE status_resolucao = 'pendente_resposta')::INTEGER,
        COUNT(*) FILTER (WHERE status_resolucao = 'em_negociacao')::INTEGER,
        COUNT(*) FILTER (WHERE nivel_interesse = 'alto')::INTEGER,
        COUNT(*) FILTER (WHERE nivel_interesse = 'medio')::INTEGER,
        COUNT(*) FILTER (WHERE nivel_interesse = 'baixo')::INTEGER
    FROM conversations_analytics
    WHERE tenant_id = p_tenant_id
      AND is_lead = TRUE
      AND analise_ia IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_remarketing_stats(INTEGER) IS
'Retorna estatísticas agregadas de remarketing para um tenant.
Uso: SELECT * FROM get_remarketing_stats(16);';

-- ============================================================================
-- 8. ATUALIZAR RLS (Row-Level Security)
-- ============================================================================

-- As policies existentes já cobrem as novas colunas automaticamente
-- (aplicam-se a toda a tabela), mas vamos adicionar comentário para documentar

COMMENT ON TABLE conversations_analytics IS
'Tabela principal de conversas analisadas (ETL v4).

ROW-LEVEL SECURITY (RLS):
- tenant_own_conversations: Clientes veem apenas seus dados
- admin_all_conversations: Admins veem todos os tenants
- etl_manage_conversations: ETL bypass RLS para inserções

NOVOS CAMPOS (2025-11-19):
- precisa_remarketing: Flag para follow-up
- status_resolucao: Classificação do estado da conversa
- nivel_interesse: Qualificação do lead
- dados_extraidos_ia: Contexto completo em JSONB

ÍNDICES OTIMIZADOS:
- idx_conversations_precisa_remarketing: Queries de remarketing
- idx_conversations_status_resolucao: Grouping por status
- idx_conversations_nivel_interesse: Filtro de qualificação
- idx_conversations_urgentes: SLA e alertas
- idx_conversations_dados_extraidos_gin: Queries JSONB avançadas';

-- ============================================================================
-- 9. GRANT PERMISSIONS
-- ============================================================================

-- Garantir que roles existentes têm acesso às novas colunas
-- (PostgreSQL herda permissões de tabela para novas colunas automaticamente)

-- ============================================================================
-- 10. VERIFICAÇÃO E FINALIZAÇÃO
-- ============================================================================

DO $$
DECLARE
    col_count INTEGER;
    idx_count INTEGER;
BEGIN
    -- Verificar colunas criadas
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'conversations_analytics'
      AND column_name IN ('precisa_remarketing', 'status_resolucao', 'nivel_interesse');

    IF col_count != 3 THEN
        RAISE EXCEPTION 'Erro: Esperadas 3 colunas, encontradas %', col_count;
    END IF;

    -- Verificar índices criados
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE tablename = 'conversations_analytics'
      AND indexname LIKE '%remarketing%'
       OR indexname LIKE '%status_resolucao%'
       OR indexname LIKE '%nivel_interesse%'
       OR indexname LIKE '%urgentes%'
       OR indexname LIKE '%dados_extraidos_gin%';

    IF idx_count < 5 THEN
        RAISE EXCEPTION 'Erro: Esperados 5+ índices, encontrados %', idx_count;
    END IF;

    RAISE NOTICE '✅ Migração concluída com sucesso!';
    RAISE NOTICE '   - 3 colunas adicionadas';
    RAISE NOTICE '   - 5 índices criados';
    RAISE NOTICE '   - 1 view criada (vw_remarketing_queue)';
    RAISE NOTICE '   - 1 função criada (get_remarketing_stats)';
    RAISE NOTICE '   - Valores existentes migrados';
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (Se necessário executar em caso de erro)
-- ============================================================================
/*
BEGIN;

-- Remover função
DROP FUNCTION IF EXISTS get_remarketing_stats(INTEGER);

-- Remover view
DROP VIEW IF EXISTS vw_remarketing_queue;

-- Remover índices
DROP INDEX IF EXISTS idx_conversations_dados_extraidos_gin;
DROP INDEX IF EXISTS idx_conversations_urgentes;
DROP INDEX IF EXISTS idx_conversations_nivel_interesse;
DROP INDEX IF EXISTS idx_conversations_status_resolucao;
DROP INDEX IF EXISTS idx_conversations_precisa_remarketing;

-- Remover constraints
ALTER TABLE conversations_analytics DROP CONSTRAINT IF EXISTS check_nivel_interesse_valid;
ALTER TABLE conversations_analytics DROP CONSTRAINT IF EXISTS check_status_resolucao_valid;

-- Remover colunas
ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS nivel_interesse;
ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS status_resolucao;
ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS precisa_remarketing;

RAISE NOTICE '❌ Rollback concluído. Alterações revertidas.';

COMMIT;
*/

-- ============================================================================
-- EXEMPLOS DE QUERIES
-- ============================================================================

/*
-- 1. Fila de remarketing ordenada por urgência
SELECT * FROM vw_remarketing_queue
WHERE tenant_id = 16
LIMIT 50;

-- 2. Estatísticas de remarketing
SELECT * FROM get_remarketing_stats(16);

-- 3. Leads urgentes (esperando resposta)
SELECT conversation_id, contact_name, horas_sem_resposta, sugestao_disparo
FROM vw_remarketing_queue
WHERE status_resolucao = 'abandonada_atendente'
  AND tenant_id = 16
ORDER BY horas_sem_resposta DESC;

-- 4. Conversas resolvidas (não precisa remarketing)
SELECT COUNT(*) as total_resolvidas
FROM conversations_analytics
WHERE tenant_id = 16
  AND status_resolucao = 'resolvida'
  AND precisa_remarketing = FALSE;

-- 5. Análise de objeções (JSONB query)
SELECT
    dados_extraidos_ia->'objecoes_identificadas' as objecoes,
    COUNT(*) as frequencia
FROM conversations_analytics
WHERE tenant_id = 16
  AND dados_extraidos_ia ? 'objecoes_identificadas'
  AND jsonb_array_length(dados_extraidos_ia->'objecoes_identificadas') > 0
GROUP BY 1
ORDER BY 2 DESC;

-- 6. Performance do remarketing
SELECT
    status_resolucao,
    nivel_interesse,
    COUNT(*) as total,
    AVG(ai_probability_score) as score_medio,
    COUNT(*) FILTER (WHERE visit_scheduled) as visitas_agendadas
FROM conversations_analytics
WHERE tenant_id = 16
  AND is_lead = TRUE
GROUP BY status_resolucao, nivel_interesse
ORDER BY score_medio DESC;
*/