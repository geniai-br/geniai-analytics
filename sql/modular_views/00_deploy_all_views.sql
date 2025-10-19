-- ============================================================================
-- SCRIPT MASTER: Deploy de TODAS as Views Modulares
-- Descrição: Cria as 7 views em ordem de dependência
-- Uso: Execute este arquivo para criar todas as views de uma vez
-- ============================================================================

\echo '============================================================================'
\echo 'DEPLOY DAS VIEWS MODULARES - AllpFit Analytics'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- CAMADA 1: Views Base (sem dependências)
-- ============================================================================

\echo 'CAMADA 1: Criando views base...'
\echo ''

\echo '  [1/7] Criando vw_conversations_base_complete...'
\i 01_vw_conversations_base_complete.sql
\echo '  ✓ vw_conversations_base_complete criada!'
\echo ''

\echo '  [2/7] Criando vw_messages_compiled_complete...'
\i 02_vw_messages_compiled_complete.sql
\echo '  ✓ vw_messages_compiled_complete criada!'
\echo ''

\echo '  [3/7] Criando vw_csat_base...'
\i 03_vw_csat_base.sql
\echo '  ✓ vw_csat_base criada!'
\echo ''

-- ============================================================================
-- CAMADA 2: Views de Métricas (dependem apenas de tabelas base)
-- ============================================================================

\echo 'CAMADA 2: Criando views de métricas...'
\echo ''

\echo '  [4/7] Criando vw_conversation_metrics_complete...'
\i 04_vw_conversation_metrics_complete.sql
\echo '  ✓ vw_conversation_metrics_complete criada!'
\echo ''

\echo '  [5/7] Criando vw_message_stats_complete...'
\i 05_vw_message_stats_complete.sql
\echo '  ✓ vw_message_stats_complete criada!'
\echo ''

\echo '  [6/7] Criando vw_temporal_metrics...'
\i 06_vw_temporal_metrics.sql
\echo '  ✓ vw_temporal_metrics criada!'
\echo ''

-- ============================================================================
-- CAMADA 3: View Final (depende de todas as anteriores)
-- ============================================================================

\echo 'CAMADA 3: Criando view final...'
\echo ''

\echo '  [7/7] Criando vw_conversations_analytics_final...'
\i 07_vw_conversations_analytics_final.sql
\echo '  ✓ vw_conversations_analytics_final criada!'
\echo ''

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

\echo '============================================================================'
\echo 'VERIFICANDO VIEWS CRIADAS'
\echo '============================================================================'
\echo ''

SELECT
    schemaname,
    viewname,
    viewowner
FROM pg_views
WHERE viewname LIKE 'vw_%'
  AND schemaname = 'public'
ORDER BY viewname;

\echo ''
\echo '============================================================================'
\echo 'TESTANDO VIEW FINAL'
\echo '============================================================================'
\echo ''

-- Contar registros
SELECT COUNT(*) as total_conversas
FROM vw_conversations_analytics_final;

\echo ''

-- Mostrar amostra de 1 registro
SELECT *
FROM vw_conversations_analytics_final
LIMIT 1;

\echo ''
\echo '============================================================================'
\echo '✓ DEPLOY CONCLUÍDO COM SUCESSO!'
\echo '============================================================================'
\echo ''
\echo 'Views criadas:'
\echo '  1. vw_conversations_base_complete'
\echo '  2. vw_messages_compiled_complete'
\echo '  3. vw_csat_base'
\echo '  4. vw_conversation_metrics_complete'
\echo '  5. vw_message_stats_complete'
\echo '  6. vw_temporal_metrics'
\echo '  7. vw_conversations_analytics_final ← Use esta no ETL!'
\echo ''
\echo 'Próximo passo: Atualizar ETL para extrair de vw_conversations_analytics_final'
\echo ''
