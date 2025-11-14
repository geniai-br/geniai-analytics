-- ============================================================================
-- SCRIPT: 08_migrate_data.sql
-- Descrição: Migra dados do banco allpfit para geniai_analytics
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -h localhost -p 5432 -U integracao_user -d geniai_analytics -f sql/multi_tenant/08_migrate_data.sql

\c geniai_analytics

\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║         MIGRAÇÃO DE DADOS: allpfit → geniai_analytics         ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- PRÉ-REQUISITOS
-- ============================================================================

\echo '🔍 Verificando pré-requisitos...'

-- Verificar se tenant AllpFit existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1) THEN
        RAISE EXCEPTION 'Tenant AllpFit (ID=1) não encontrado! Execute 03_seed_data.sql primeiro.';
    ELSE
        RAISE NOTICE '✅ Tenant AllpFit encontrado (ID=1)';
    END IF;
END $$;

-- Verificar se tabelas de destino existem
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations_analytics') THEN
        RAISE EXCEPTION 'Tabela conversations_analytics não encontrada! Execute 07_create_analytics_tables.sql primeiro.';
    ELSE
        RAISE NOTICE '✅ Tabela conversations_analytics existe';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations_analytics_ai') THEN
        RAISE EXCEPTION 'Tabela conversations_analytics_ai não encontrada! Execute 07_create_analytics_tables.sql primeiro.';
    ELSE
        RAISE NOTICE '✅ Tabela conversations_analytics_ai existe';
    END IF;
END $$;

\echo '✅ Pré-requisitos verificados!'
\echo ''

-- ============================================================================
-- 1. MIGRAR conversations_analytics
-- ============================================================================

\echo '📊 Migrando conversas do banco allpfit...'
\echo ''

-- Contar registros no banco de origem
DO $$
DECLARE
    origem_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO origem_count
    FROM dblink(
        'host=localhost dbname=allpfit user=integracao_user password=vlVMVM6UNz2yYSBlzodPjQvZh',
        'SELECT COUNT(*)::INTEGER FROM conversas_analytics'
    ) AS t(count INTEGER);

    RAISE NOTICE '📈 Registros no allpfit.conversas_analytics: %', origem_count;
END $$;

