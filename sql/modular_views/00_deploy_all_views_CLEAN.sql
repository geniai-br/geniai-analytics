-- ============================================================================
-- SCRIPT COMPLETO DE DEPLOY DAS 7 VIEWS - VERSÃO LIMPA E OTIMIZADA
-- ============================================================================
-- Este script cria todas as 7 views em ordem, removendo campos problemáticos
-- Execute este script inteiro de uma vez no banco de produção
-- ============================================================================

-- ============================================================================
-- VIEW 1/6: vw_conversations_base_complete
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversations_base_complete AS

SELECT
    -- Identificadores
    c.id AS conversation_id,
    c.display_id,
    c.uuid AS conversation_uuid,
    c.account_id,

    -- Status e classificação
    c.status,
    c.priority,
    c.snoozed_until,

    -- Atribuição
    c.assignee_id,
    c.team_id,
    c.campaign_id,

    -- Relacionamentos
    c.contact_id,
    c.inbox_id,

    -- Timestamps
    c.created_at AS conversation_created_at,
    c.updated_at AS conversation_updated_at,
    c.last_activity_at,
    c.first_reply_created_at,
    c.waiting_since,
    c.contact_last_seen_at,
    c.agent_last_seen_at,

    -- Contato
    cont.name AS contact_name,
    cont.email AS contact_email,
    cont.phone_number AS contact_phone,
    cont.identifier AS contact_identifier,

    -- Inbox
    i.name AS inbox_name,
    i.channel_type AS inbox_channel_type,
    i.timezone AS inbox_timezone,

    -- Agente
    u.name AS assignee_name,
    u.email AS assignee_email,

    -- Time
    t.name AS team_name,

    -- Conta
    acc.name AS account_name

FROM conversations c
LEFT JOIN contacts cont ON cont.id = c.contact_id
LEFT JOIN inboxes i ON i.id = c.inbox_id
LEFT JOIN users u ON u.id = c.assignee_id
LEFT JOIN teams t ON t.id = c.team_id
LEFT JOIN accounts acc ON acc.id = c.account_id;

COMMENT ON VIEW vw_conversations_base_complete IS 'View base com dados principais das conversas';
GRANT SELECT ON vw_conversations_base_complete TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 2/6: vw_messages_compiled_complete
-- ============================================================================

CREATE OR REPLACE VIEW vw_messages_compiled_complete AS

SELECT
    m.conversation_id,

    -- JSON com todas as mensagens
    jsonb_agg(
        jsonb_build_object(
            'message_id', m.id,
            'text', m.content,
            'sender', m.sender_type,
            'sender_id', m.sender_id,
            'sent_at', m.created_at,
            'message_type', m.message_type,
            'private', m.private
        ) ORDER BY m.created_at
    ) AS message_compiled,

    -- Campos de compatibilidade
    (ARRAY_AGG(m.sender_id ORDER BY m.created_at)
     FILTER (WHERE m.sender_type = 'Contact'))[1] AS client_sender_id,

    MIN(m.inbox_id) AS inbox_id,

    (
        SELECT c.phone_number
        FROM contacts c
        WHERE c.id = (
            ARRAY_AGG(m.sender_id ORDER BY m.created_at)
            FILTER (WHERE m.sender_type = 'Contact')
        )[1]
        LIMIT 1
    ) AS client_phone,

    COUNT(*) AS t_messages,
    COUNT(*) FILTER (WHERE m.private = false) AS total_messages_public,
    COUNT(*) FILTER (WHERE m.private = true) AS total_messages_private,
    MIN(m.created_at) AS first_message_at,
    MAX(m.created_at) AS last_message_at

FROM messages m
GROUP BY m.conversation_id;

COMMENT ON VIEW vw_messages_compiled_complete IS 'Mensagens compiladas em JSON por conversa';
GRANT SELECT ON vw_messages_compiled_complete TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 3/6: vw_csat_base
-- ============================================================================

