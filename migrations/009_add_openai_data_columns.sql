-- Migration: Add OpenAI Data Columns to conversations_analytics
-- Date: 2025-11-09
-- Fase: 5.6 - OpenAI Integration (Part 2)
-- Descrição: Adiciona colunas para armazenar dados extraídos pelo OpenAI

-- ============================================================================
-- ADICIONAR COLUNAS DE DADOS OPENAI EM conversations_analytics
-- ============================================================================

-- Colunas para dados extraídos pelo OpenAI
ALTER TABLE conversations_analytics
ADD COLUMN IF NOT EXISTS nome_mapeado_bot TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS condicao_fisica TEXT DEFAULT 'Não mencionado',
ADD COLUMN IF NOT EXISTS objetivo TEXT DEFAULT 'Não mencionado',
ADD COLUMN IF NOT EXISTS analise_ia TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS sugestao_disparo TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS probabilidade_conversao INTEGER DEFAULT 0;

-- Comentários
COMMENT ON COLUMN conversations_analytics.nome_mapeado_bot IS 'Nome completo do lead extraído pela IA';
COMMENT ON COLUMN conversations_analytics.condicao_fisica IS 'Condição física do lead (Sedentário | Iniciante | Intermediário | Avançado | Não mencionado)';
COMMENT ON COLUMN conversations_analytics.objetivo IS 'Objetivo do lead (Perda de peso | Ganho de massa | etc)';
COMMENT ON COLUMN conversations_analytics.analise_ia IS 'Análise detalhada da conversa gerada pela IA (3-5 parágrafos)';
COMMENT ON COLUMN conversations_analytics.sugestao_disparo IS 'Mensagem personalizada sugerida pela IA para enviar ao lead';
COMMENT ON COLUMN conversations_analytics.probabilidade_conversao IS 'Probabilidade de conversão 0-5 (OpenAI raw score antes de conversão para 0-100)';

-- Índices para melhor performance em queries
CREATE INDEX IF NOT EXISTS idx_conv_analytics_nome_mapeado
    ON conversations_analytics (nome_mapeado_bot)
    WHERE nome_mapeado_bot != '';

CREATE INDEX IF NOT EXISTS idx_conv_analytics_condicao_fisica
    ON conversations_analytics (condicao_fisica)
    WHERE condicao_fisica != 'Não mencionado';

CREATE INDEX IF NOT EXISTS idx_conv_analytics_objetivo
    ON conversations_analytics (objetivo)
    WHERE objetivo != 'Não mencionado';

CREATE INDEX IF NOT EXISTS idx_conv_analytics_prob_conversao
    ON conversations_analytics (probabilidade_conversao)
    WHERE probabilidade_conversao > 0;

-- Verificação
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'conversations_analytics'
--   AND column_name IN ('nome_mapeado_bot', 'condicao_fisica', 'objetivo', 'analise_ia', 'sugestao_disparo', 'probabilidade_conversao')
-- ORDER BY column_name;