-- Migrar dados
INSERT INTO conversations_analytics (
    tenant_id,
    conversation_id,
    etl_inserted_at,
    etl_updated_at,
    display_id,
    conversation_uuid,
    account_id,
    status,
    status_label_pt,
    priority,
    priority_label,
    priority_score,
    snoozed_until,
    assignee_id,
    assignee_name,
    assignee_email,
    team_id,
    team_name,
    campaign_id,
    contact_id,
    contact_name,
    contact_email,
    contact_phone,
    contact_identifier,
    inbox_id,
    inbox_name,
    inbox_channel_type,
    inbox_timezone,
    account_name,
    conversation_created_at,
    conversation_updated_at,
    last_activity_at,
    first_reply_created_at,
    waiting_since,
    contact_last_seen_at,
    agent_last_seen_at,
    message_compiled,
    client_sender_id,
    client_phone,
    t_messages,
    total_messages_public,
    total_messages_private,
    mc_first_message_at,
    mc_last_message_at,
    csat_response_id,
    csat_rating,
    csat_feedback,
    csat_created_at,
    csat_nps_category,
    csat_sentiment_category,
    has_written_feedback,
    has_detailed_feedback,
    has_csat,
    first_response_time_seconds,
    first_response_time_minutes,
    resolution_time_seconds,
    waiting_time_seconds,
    conversation_duration_seconds,
    avg_time_between_messages_seconds,
    is_assigned,
    has_team,
    is_resolved,
    is_open,
    is_pending,
    is_snoozed,
    has_contact,
    is_waiting,
    has_priority,
    is_high_priority,
    is_from_campaign,
    is_fast_response,
    is_slow_response,
    is_fast_resolution,
    is_waiting_long,
    contact_has_seen,
    agent_has_seen,
    user_messages_count,
    contact_messages_count,
    private_notes_count,
    first_message_text,
    last_message_text,
    first_message_sender_type,
    last_message_sender_type,
    avg_message_length,
    max_message_length,
    has_user_messages,
    has_contact_messages,
    has_private_notes,
    has_contact_reply,
    is_short_conversation,
    is_long_conversation,
    user_message_ratio,
    contact_message_ratio,
    has_human_intervention,
    is_bot_resolved,
    conversation_date,
    conversation_year,
    conversation_month,
    conversation_day,
    conversation_day_of_week,
    conversation_hour,
    conversation_minute,
    conversation_week_of_year,
    conversation_quarter,
    conversation_day_name,
    conversation_month_name,
    conversation_period,
    is_weekday,
    is_weekend,
    is_business_hours,
    is_night_time,
    days_since_creation,
    is_today,
    is_yesterday,
    is_this_week,
    is_this_month,
    is_this_year,
    conversation_date_formatted,
    conversation_datetime_formatted,
    conversation_year_month,
    conversation_year_week
)
SELECT
    1 AS tenant_id,  -- AllpFit = tenant_id 1
    conversation_id,
    etl_inserted_at,
    etl_updated_at,
    display_id,
    conversation_uuid,
    account_id,
    status,
    status_label_pt,
    priority,
    priority_label,
    priority_score,
    snoozed_until,
    assignee_id,
    assignee_name,
    assignee_email,
    team_id,
    team_name,
    campaign_id,
    contact_id,
    contact_name,
    contact_email,
    contact_phone,
    contact_identifier,
    inbox_id,
    inbox_name,
    inbox_channel_type,
    inbox_timezone,
    account_name,
    conversation_created_at,
    conversation_updated_at,
    last_activity_at,
    first_reply_created_at,
    waiting_since,
    contact_last_seen_at,
    agent_last_seen_at,
    message_compiled,
    client_sender_id,
    client_phone,
    t_messages,
    total_messages_public,
    total_messages_private,
    mc_first_message_at,
    mc_last_message_at,
    csat_response_id,
    csat_rating,
    csat_feedback,
    csat_created_at,
    csat_nps_category,
    csat_sentiment_category,
    has_written_feedback,
    has_detailed_feedback,
    has_csat,
    first_response_time_seconds,
    first_response_time_minutes,
    resolution_time_seconds,
    waiting_time_seconds,
    conversation_duration_seconds,
    avg_time_between_messages_seconds,
    is_assigned,
    has_team,
    is_resolved,
    is_open,
    is_pending,
    is_snoozed,
    has_contact,
    is_waiting,
    has_priority,
    is_high_priority,
    is_from_campaign,
    is_fast_response,
    is_slow_response,
    is_fast_resolution,
    is_waiting_long,
    contact_has_seen,
    agent_has_seen,
    user_messages_count,
    contact_messages_count,
    private_notes_count,
    first_message_text,
    last_message_text,
    first_message_sender_type,
    last_message_sender_type,
    avg_message_length,
    max_message_length,
    has_user_messages,
    has_contact_messages,
    has_private_notes,
    has_contact_reply,
    is_short_conversation,
    is_long_conversation,
    user_message_ratio,
    contact_message_ratio,
    has_human_intervention,
    is_bot_resolved,
    conversation_date,
    conversation_year,
    conversation_month,
    conversation_day,
    conversation_day_of_week,
    conversation_hour,
    conversation_minute,
    conversation_week_of_year,
    conversation_quarter,
    conversation_day_name,
    conversation_month_name,
    conversation_period,
    is_weekday,
    is_weekend,
    is_business_hours,
    is_night_time,
    days_since_creation,
    is_today,
    is_yesterday,
    is_this_week,
    is_this_month,
    is_this_year,
    conversation_date_formatted,
    conversation_datetime_formatted,
    conversation_year_month,
    conversation_year_week