CREATE OR REPLACE VIEW vw_csat_base AS

SELECT
    csat.id AS csat_response_id,
    csat.conversation_id,
    csat.rating AS csat_rating,
    csat.feedback_message AS csat_feedback,
    csat.created_at AS csat_created_at,

    -- Classificação NPS
    CASE
        WHEN csat.rating >= 5 THEN 'Promotor'
        WHEN csat.rating >= 4 THEN 'Neutro'
        WHEN csat.rating >= 1 THEN 'Detrator'
        ELSE 'Sem Rating'
    END AS csat_nps_category,

    -- Classificação qualitativa
    CASE
        WHEN csat.rating >= 4 THEN 'Positivo'
        WHEN csat.rating = 3 THEN 'Neutro'
        WHEN csat.rating <= 2 THEN 'Negativo'
        ELSE NULL
    END AS csat_sentiment_category,

    -- Flags
    (csat.feedback_message IS NOT NULL AND csat.feedback_message != '') AS has_written_feedback,
    (LENGTH(csat.feedback_message) > 50) AS has_detailed_feedback

FROM csat_survey_responses csat;

COMMENT ON VIEW vw_csat_base IS 'Dados de satisfação do cliente (CSAT)';
GRANT SELECT ON vw_csat_base TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 4/6: vw_conversation_metrics_complete
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversation_metrics_complete AS

SELECT
    c.id AS conversation_id,

    -- Métricas de tempo
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at))::INTEGER
        ELSE NULL
    END AS first_response_time_seconds,

    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN ROUND(EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) / 60.0, 1)
        ELSE NULL
    END AS first_response_time_minutes,

    CASE
        WHEN c.status IN (1, 4) AND c.updated_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.updated_at - c.created_at))::INTEGER
        ELSE NULL
    END AS resolution_time_seconds,

    CASE
        WHEN c.waiting_since IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - c.waiting_since))::INTEGER
        ELSE NULL
    END AS waiting_time_seconds,

    -- Flags de status
    (c.assignee_id IS NOT NULL) AS is_assigned,
    (c.team_id IS NOT NULL) AS has_team,
    (c.status IN (1, 4)) AS is_resolved,
    (c.status IN (0, 2)) AS is_open,
    (c.status = 2) AS is_pending,
    (c.snoozed_until IS NOT NULL AND c.snoozed_until > NOW()) AS is_snoozed,
    (c.contact_id IS NOT NULL) AS has_contact,
    (c.waiting_since IS NOT NULL) AS is_waiting,

    -- Flags de prioridade
    (c.priority IS NOT NULL AND c.priority > 0) AS has_priority,
    (c.priority >= 3) AS is_high_priority,
    (c.campaign_id IS NOT NULL) AS is_from_campaign,

    -- Flags de tempo
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) < 300
        ELSE NULL
    END AS is_fast_response,

    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) > 1800
        ELSE NULL
    END AS is_slow_response,

    CASE
        WHEN c.status IN (1, 4) AND c.updated_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.updated_at - c.created_at)) < 7200
        ELSE NULL
    END AS is_fast_resolution,

    CASE
        WHEN c.waiting_since IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - c.waiting_since)) > 3600
        ELSE false
    END AS is_waiting_long,

    -- Flags de visualização
    (c.contact_last_seen_at IS NOT NULL) AS contact_has_seen,
    (c.agent_last_seen_at IS NOT NULL) AS agent_has_seen,

    -- Classificações
    COALESCE(c.priority, 0) AS priority_score,

    CASE c.priority
        WHEN 0 THEN 'None'
        WHEN 1 THEN 'Low'
        WHEN 2 THEN 'Medium'
        WHEN 3 THEN 'High'
        WHEN 4 THEN 'Urgent'
        ELSE 'None'
    END AS priority_label,

    CASE c.status
        WHEN 0 THEN 'Aberta'
        WHEN 2 THEN 'Pendente'
        WHEN 1 THEN 'Resolvida'
        WHEN 4 THEN 'Fechada'
        WHEN 3 THEN 'Adiada'
        ELSE 'Desconhecido'
    END AS status_label_pt

