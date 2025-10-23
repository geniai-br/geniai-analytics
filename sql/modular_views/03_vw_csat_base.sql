-- ============================================================================
-- VIEW 3/6: vw_csat_base
-- Descrição: Dados de satisfação do cliente (CSAT)
-- Performance: ⚡⚡⚡ MUITO RÁPIDA (simples, sem JOINs)
-- ============================================================================

CREATE OR REPLACE VIEW vw_csat_base AS

SELECT
    csat.id AS csat_response_id,
    csat.conversation_id,
    csat.account_id,
    csat.contact_id,
    csat.message_id,
    csat.assigned_agent_id,

    -- ========================================
    -- DADOS DE SATISFAÇÃO
    -- ========================================
    csat.rating AS csat_rating,
    csat.feedback_message AS csat_feedback,

    -- ========================================
    -- TIMESTAMPS
    -- ========================================
    csat.created_at AS csat_created_at,
    csat.updated_at AS csat_updated_at,

    -- ========================================
    -- CLASSIFICAÇÃO DO RATING (NPS)
    -- ========================================
    CASE
        WHEN csat.rating >= 5 THEN 'Promotor'       -- 5 estrelas
        WHEN csat.rating >= 4 THEN 'Neutro'         -- 4 estrelas
        WHEN csat.rating >= 1 THEN 'Detrator'       -- 1-3 estrelas
        ELSE 'Sem Rating'
    END AS csat_nps_category,

    -- ========================================
    -- CLASSIFICAÇÃO QUALITATIVA
    -- ========================================
    CASE
        WHEN csat.rating >= 4 THEN 'Positivo'
        WHEN csat.rating = 3 THEN 'Neutro'
        WHEN csat.rating <= 2 THEN 'Negativo'
        ELSE NULL
    END AS csat_sentiment_category,

    -- ========================================
    -- FLAGS
    -- ========================================
    (csat.feedback_message IS NOT NULL AND csat.feedback_message != '') AS has_written_feedback,
    (LENGTH(csat.feedback_message) > 50) AS has_detailed_feedback

FROM csat_survey_responses csat;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_csat_base IS
'View de satisfação do cliente (CSAT).
Inclui rating, feedback, classificações NPS e flags.
Performance: Muito rápida, sem JOINs.';

GRANT SELECT ON vw_csat_base TO hetzner_dev_isaac_read;
