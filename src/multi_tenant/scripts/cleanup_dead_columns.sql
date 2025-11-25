-- ============================================================================
-- Script de Limpeza: Remoção de Colunas Mortas
-- ============================================================================
-- Objetivo: Remover colunas que estão sempre NULL e não são utilizadas
--
-- Data: 2025-11-25
-- Fase: REFACTOR - Cleanup dead code and columns
-- ============================================================================

-- IMPORTANTE: Execute este script APENAS após confirmar que:
-- 1. O ETL foi atualizado para não extrair mais essas colunas
-- 2. O dashboard foi atualizado para não usar essas colunas
-- 3. Você tem um backup do banco de dados

-- ============================================================================
-- VERIFICAÇÃO PRÉ-REMOÇÃO
-- ============================================================================

\echo '=============================================='
\echo 'VERIFICAÇÃO PRÉ-REMOÇÃO DE COLUNAS'
\echo '=============================================='

-- Verificar se as colunas realmente estão 100% NULL
SELECT
    'campaign_id' as coluna,
    COUNT(*) as total,
    COUNT(campaign_id) as preenchidos,
    ROUND(100.0 * COUNT(campaign_id) / NULLIF(COUNT(*), 0), 2) as percentual
FROM conversations_analytics
UNION ALL
SELECT
    'contact_email',
    COUNT(*),
    COUNT(contact_email),
    ROUND(100.0 * COUNT(contact_email) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics
UNION ALL
SELECT
    'csat_rating',
    COUNT(*),
    COUNT(csat_rating),
    ROUND(100.0 * COUNT(csat_rating) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics
UNION ALL
SELECT
    'csat_feedback',
    COUNT(*),
    COUNT(csat_feedback),
    ROUND(100.0 * COUNT(csat_feedback) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics
UNION ALL
SELECT
    'csat_nps_category',
    COUNT(*),
    COUNT(csat_nps_category),
    ROUND(100.0 * COUNT(csat_nps_category) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics
UNION ALL
SELECT
    'is_weekday',
    COUNT(*),
    COUNT(is_weekday),
    ROUND(100.0 * COUNT(is_weekday) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics
UNION ALL
SELECT
    'is_business_hours',
    COUNT(*),
    COUNT(is_business_hours),
    ROUND(100.0 * COUNT(is_business_hours) / NULLIF(COUNT(*), 0), 2)
FROM conversations_analytics;

\echo ''
\echo 'Se alguma coluna acima tiver preenchidos > 0, NÃO execute a remoção!'
\echo ''

-- ============================================================================
-- REMOÇÃO DAS COLUNAS (DESCOMENTE PARA EXECUTAR)
-- ============================================================================

-- CUIDADO: As linhas abaixo irão REMOVER permanentemente as colunas!
-- Descomente apenas se tiver certeza e backup.

-- \echo 'Removendo colunas mortas...'

-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS campaign_id;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS contact_email;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_response_id;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_rating;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_feedback;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_created_at;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_nps_category;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS csat_sentiment_category;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS has_written_feedback;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS has_detailed_feedback;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS has_csat;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS is_weekday;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS is_business_hours;
-- ALTER TABLE conversations_analytics DROP COLUMN IF EXISTS is_from_campaign;

-- \echo '✅ Colunas removidas com sucesso!'

-- ============================================================================
-- VERIFICAÇÃO PÓS-REMOÇÃO
-- ============================================================================

\echo ''
\echo 'Contagem atual de colunas na tabela:'
SELECT COUNT(*) as total_colunas
FROM information_schema.columns
WHERE table_name = 'conversations_analytics'
  AND table_schema = 'public';

\echo ''
\echo 'Lista de colunas restantes:'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'conversations_analytics'
  AND table_schema = 'public'
ORDER BY ordinal_position;