FROM conversations c;

COMMENT ON VIEW vw_conversation_metrics_complete IS 'Métricas calculadas e flags booleanos. Status é INTEGER: 0=open, 1=resolved, 2=pending, 3=snoozed, 4=closed';
GRANT SELECT ON vw_conversation_metrics_complete TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 5/6: vw_message_stats_complete
-- ============================================================================

CREATE OR REPLACE VIEW vw_message_stats_complete AS

SELECT
    m.conversation_id,

    -- Contadores
    COUNT(*) FILTER (WHERE m.private = false) AS total_messages_public,
    COUNT(*) FILTER (WHERE m.sender_type = 'User' AND m.private = false) AS user_messages_count,
    COUNT(*) FILTER (WHERE m.sender_type = 'Contact' AND m.private = false) AS contact_messages_count,
    COUNT(*) FILTER (WHERE m.private = true) AS private_notes_count,

    -- Primeira e última mensagem
    (ARRAY_AGG(m.content ORDER BY m.created_at)
     FILTER (WHERE m.private = false))[1] AS first_message_text,

    (ARRAY_AGG(m.content ORDER BY m.created_at DESC)
     FILTER (WHERE m.private = false))[1] AS last_message_text,

    (ARRAY_AGG(m.sender_type ORDER BY m.created_at)
     FILTER (WHERE m.private = false))[1] AS first_message_sender_type,

    (ARRAY_AGG(m.sender_type ORDER BY m.created_at DESC)
     FILTER (WHERE m.private = false))[1] AS last_message_sender_type,

    -- Timestamps
    MIN(m.created_at) FILTER (WHERE m.private = false) AS first_message_at,
    MAX(m.created_at) FILTER (WHERE m.private = false) AS last_message_at,

    -- Duração da conversa
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
        THEN ROUND(
            EXTRACT(EPOCH FROM (
                MAX(m.created_at) FILTER (WHERE m.private = false) -
                MIN(m.created_at) FILTER (WHERE m.private = false)
            )) / NULLIF((COUNT(*) FILTER (WHERE m.private = false) - 1), 0),
            1
        )
        ELSE NULL
    END AS avg_time_between_messages_seconds,

    -- Tamanho de mensagens
    ROUND(
        AVG(LENGTH(m.content))
        FILTER (WHERE m.private = false AND m.content IS NOT NULL),
        0
    )::INTEGER AS avg_message_length,

    MAX(LENGTH(m.content))
    FILTER (WHERE m.private = false AND m.content IS NOT NULL) AS max_message_length,

    -- Flags
    (COUNT(*) FILTER (WHERE m.sender_type = 'User') > 0) AS has_user_messages,
    (COUNT(*) FILTER (WHERE m.sender_type = 'Contact') > 0) AS has_contact_messages,
    (COUNT(*) FILTER (WHERE m.private = true) > 0) AS has_private_notes,
    (COUNT(*) FILTER (WHERE m.sender_type = 'Contact') > 0) AS has_contact_reply,
    (COUNT(*) FILTER (WHERE m.private = false) <= 5) AS is_short_conversation,
    (COUNT(*) FILTER (WHERE m.private = false) > 20) AS is_long_conversation,

    -- Ratios
    CASE
        WHEN COUNT(*) FILTER (WHERE m.private = false) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE m.sender_type = 'User' AND m.private = false)::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE m.private = false), 0),
            2
        )
        ELSE NULL
    END AS user_message_ratio,

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

COMMENT ON VIEW vw_message_stats_complete IS 'Estatísticas detalhadas de mensagens por conversa';
GRANT SELECT ON vw_message_stats_complete TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 6/6: vw_temporal_metrics
-- ============================================================================