FROM dblink(
    'host=localhost dbname=allpfit user=integracao_user password=vlVMVM6UNz2yYSBlzodPjQvZh',
    'SELECT * FROM conversas_analytics ORDER BY conversation_id'
) AS origem (
    id INTEGER,
    conversation_id INTEGER,
    etl_inserted_at TIMESTAMP,
    etl_updated_at TIMESTAMP,
    display_id INTEGER,
    conversation_uuid UUID,
    account_id INTEGER,
    status INTEGER,
    status_label_pt VARCHAR(50),
    priority INTEGER,
    priority_label VARCHAR(20),
    priority_score INTEGER,
    snoozed_until TIMESTAMP,
    assignee_id INTEGER,
    assignee_name VARCHAR(255),
    assignee_email VARCHAR(255),
    team_id INTEGER,
    team_name VARCHAR(255),
    campaign_id INTEGER,
    contact_id INTEGER,
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_identifier VARCHAR(255),
    inbox_id INTEGER,
    inbox_name VARCHAR(255),
    inbox_channel_type VARCHAR(50),
    inbox_timezone VARCHAR(50),
    account_name VARCHAR(255),
    conversation_created_at TIMESTAMP,
    conversation_updated_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    first_reply_created_at TIMESTAMP,
    waiting_since TIMESTAMP,
    contact_last_seen_at TIMESTAMP,
    agent_last_seen_at TIMESTAMP,
    message_compiled JSONB,
    client_sender_id INTEGER,
    client_phone VARCHAR(50),
    t_messages INTEGER,
    total_messages_public INTEGER,
    total_messages_private INTEGER,
    mc_first_message_at TIMESTAMP,
    mc_last_message_at TIMESTAMP,
    csat_response_id INTEGER,
    csat_rating INTEGER,
    csat_feedback TEXT,
    csat_created_at TIMESTAMP,
    csat_nps_category VARCHAR(50),
    csat_sentiment_category VARCHAR(50),
    has_written_feedback BOOLEAN,
    has_detailed_feedback BOOLEAN,
    has_csat BOOLEAN,
    first_response_time_seconds INTEGER,
    first_response_time_minutes NUMERIC(10,1),
    resolution_time_seconds INTEGER,
    waiting_time_seconds INTEGER,
    conversation_duration_seconds INTEGER,
    avg_time_between_messages_seconds NUMERIC(10,1),
    is_assigned BOOLEAN,
    has_team BOOLEAN,
    is_resolved BOOLEAN,
    is_open BOOLEAN,
    is_pending BOOLEAN,
    is_snoozed BOOLEAN,
    has_contact BOOLEAN,
    is_waiting BOOLEAN,
    has_priority BOOLEAN,
    is_high_priority BOOLEAN,
    is_from_campaign BOOLEAN,
    is_fast_response BOOLEAN,
    is_slow_response BOOLEAN,
    is_fast_resolution BOOLEAN,
    is_waiting_long BOOLEAN,
    contact_has_seen BOOLEAN,
    agent_has_seen BOOLEAN,
    user_messages_count INTEGER,
    contact_messages_count INTEGER,
    private_notes_count INTEGER,
    first_message_text TEXT,
    last_message_text TEXT,
    first_message_sender_type VARCHAR(50),
    last_message_sender_type VARCHAR(50),
    avg_message_length INTEGER,
    max_message_length INTEGER,
    has_user_messages BOOLEAN,
    has_contact_messages BOOLEAN,
    has_private_notes BOOLEAN,
    has_contact_reply BOOLEAN,
    is_short_conversation BOOLEAN,
    is_long_conversation BOOLEAN,
    user_message_ratio NUMERIC(5,2),
    contact_message_ratio NUMERIC(5,2),
    has_human_intervention BOOLEAN,
    is_bot_resolved BOOLEAN,
    conversation_date DATE,
    conversation_year INTEGER,
    conversation_month INTEGER,
    conversation_day INTEGER,
    conversation_day_of_week INTEGER,
    conversation_hour INTEGER,
    conversation_minute INTEGER,
    conversation_week_of_year INTEGER,
    conversation_quarter INTEGER,
    conversation_day_name VARCHAR(20),
    conversation_month_name VARCHAR(20),
    conversation_period VARCHAR(20),
    is_weekday BOOLEAN,
    is_weekend BOOLEAN,
    is_business_hours BOOLEAN,
    is_night_time BOOLEAN,
    days_since_creation INTEGER,
    is_today BOOLEAN,
    is_yesterday BOOLEAN,
    is_this_week BOOLEAN,
    is_this_month BOOLEAN,
    is_this_year BOOLEAN,
    conversation_date_formatted VARCHAR(20),
    conversation_datetime_formatted VARCHAR(30),
    conversation_year_month VARCHAR(10),
    conversation_year_week VARCHAR(10)
)
ON CONFLICT (tenant_id, conversation_id) DO NOTHING;

