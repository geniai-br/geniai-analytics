-- ============================================================================
-- VIEW: vw_conversas_analytics_completa
-- Descrição: View enriquecida para análise completa de conversas do Chatwoot
-- Versão: 2.0 - Enhanced
-- Data: 2025-10-17
-- Baseado em: vw_conversas_por_lead (view atual)
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversas_analytics_completa AS

SELECT
    -- ========================================
    -- CAMPOS DA VIEW ORIGINAL (mantidos para compatibilidade)
    -- ========================================
    m.conversation_id,

    -- message_compiled: JSON agregado de todas as mensagens
    jsonb_agg(
        jsonb_build_object(
            'message_id', m.id,
            'sender', m.sender_type,
            'sender_id', m.sender_id,
            'text', m.content,
            'sent_at', m.created_at,
            'message_type', m.message_type,
            'content_type', m.content_type,
            'status', m.status,
            'private', m.private,
            'sentiment', m.sentiment
        ) ORDER BY m.created_at
    ) AS message_compiled,

    -- client_sender_id: ID do primeiro contato que enviou mensagem
    (ARRAY_AGG(m.sender_id ORDER BY m.created_at) FILTER (WHERE m.sender_type = 'Contact'))[1] AS client_sender_id,

    -- inbox_id: ID do canal
    MIN(m.inbox_id) AS inbox_id,

    -- client_phone: Telefone do cliente
    (
        SELECT c.phone_number
        FROM contacts c
        WHERE c.id = (ARRAY_AGG(m.sender_id ORDER BY m.created_at) FILTER (WHERE m.sender_type = 'Contact'))[1]
        LIMIT 1
    ) AS client_phone,

    -- t_messages: Total de mensagens
    COUNT(*) AS t_messages,

    -- ========================================
    -- NOVOS CAMPOS - INFORMAÇÕES DA CONVERSA
    -- ========================================

    -- IDs e identificadores
    c.id AS conversation_id_full,
    c.display_id,
    c.uuid AS conversation_uuid,
    c.account_id,
    c.contact_id,

    -- Status e classificação
    c.status,
    c.priority,
    c.snoozed_until,

    -- Atribuição
    c.assignee_id,
    c.team_id,
    c.campaign_id,

    -- Datas principais
    c.created_at AS conversation_created_at,
    c.updated_at AS conversation_updated_at,
    c.last_activity_at,
    c.first_reply_created_at,
    c.waiting_since,

    -- Visualizações
    c.contact_last_seen_at,
    c.agent_last_seen_at,
    c.assignee_last_seen_at,

    -- Labels e atributos
    c.cached_label_list,
    c.additional_attributes AS conversation_attributes,
    c.custom_attributes AS conversation_custom_attrs,

    -- ========================================
    -- INFORMAÇÕES DO CONTATO/CLIENTE
    -- ========================================
    cont.name AS contact_name,
    cont.email AS contact_email,
    cont.identifier AS contact_identifier,
    cont.contact_type,
    cont.location AS contact_location,
    cont.country_code AS contact_country,
    cont.created_at AS contact_created_at,
    cont.last_activity_at AS contact_last_activity_at,
    cont.blocked AS contact_blocked,

    -- ========================================
    -- INFORMAÇÕES DO CANAL (INBOX)
    -- ========================================
    i.name AS inbox_name,
    i.channel_type AS inbox_channel_type,
    i.business_name AS inbox_business_name,
    i.timezone AS inbox_timezone,
    i.enable_auto_assignment AS inbox_auto_assign,
    i.csat_survey_enabled AS inbox_csat_enabled,

    -- ========================================
    -- INFORMAÇÕES DO AGENTE
    -- ========================================
    u.name AS assignee_name,
    u.display_name AS assignee_display_name,
    u.email AS assignee_email,
    u.availability AS assignee_availability,

    -- ========================================
    -- INFORMAÇÕES DO TIME
    -- ========================================
    t.name AS team_name,
    t.description AS team_description,

    -- ========================================
    -- SATISFAÇÃO DO CLIENTE (CSAT)
    -- ========================================
    csat.rating AS csat_rating,
    csat.feedback_message AS csat_feedback,
    csat.created_at AS csat_created_at,

    -- ========================================
    -- CONTADORES DE MENSAGENS DETALHADOS
    -- ========================================

    -- Total de mensagens do agente/usuário
    COUNT(*) FILTER (WHERE m.sender_type = 'User' AND m.private = false) AS user_messages_count,

    -- Total de mensagens do contato
    COUNT(*) FILTER (WHERE m.sender_type = 'Contact') AS contact_messages_count,

    -- Total de notas privadas/internas
    COUNT(*) FILTER (WHERE m.private = true) AS private_notes_count,

    -- Total de mensagens do sistema
    COUNT(*) FILTER (WHERE m.sender_type IS NULL OR m.sender_type NOT IN ('User', 'Contact')) AS system_messages_count,

    -- ========================================
    -- PRIMEIRA E ÚLTIMA MENSAGEM
    -- ========================================

    -- Primeira mensagem (texto)
    (ARRAY_AGG(m.content ORDER BY m.created_at) FILTER (WHERE m.private = false))[1] AS first_message_text,

    -- Última mensagem (texto)
    (ARRAY_AGG(m.content ORDER BY m.created_at DESC) FILTER (WHERE m.private = false))[1] AS last_message_text,

    -- Data da primeira mensagem
    MIN(m.created_at) AS first_message_at,

    -- Data da última mensagem
    MAX(m.created_at) AS last_message_at,

    -- Tipo do sender da primeira mensagem
    (ARRAY_AGG(m.sender_type ORDER BY m.created_at) FILTER (WHERE m.private = false))[1] AS first_message_sender_type,

    -- Tipo do sender da última mensagem
    (ARRAY_AGG(m.sender_type ORDER BY m.created_at DESC) FILTER (WHERE m.private = false))[1] AS last_message_sender_type,

    -- ========================================
    -- MÉTRICAS DE TEMPO CALCULADAS
    -- ========================================

    -- Tempo até primeira resposta (segundos)
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at))
        ELSE NULL
    END AS first_response_time_seconds,

    -- Duração total da conversa (segundos)
    CASE
        WHEN MAX(m.created_at) IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (MAX(m.created_at) - c.created_at))
        ELSE NULL
    END AS conversation_duration_seconds,

    -- Tempo médio entre mensagens (segundos)
    CASE
        WHEN COUNT(*) > 1 AND MAX(m.created_at) IS NOT NULL AND MIN(m.created_at) IS NOT NULL
        THEN EXTRACT(EPOCH FROM (MAX(m.created_at) - MIN(m.created_at))) / NULLIF((COUNT(*) - 1), 0)
        ELSE NULL
    END AS avg_time_between_messages_seconds,

    -- ========================================
    -- FLAGS E INDICADORES BOOLEANOS
    -- ========================================

    -- Foi atribuída a um agente?
    (c.assignee_id IS NOT NULL) AS is_assigned,

    -- Foi atribuída a um time?
    (c.team_id IS NOT NULL) AS has_team,

    -- Está resolvida?
    (c.status IN ('resolved', 'closed')) AS is_resolved,

    -- Está aberta?
    (c.status IN ('open', 'pending')) AS is_open,

    -- Está adiada (snoozed)?
    (c.snoozed_until IS NOT NULL AND c.snoozed_until > NOW()) AS is_snoozed,

    -- Tem avaliação CSAT?
    (csat.id IS NOT NULL) AS has_csat,

    -- Teve intervenção humana?
    (COUNT(*) FILTER (WHERE m.sender_type = 'User') > 0) AS has_human_intervention,

    -- Foi resolvida apenas por bot? (sem mensagens de User)
    (
        c.status IN ('resolved', 'closed')
        AND COUNT(*) FILTER (WHERE m.sender_type = 'User') = 0
    ) AS is_bot_resolved,

    -- Cliente respondeu?
    (COUNT(*) FILTER (WHERE m.sender_type = 'Contact') > 0) AS has_contact_reply,

    -- Tem contato identificado?
    (c.contact_id IS NOT NULL) AS has_contact,

    -- ========================================
    -- ANÁLISE DE SENTIMENT (se disponível)
    -- ========================================

    -- Média de sentiment das mensagens
    AVG(
        CASE
            WHEN m.sentiment IS NOT NULL
            THEN m.sentiment::numeric
            ELSE NULL
        END
    ) AS avg_sentiment_score,

    -- ========================================
    -- INFORMAÇÕES DA CONTA
    -- ========================================
    acc.name AS account_name,
    acc.locale AS account_locale,

    -- ========================================
    -- METADADOS TEMPORAIS ÚTEIS PARA ANÁLISE
    -- ========================================
    c.created_at::date AS conversation_date,
    EXTRACT(YEAR FROM c.created_at)::integer AS conversation_year,
    EXTRACT(MONTH FROM c.created_at)::integer AS conversation_month,
    EXTRACT(DAY FROM c.created_at)::integer AS conversation_day,
    EXTRACT(DOW FROM c.created_at)::integer AS conversation_day_of_week,  -- 0=domingo
    EXTRACT(HOUR FROM c.created_at)::integer AS conversation_hour,

    -- Nome do dia da semana
    CASE EXTRACT(DOW FROM c.created_at)::integer
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terça'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sábado'
    END AS conversation_day_name,

    -- Período do dia
    CASE
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 6 AND 11 THEN 'Manhã'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 12 AND 17 THEN 'Tarde'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 18 AND 23 THEN 'Noite'
    END AS conversation_period,

    -- É dia útil? (segunda a sexta)
    (EXTRACT(DOW FROM c.created_at)::integer BETWEEN 1 AND 5) AS is_weekday,

    -- É horário comercial? (9h-18h em dia útil)
    (
        EXTRACT(DOW FROM c.created_at)::integer BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM c.created_at) BETWEEN 9 AND 17
    ) AS is_business_hours