CREATE OR REPLACE VIEW vw_temporal_metrics AS

SELECT
    c.id AS conversation_id,

    -- Componentes de data/hora
    c.created_at::DATE AS conversation_date,
    EXTRACT(YEAR FROM c.created_at)::INTEGER AS conversation_year,
    EXTRACT(MONTH FROM c.created_at)::INTEGER AS conversation_month,
    EXTRACT(DAY FROM c.created_at)::INTEGER AS conversation_day,
    EXTRACT(DOW FROM c.created_at)::INTEGER AS conversation_day_of_week,
    EXTRACT(HOUR FROM c.created_at)::INTEGER AS conversation_hour,
    EXTRACT(MINUTE FROM c.created_at)::INTEGER AS conversation_minute,
    EXTRACT(WEEK FROM c.created_at)::INTEGER AS conversation_week_of_year,
    EXTRACT(QUARTER FROM c.created_at)::INTEGER AS conversation_quarter,

    -- Labels
    CASE EXTRACT(DOW FROM c.created_at)::INTEGER
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terça'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sábado'
    END AS conversation_day_name,

    CASE EXTRACT(MONTH FROM c.created_at)::INTEGER
        WHEN 1 THEN 'Janeiro'
        WHEN 2 THEN 'Fevereiro'
        WHEN 3 THEN 'Março'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Maio'
        WHEN 6 THEN 'Junho'
        WHEN 7 THEN 'Julho'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro'
        WHEN 11 THEN 'Novembro'
        WHEN 12 THEN 'Dezembro'
    END AS conversation_month_name,

    -- Período do dia
    CASE
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 6 AND 11 THEN 'Manhã'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 12 AND 17 THEN 'Tarde'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 18 AND 23 THEN 'Noite'
    END AS conversation_period,

    -- Flags temporais
    (EXTRACT(DOW FROM c.created_at)::INTEGER BETWEEN 1 AND 5) AS is_weekday,
    (EXTRACT(DOW FROM c.created_at)::INTEGER IN (0, 6)) AS is_weekend,
    (
        EXTRACT(DOW FROM c.created_at)::INTEGER BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM c.created_at) BETWEEN 9 AND 17
    ) AS is_business_hours,
    (
        EXTRACT(HOUR FROM c.created_at) >= 20
        OR EXTRACT(HOUR FROM c.created_at) < 6
    ) AS is_night_time,

    -- Datas relativas
    (CURRENT_DATE - c.created_at::DATE)::INTEGER AS days_since_creation,
    (c.created_at::DATE = CURRENT_DATE) AS is_today,
    (c.created_at::DATE = CURRENT_DATE - 1) AS is_yesterday,
    (c.created_at >= DATE_TRUNC('week', CURRENT_DATE)) AS is_this_week,
    (c.created_at >= DATE_TRUNC('month', CURRENT_DATE)) AS is_this_month,
    (EXTRACT(YEAR FROM c.created_at) = EXTRACT(YEAR FROM CURRENT_DATE)) AS is_this_year,

    -- Formatações
    TO_CHAR(c.created_at, 'YYYY-MM-DD') AS conversation_date_formatted,
    TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') AS conversation_datetime_formatted,
    TO_CHAR(c.created_at, 'YYYY-MM') AS conversation_year_month,
    TO_CHAR(c.created_at, 'IYYY-IW') AS conversation_year_week

FROM conversations c;

COMMENT ON VIEW vw_temporal_metrics IS 'Métricas temporais para análise de sazonalidade';
GRANT SELECT ON vw_temporal_metrics TO hetzner_dev_isaac_read;


-- ============================================================================
-- VIEW 7/7: vw_conversations_analytics_final
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversations_analytics_final AS

