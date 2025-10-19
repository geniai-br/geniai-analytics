-- ============================================================================
-- VIEW FINAL: vw_conversations_analytics_final
-- Descrição: Junta TODAS as 6 views modulares em uma view completa
-- Performance: ⚡⚡ MÉDIA (JOINs de views, mas cada view já está otimizada)
-- USO: Esta é a view que o ETL e Dashboard devem consultar
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversations_analytics_final AS

SELECT
    -- ========================================
    -- TODOS OS CAMPOS DA VIEW BASE
    -- ========================================
    cb.*,

    -- ========================================
    -- CAMPOS DA VIEW DE MENSAGENS COMPILADAS
    -- ========================================
    mc.message_compiled,
    mc.client_sender_id,
    mc.client_phone,
    mc.t_messages,
    mc.total_messages_public,
    mc.total_messages_private,
    mc.first_message_at AS mc_first_message_at,
    mc.last_message_at AS mc_last_message_at,

    -- ========================================
    -- CAMPOS DA VIEW DE CSAT
    -- ========================================
    csat.csat_response_id,
    csat.csat_rating,
    csat.csat_feedback,
    csat.csat_created_at,
    csat.csat_nps_category,
    csat.csat_sentiment_category,
    csat.has_written_feedback,
    csat.has_detailed_feedback,

    -- Flag: Tem CSAT?
    (csat.csat_response_id IS NOT NULL) AS has_csat,

    -- ========================================
    -- CAMPOS DA VIEW DE MÉTRICAS
    -- ========================================
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

    -- ========================================
    -- CAMPOS DA VIEW DE STATS DE MENSAGENS
    -- ========================================
    ms.user_messages_count,
    ms.contact_messages_count,
    ms.system_messages_count,
    ms.private_notes_count,
    ms.first_message_text,
    ms.last_message_text,
    ms.first_message_sender_type,
    ms.last_message_sender_type,
    ms.conversation_duration_seconds,
    ms.avg_time_between_messages_seconds,
    ms.avg_sentiment_score,
    ms.messages_with_sentiment_count,
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

    -- ========================================
    -- CAMPOS ADICIONAIS DE ANÁLISE DE IA/BOT
    -- ========================================

    -- Teve intervenção humana?
    (ms.user_messages_count > 0) AS has_human_intervention,

    -- Foi resolvida apenas por bot?
    (
        cm.is_resolved = true
        AND ms.user_messages_count = 0
    ) AS is_bot_resolved,

    -- ========================================
    -- CAMPOS DA VIEW TEMPORAL
    -- ========================================
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
    tm.conversation_day_abbr,
    tm.conversation_month_name,
    tm.conversation_month_abbr,
    tm.conversation_period,
    tm.conversation_period_detailed,
    tm.is_weekday,
    tm.is_weekend,
    tm.is_business_hours,
    tm.is_extended_hours,
    tm.is_night_time,
    tm.is_lunch_time,
    tm.is_start_of_month,
    tm.is_end_of_month,
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

-- JOINs com as views modulares
LEFT JOIN vw_messages_compiled_complete mc ON mc.conversation_id = cb.conversation_id
LEFT JOIN vw_csat_base csat ON csat.conversation_id = cb.conversation_id
LEFT JOIN vw_conversation_metrics_complete cm ON cm.conversation_id = cb.conversation_id
LEFT JOIN vw_message_stats_complete ms ON ms.conversation_id = cb.conversation_id
LEFT JOIN vw_temporal_metrics tm ON tm.conversation_id = cb.conversation_id

-- Ordenar por data de criação (mais recentes primeiro)
ORDER BY cb.conversation_created_at DESC;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_conversations_analytics_final IS
'View FINAL completa para análise de conversas.
Junta TODAS as 6 views modulares:
  1. vw_conversations_base_complete (dados base)
  2. vw_messages_compiled_complete (mensagens JSON)
  3. vw_csat_base (satisfação)
  4. vw_conversation_metrics_complete (métricas e flags)
  5. vw_message_stats_complete (estatísticas de mensagens)
  6. vw_temporal_metrics (análise temporal)

Total: 150+ campos para análise completa.
Performance: Média, use com filtros e limite.
Recomendação: ETL deve extrair para banco local.';

GRANT SELECT ON vw_conversations_analytics_final TO hetzner_dev_isaac_read;
