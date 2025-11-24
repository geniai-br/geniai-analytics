-- ============================================================================
-- Script de Backfill: conversation_period
-- ============================================================================
-- Objetivo: Popular a coluna conversation_period para todos os registros
--           que possuem conversation_created_at válido mas período NULL
--
-- Data: 2025-11-24
-- Fase: FASE 5.5 - Correção de dados históricos
-- ============================================================================

-- Antes do update, vamos ver a situação atual
SELECT
    'ANTES DO UPDATE' as momento,
    COUNT(*) as total_conversas,
    COUNT(conversation_period) as com_periodo,
    COUNT(*) - COUNT(conversation_period) as sem_periodo,
    ROUND(100.0 * COUNT(conversation_period) / COUNT(*), 2) as percentual_preenchido
FROM conversations_analytics;

-- Update principal: calcular período baseado na hora
UPDATE conversations_analytics
SET conversation_period = CASE
    WHEN EXTRACT(HOUR FROM conversation_created_at) BETWEEN 0 AND 5 THEN 'Madrugada'
    WHEN EXTRACT(HOUR FROM conversation_created_at) BETWEEN 6 AND 11 THEN 'Manhã'
    WHEN EXTRACT(HOUR FROM conversation_created_at) BETWEEN 12 AND 17 THEN 'Tarde'
    WHEN EXTRACT(HOUR FROM conversation_created_at) BETWEEN 18 AND 23 THEN 'Noite'
    ELSE NULL
END
WHERE conversation_period IS NULL
  AND conversation_created_at IS NOT NULL;

-- Verificar resultado após update
SELECT
    'APÓS UPDATE' as momento,
    COUNT(*) as total_conversas,
    COUNT(conversation_period) as com_periodo,
    COUNT(*) - COUNT(conversation_period) as sem_periodo,
    ROUND(100.0 * COUNT(conversation_period) / COUNT(*), 2) as percentual_preenchido
FROM conversations_analytics;

-- Distribuição por período após update
SELECT
    conversation_period,
    COUNT(*) as quantidade,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentual
FROM conversations_analytics
WHERE conversation_period IS NOT NULL
GROUP BY conversation_period
ORDER BY CASE conversation_period
    WHEN 'Manhã' THEN 1
    WHEN 'Tarde' THEN 2
    WHEN 'Noite' THEN 3
    WHEN 'Madrugada' THEN 4
    ELSE 99
END;

-- Verificação por tenant
SELECT
    tenant_id,
    COUNT(*) as total,
    COUNT(conversation_period) as com_periodo,
    COUNT(*) - COUNT(conversation_period) as sem_periodo
FROM conversations_analytics
GROUP BY tenant_id
ORDER BY tenant_id;