FROM messages m

-- JOIN com conversations
INNER JOIN conversations c ON c.id = m.conversation_id

-- JOINs opcionais (LEFT JOIN)
LEFT JOIN contacts cont ON cont.id = c.contact_id
LEFT JOIN inboxes i ON i.id = m.inbox_id
LEFT JOIN users u ON u.id = c.assignee_id
LEFT JOIN teams t ON t.id = c.team_id
LEFT JOIN csat_survey_responses csat ON csat.conversation_id = c.id
LEFT JOIN accounts acc ON acc.id = c.account_id

-- Agrupar por conversa e incluir campos da tabela conversations
GROUP BY
    m.conversation_id,
    c.id,
    c.display_id,
    c.uuid,
    c.account_id,
    c.contact_id,
    c.status,
    c.priority,
    c.snoozed_until,
    c.assignee_id,
    c.team_id,
    c.campaign_id,
    c.created_at,
    c.updated_at,
    c.last_activity_at,
    c.first_reply_created_at,
    c.waiting_since,
    c.contact_last_seen_at,
    c.agent_last_seen_at,
    c.assignee_last_seen_at,
    c.cached_label_list,
    c.additional_attributes,
    c.custom_attributes,
    cont.name,
    cont.email,
    cont.identifier,
    cont.contact_type,
    cont.location,
    cont.country_code,
    cont.created_at,
    cont.last_activity_at,
    cont.blocked,
    i.name,
    i.channel_type,
    i.business_name,
    i.timezone,
    i.enable_auto_assignment,
    i.csat_survey_enabled,
    u.name,
    u.display_name,
    u.email,
    u.availability,
    t.name,
    t.description,
    csat.id,
    csat.rating,
    csat.feedback_message,
    csat.created_at,
    acc.name,
    acc.locale

-- Ordenar por data de criação (mais recentes primeiro)
ORDER BY c.created_at DESC;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_conversas_analytics_completa IS
'View completa para análise de conversas do Chatwoot.
Inclui:
- Todas as mensagens compiladas em JSON
- Métricas de tempo (duração, tempo de resposta)
- Contadores detalhados de mensagens
- Informações de contato, agente, time, canal
- Satisfação do cliente (CSAT)
- Flags booleanos para análise
- Metadados temporais para segmentação
Versão: 2.0';

-- Grant de acesso para usuário read-only
GRANT SELECT ON vw_conversas_analytics_completa TO hetzner_dev_isaac_read;

-- ============================================================================
-- FIM
-- ============================================================================