\echo '✅ Conversas migradas!'
\echo ''

-- ============================================================================
-- 2. MIGRAR conversations_analytics_ai
-- ============================================================================

\echo '🤖 Migrando análises de IA...'
\echo ''

-- Contar registros de IA
DO $$
DECLARE
    origem_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO origem_count
    FROM dblink(
        'host=localhost dbname=allpfit user=integracao_user password=vlVMVM6UNz2yYSBlzodPjQvZh',
        'SELECT COUNT(*)::INTEGER FROM conversas_analytics_ai'
    ) AS t(count INTEGER);

    RAISE NOTICE '📈 Análises de IA no allpfit: %', origem_count;
END $$;

-- Migrar análises de IA (adaptando estrutura AllpFit para estrutura genérica)
INSERT INTO conversations_analytics_ai (
    tenant_id,
    conversation_id,
    ai_analysis,
    ai_summary,
    ai_sentiment,
    ai_priority_score,
    ai_lead_quality,
    ai_next_best_action,
    ai_extracted_name,
    ai_is_lead,
    ai_confidence_score,
    ai_model_version,
    ai_analyzed_at,
    ai_updated_at
)
SELECT
    1 AS tenant_id,  -- AllpFit = tenant_id 1
    conversation_id,
    jsonb_build_object(
        'condicao_fisica', condicao_fisica,
        'objetivo', objetivo,
        'analise_completa', analise_ia,
        'sugestao_disparo', sugestao_disparo,
        'probabilidade_conversao', probabilidade_conversao,
        'visita_agendada', visita_agendada,
        'versao_prompt', versao_prompt
    ) AS ai_analysis,
    LEFT(analise_ia, 500) AS ai_summary,  -- Resumo (primeiros 500 chars)
    CASE
        WHEN probabilidade_conversao >= 4 THEN 'positive'
        WHEN probabilidade_conversao >= 2 THEN 'neutral'
        ELSE 'negative'
    END AS ai_sentiment,
    probabilidade_conversao AS ai_priority_score,
    CASE
        WHEN probabilidade_conversao = 5 THEN 'hot'
        WHEN probabilidade_conversao = 4 THEN 'warm'
        WHEN probabilidade_conversao = 3 THEN 'medium'
        ELSE 'cold'
    END AS ai_lead_quality,
    sugestao_disparo AS ai_next_best_action,
    nome_mapeado_bot AS ai_extracted_name,
    (probabilidade_conversao >= 3) AS ai_is_lead,
    (probabilidade_conversao / 5.0 * 100) AS ai_confidence_score,
    modelo_ia AS ai_model_version,
    analisado_em AS ai_analyzed_at,
    updated_at AS ai_updated_at