SELECT
    cb.*,

    -- Mensagens
    mc.message_compiled,
    mc.client_sender_id,
    mc.client_phone,
    mc.t_messages,
    mc.total_messages_public,
    mc.total_messages_private,
    mc.first_message_at AS mc_first_message_at,
    mc.last_message_at AS mc_last_message_at,

    -- CSAT
    csat.csat_response_id,
    csat.csat_rating,
    csat.csat_feedback,
    csat.csat_created_at,
    csat.csat_nps_category,
    csat.csat_sentiment_category,
    csat.has_written_feedback,
    csat.has_detailed_feedback,
    (csat.csat_response_id IS NOT NULL) AS has_csat,

    -- Métricas
    cm.first_response_time_seconds,
    cm.first_response_time_minutes,
    cm.resolution_time_seconds,
    cm.waiting_time_seconds,
    cm.is_assigned,
    cm.has_team,
    cm.is_resolved,
    cm.is_open,
    cm.is_pending,
    cm.is_snoozed,
    cm.has_contact,
    cm.is_waiting,
    cm.has_priority,
    cm.is_high_priority,
    cm.is_from_campaign,
    cm.is_fast_response,
    cm.is_slow_response,
    cm.is_fast_resolution,
    cm.is_waiting_long,
    cm.contact_has_seen,
    cm.agent_has_seen,
    cm.priority_score,
    cm.priority_label,
    cm.status_label_pt,

    -- Stats de mensagens
    ms.user_messages_count,
    ms.contact_messages_count,
    ms.private_notes_count,
    ms.first_message_text,
    ms.last_message_text,
    ms.first_message_sender_type,
    ms.last_message_sender_type,
    ms.conversation_duration_seconds,
    ms.avg_time_between_messages_seconds,
    ms.avg_message_length,
    ms.max_message_length,
    ms.has_user_messages,
    ms.has_contact_messages,
    ms.has_private_notes,
    ms.has_contact_reply,
    ms.is_short_conversation,
    ms.is_long_conversation,
    ms.user_message_ratio,
    ms.contact_message_ratio,

    -- Análise IA/Bot
    (ms.user_messages_count > 0) AS has_human_intervention,
    (cm.is_resolved = true AND ms.user_messages_count = 0) AS is_bot_resolved,

    -- Temporal
    tm.conversation_date,
    tm.conversation_year,
    tm.conversation_month,
    tm.conversation_day,
    tm.conversation_day_of_week,
    tm.conversation_hour,
    tm.conversation_minute,
    tm.conversation_week_of_year,
    tm.conversation_quarter,
    tm.conversation_day_name,
    tm.conversation_month_name,
    tm.conversation_period,
    tm.is_weekday,
    tm.is_weekend,
    tm.is_business_hours,
    tm.is_night_time,
    tm.days_since_creation,
    tm.is_today,
    tm.is_yesterday,
    tm.is_this_week,
    tm.is_this_month,
    tm.is_this_year,
    tm.conversation_date_formatted,
    tm.conversation_datetime_formatted,
    tm.conversation_year_month,
    tm.conversation_year_week

FROM vw_conversations_base_complete cb
LEFT JOIN vw_messages_compiled_complete mc ON mc.conversation_id = cb.conversation_id
LEFT JOIN vw_csat_base csat ON csat.conversation_id = cb.conversation_id
LEFT JOIN vw_conversation_metrics_complete cm ON cm.conversation_id = cb.conversation_id
LEFT JOIN vw_message_stats_complete ms ON ms.conversation_id = cb.conversation_id
LEFT JOIN vw_temporal_metrics tm ON tm.conversation_id = cb.conversation_id

ORDER BY cb.conversation_created_at DESC;

COMMENT ON VIEW vw_conversations_analytics_final IS 'View FINAL completa para análise de conversas. Junta todas as 6 views modulares. Use com filtros e limite.';
GRANT SELECT ON vw_conversations_analytics_final TO hetzner_dev_isaac_read;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
