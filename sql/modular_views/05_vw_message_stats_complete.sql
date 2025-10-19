-- ============================================================================
-- VIEW 5/6: vw_message_stats_complete
-- Descrição: Estatísticas detalhadas de mensagens por conversa
-- Performance: ⚡⚡ MÉDIA (agregações sobre messages)
-- ============================================================================

CREATE OR REPLACE VIEW vw_message_stats_complete AS

SELECT
    m.conversation_id,

    -- ========================================
    -- CONTADORES DE MENSAGENS POR TIPO
    -- ========================================

    -- Total de mensagens (públicas)
    COUNT(*) FILTER (WHERE m.private = false) AS total_messages_public,

    -- Mensagens do agente/usuário
    COUNT(*) FILTER (WHERE m.sender_type = 'User' AND m.private = false) AS user_messages_count,

    -- Mensagens do contato/cliente
    COUNT(*) FILTER (WHERE m.sender_type = 'Contact' AND m.private = false) AS contact_messages_count,

    -- Mensagens do sistema
    COUNT(*) FILTER (
        WHERE m.private = false
        AND (m.sender_type IS NULL OR m.sender_type NOT IN ('User', 'Contact'))
    ) AS system_messages_count,

    -- Notas privadas/internas
    COUNT(*) FILTER (WHERE m.private = true) AS private_notes_count,

    -- ========================================
    -- PRIMEIRA E ÚLTIMA MENSAGEM (TEXTOS)
    -- ========================================

    -- Primeira mensagem (texto)
    (ARRAY_AGG(m.content ORDER BY m.created_at)
     FILTER (WHERE m.private = false))[1] AS first_message_text,

    -- Última mensagem (texto)
    (ARRAY_AGG(m.content ORDER BY m.created_at DESC)
     FILTER (WHERE m.private = false))[1] AS last_message_text,

    -- Tipo do sender da primeira mensagem
    (ARRAY_AGG(m.sender_type ORDER BY m.created_at)
     FILTER (WHERE m.private = false))[1] AS first_message_sender_type,

    -- Tipo do sender da última mensagem
    (ARRAY_AGG(m.sender_type ORDER BY m.created_at DESC)
     FILTER (WHERE m.private = false))[1] AS last_message_sender_type,

    -- ========================================
    -- TIMESTAMPS DE MENSAGENS
    -- ========================================

    -- Data da primeira mensagem
    MIN(m.created_at) FILTER (WHERE m.private = false) AS first_message_at,

    -- Data da última mensagem
    MAX(m.created_at) FILTER (WHERE m.private = false) AS last_message_at,

    -- ========================================
    -- MÉTRICAS DE TEMPO
    -- ========================================

    -- Duração total da conversa (primeira até última mensagem)
    CASE
        WHEN MAX(m.created_at) FILTER (WHERE m.private = false) IS NOT NULL
             AND MIN(m.created_at) FILTER (WHERE m.private = false) IS NOT NULL
        THEN EXTRACT(EPOCH FROM (
            MAX(m.created_at) FILTER (WHERE m.private = false) -
            MIN(m.created_at) FILTER (WHERE m.private = false)
        ))::INTEGER
        ELSE NULL
    END AS conversation_duration_seconds,

    -- Tempo médio entre mensagens
    CASE
        WHEN COUNT(*) FILTER (WHERE m.private = false) > 1
             AND MAX(m.created_at) FILTER (WHERE m.private = false) IS NOT NULL
             AND MIN(m.created_at) FILTER (WHERE m.private = false) IS NOT NULL
        THEN ROUND(
            EXTRACT(EPOCH FROM (
                MAX(m.created_at) FILTER (WHERE m.private = false) -
                MIN(m.created_at) FILTER (WHERE m.private = false)
            )) / NULLIF((COUNT(*) FILTER (WHERE m.private = false) - 1), 0),
            1
        )
        ELSE NULL
    END AS avg_time_between_messages_seconds,

    -- ========================================
    -- ANÁLISE DE SENTIMENT
    -- ========================================

    -- Média de sentiment das mensagens (se disponível)
    ROUND(
        AVG(
            CASE
                WHEN m.sentiment IS NOT NULL
                THEN m.sentiment::NUMERIC
                ELSE NULL
            END
        ),
        3
    ) AS avg_sentiment_score,

    -- Quantidade de mensagens com sentiment
    COUNT(*) FILTER (WHERE m.sentiment IS NOT NULL) AS messages_with_sentiment_count,

    -- ========================================
    -- ANÁLISE DE CONTEÚDO
    -- ========================================

    -- Tamanho médio das mensagens (caracteres)
    ROUND(
        AVG(LENGTH(m.content))
        FILTER (WHERE m.private = false AND m.content IS NOT NULL),
        0
    )::INTEGER AS avg_message_length,

    -- Mensagem mais longa (tamanho)
    MAX(LENGTH(m.content))
    FILTER (WHERE m.private = false AND m.content IS NOT NULL) AS max_message_length,

    -- ========================================
    -- FLAGS BOOLEANOS
    -- ========================================

    -- Teve mensagem do agente?
    (COUNT(*) FILTER (WHERE m.sender_type = 'User') > 0) AS has_user_messages,

    -- Teve mensagem do contato?
    (COUNT(*) FILTER (WHERE m.sender_type = 'Contact') > 0) AS has_contact_messages,

    -- Tem notas privadas?
    (COUNT(*) FILTER (WHERE m.private = true) > 0) AS has_private_notes,

    -- Cliente respondeu?
    (COUNT(*) FILTER (WHERE m.sender_type = 'Contact') > 0) AS has_contact_reply,

    -- É uma conversa curta? (<=5 mensagens)
    (COUNT(*) FILTER (WHERE m.private = false) <= 5) AS is_short_conversation,

    -- É uma conversa longa? (>20 mensagens)
    (COUNT(*) FILTER (WHERE m.private = false) > 20) AS is_long_conversation,

    -- ========================================
    -- RATIOS E PROPORÇÕES
    -- ========================================

    -- Proporção de mensagens do agente vs total
    CASE
        WHEN COUNT(*) FILTER (WHERE m.private = false) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE m.sender_type = 'User' AND m.private = false)::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE m.private = false), 0),
            2
        )
        ELSE NULL
    END AS user_message_ratio,

    -- Proporção de mensagens do contato vs total
    CASE
        WHEN COUNT(*) FILTER (WHERE m.private = false) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE m.sender_type = 'Contact')::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE m.private = false), 0),
            2
        )
        ELSE NULL
    END AS contact_message_ratio

FROM messages m

GROUP BY m.conversation_id;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_message_stats_complete IS
'View de estatísticas detalhadas de mensagens por conversa.
Inclui: contadores, textos, timestamps, métricas de tempo, sentiment, flags.
Performance: Média devido a múltiplas agregações.';

GRANT SELECT ON vw_message_stats_complete TO hetzner_dev_isaac_read;