FROM dblink(
    'host=localhost dbname=allpfit user=integracao_user password=vlVMVM6UNz2yYSBlzodPjQvZh',
    'SELECT
        conversation_id,
        condicao_fisica,
        objetivo,
        analise_ia,
        sugestao_disparo,
        probabilidade_conversao,
        analisado_em,
        modelo_ia,
        versao_prompt,
        updated_at,
        visita_agendada,
        nome_mapeado_bot
    FROM conversas_analytics_ai
    ORDER BY conversation_id'
) AS origem (
    conversation_id INTEGER,
    condicao_fisica TEXT,
    objetivo TEXT,
    analise_ia TEXT,
    sugestao_disparo TEXT,
    probabilidade_conversao INTEGER,
    analisado_em TIMESTAMP,
    modelo_ia VARCHAR(50),
    versao_prompt INTEGER,
    updated_at TIMESTAMP,
    visita_agendada BOOLEAN,
    nome_mapeado_bot TEXT
)
ON CONFLICT (tenant_id, conversation_id) DO NOTHING;

\echo '✅ Análises de IA migradas!'
\echo ''

-- ============================================================================
-- 3. MIGRAR etl_control
-- ============================================================================

\echo '⚙️  Migrando histórico de ETL...'
\echo ''

-- Verificar se tabela existe no banco de origem
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM dblink(
            'host=localhost dbname=allpfit user=integracao_user password=vlVMVM6UNz2yYSBlzodPjQvZh',
            'SELECT 1 FROM information_schema.tables WHERE table_name = ''etl_control'''
        ) AS t(exists INT)
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE '✅ Tabela etl_control encontrada no allpfit';
    ELSE
        RAISE NOTICE '⚠️  Tabela etl_control não encontrada no allpfit (OK, será criada depois)';
    END IF;
END $$;

\echo '✅ Verificação de ETL concluída!'
\echo ''

-- ============================================================================
-- 4. ATUALIZAR tenant AllpFit com inbox_ids
-- ============================================================================

\echo '📝 Atualizando tenant AllpFit com inbox_ids...'

UPDATE tenants
SET inbox_ids = ARRAY(
    SELECT DISTINCT inbox_id
    FROM conversations_analytics
    WHERE tenant_id = 1
      AND inbox_id IS NOT NULL
    ORDER BY inbox_id
)
WHERE id = 1;

\echo '✅ Tenant atualizado!'
\echo ''

-- ============================================================================
-- 5. VERIFICAÇÃO FINAL
-- ============================================================================

\echo '═══════════════════════════════════════════════════════════════'
\echo '  VERIFICAÇÃO FINAL'
\echo '═══════════════════════════════════════════════════════════════'
\echo ''

-- Contagem de registros migrados
SELECT
    'conversations_analytics' AS tabela,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT tenant_id) AS total_tenants,
    MIN(conversation_created_at)::DATE AS primeira_conversa,
    MAX(conversation_created_at)::DATE AS ultima_conversa
FROM conversations_analytics
WHERE tenant_id = 1

UNION ALL

SELECT
    'conversations_analytics_ai' AS tabela,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT tenant_id) AS total_tenants,
    MIN(ai_analyzed_at)::DATE AS primeira_analise,
    MAX(ai_analyzed_at)::DATE AS ultima_analise
FROM conversations_analytics_ai
WHERE tenant_id = 1;

\echo ''

-- Tenant AllpFit atualizado
SELECT
    '=== TENANT ALLPFIT ===' AS section,
    id,
    name,
    slug,
    status,
    inbox_ids,
    array_length(inbox_ids, 1) AS total_inboxes
FROM tenants
WHERE id = 1;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║              ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!                ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  📊 Dados migrados do banco allpfit → geniai_analytics         ║'
\echo '║  ✅ Todas as conversas receberam tenant_id = 1 (AllpFit)       ║'
\echo '║  ✅ Análises de IA adaptadas para estrutura genérica           ║'
\echo '║  ✅ Tenant AllpFit atualizado com inbox_ids                    ║'
\echo '║                                                                ║'
\echo '║  📋 PRÓXIMO PASSO:                                             ║'
\echo '║  Executar: 09_add_rls_analytics.sql                            ║'
\echo '║  (Adicionar RLS nas tabelas de analytics)                      ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''