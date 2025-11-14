-- ============================================================================
-- SCRIPT: 04_migrate_allpfit_data.sql
-- Descrição: Migra dados do banco allpfit para geniai_analytics
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- IMPORTANTE: Este script usa dblink para copiar dados entre bancos
-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/04_migrate_allpfit_data.sql

\c geniai_analytics

-- ============================================================================
-- PRÉ-REQUISITOS
-- ============================================================================

-- 1. Extensão dblink deve estar instalada
CREATE EXTENSION IF NOT EXISTS dblink;

-- 2. Banco de origem (allpfit) deve existir e estar acessível
-- 3. Tenant AllpFit (ID=1) deve já existir na tabela tenants
-- 4. Fazer BACKUP do banco allpfit antes de migrar!

SELECT 'Iniciando migração de dados...' AS status;

-- ============================================================================
-- VERIFICAÇÕES PRÉ-MIGRAÇÃO
-- ============================================================================

-- Verificar se tenant AllpFit existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tenants WHERE id = 1) THEN
        RAISE EXCEPTION 'Tenant AllpFit (ID=1) não encontrado! Execute 03_seed_data.sql primeiro.';
    END IF;
END $$;

-- Verificar se banco allpfit existe
DO $$
DECLARE
    db_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM dblink('dbname=postgres', 'SELECT 1 FROM pg_database WHERE datname = ''allpfit''') AS t(exists INT)
    ) INTO db_exists;

    IF NOT db_exists THEN
        RAISE NOTICE 'AVISO: Banco allpfit não encontrado. Migração será pulada.';
        RAISE NOTICE 'Se você tem dados para migrar, certifique-se que o banco allpfit está acessível.';
    END IF;
END $$;

-- ============================================================================
-- 1. MIGRAÇÃO: conversations_analytics
-- ============================================================================

\echo '=== MIGRANDO conversations_analytics ==='

-- Verificar quantos registros existem no banco de origem
DO $$
DECLARE
    origem_count INTEGER;
BEGIN
    SELECT count
    INTO origem_count
    FROM dblink(
        'dbname=allpfit user=' || current_user,
        'SELECT COUNT(*)::INTEGER FROM conversas_analytics'
    ) AS t(count INTEGER);

    RAISE NOTICE 'Registros no banco allpfit: %', COALESCE(origem_count, 0);

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Não foi possível conectar ao banco allpfit';
        RAISE NOTICE 'Detalhes: %', SQLERRM;
END $$;

-- Migrar dados (comentado por segurança - descomentar após ajustar)
-- DESCOMENTAR APÓS CONFIRMAR QUE TUDO ESTÁ CORRETO:

/*
INSERT INTO conversations_analytics
SELECT
    -- Manter campos existentes
    id,
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
    conversation_year_week,
    -- NOVOS CAMPOS multi-tenant
    1 AS tenant_id,  -- AllpFit = tenant_id 1
    inbox_id         -- Já existe, apenas replicar
FROM dblink(
    'dbname=allpfit user=' || current_user,
    'SELECT * FROM conversas_analytics'
) AS t(
    -- Listar TODAS as colunas da tabela conversas_analytics
    -- (mesma ordem do SELECT acima)
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
ON CONFLICT (conversation_id) DO NOTHING;  -- Evitar duplicatas
*/

-- ============================================================================
-- 2. MIGRAÇÃO: conversas_analytics_ai
-- ============================================================================

\echo '=== MIGRANDO conversas_analytics_ai ==='

/*
INSERT INTO conversas_analytics_ai
SELECT
    id,
    conversation_id,
    condicao_fisica,
    objetivo,
    analise_ia,
    sugestao_disparo,
    probabilidade_conversao,
    data_atualizacao_telefone,
    analisado_em,
    modelo_ia,
    versao_prompt,
    created_at,
    updated_at,
    1 AS tenant_id  -- AllpFit
FROM dblink(
    'dbname=allpfit user=' || current_user,
    'SELECT * FROM conversas_analytics_ai'
) AS t(
    id INTEGER,
    conversation_id INTEGER,
    condicao_fisica TEXT,
    objetivo TEXT,
    analise_ia TEXT,
    sugestao_disparo TEXT,
    probabilidade_conversao INTEGER,
    data_atualizacao_telefone TIMESTAMP,
    analisado_em TIMESTAMP,
    modelo_ia VARCHAR(50),
    versao_prompt INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
ON CONFLICT (conversation_id) DO NOTHING;
*/

-- ============================================================================
-- 3. MIGRAÇÃO: etl_control
-- ============================================================================

\echo '=== MIGRANDO etl_control ==='

/*
INSERT INTO etl_control
SELECT
    id,
    started_at,
    finished_at,
    status,
    triggered_by,
    load_type,
    is_full_load,
    watermark_start,
    watermark_end,
    rows_extracted,
    rows_inserted,
    rows_updated,
    rows_total,
    execution_time_seconds,
    error_message,
    1 AS tenant_id,    -- AllpFit
    NULL AS inbox_ids  -- Será preenchido pelo novo ETL
FROM dblink(
    'dbname=allpfit user=' || current_user,
    'SELECT * FROM etl_control ORDER BY id'
) AS t(
    id INTEGER,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status VARCHAR(20),
    triggered_by VARCHAR(50),
    load_type VARCHAR(20),
    is_full_load BOOLEAN,
    watermark_start TIMESTAMP,
    watermark_end TIMESTAMP,
    rows_extracted INTEGER,
    rows_inserted INTEGER,
    rows_updated INTEGER,
    rows_total INTEGER,
    execution_time_seconds NUMERIC(10,2),
    error_message TEXT
);

-- Atualizar sequence
SELECT setval('etl_control_id_seq', (SELECT COALESCE(MAX(id), 0) FROM etl_control), true);
*/

-- ============================================================================
-- VERIFICAÇÃO PÓS-MIGRAÇÃO
-- ============================================================================

\echo ''
\echo '=== VERIFICAÇÃO PÓS-MIGRAÇÃO ==='

-- Comparar contagens (se migração foi feita)
DO $$
DECLARE
    count_allpfit INTEGER := 0;
    count_geniai INTEGER;
BEGIN
    -- Contar no banco de origem (se acessível)
    BEGIN
        SELECT count
        INTO count_allpfit
        FROM dblink(
            'dbname=allpfit user=' || current_user,
            'SELECT COUNT(*)::INTEGER FROM conversas_analytics'
        ) AS t(count INTEGER);
    EXCEPTION WHEN OTHERS THEN
        count_allpfit := 0;
    END;

    -- Contar no banco de destino (tenant_id = 1)
    SELECT COUNT(*) INTO count_geniai
    FROM conversations_analytics
    WHERE tenant_id = 1;

    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════════════╗';
    RAISE NOTICE '║       COMPARAÇÃO DE REGISTROS                  ║';
    RAISE NOTICE '╠════════════════════════════════════════════════╣';
    RAISE NOTICE '║ Banco allpfit:        % registros     ║', LPAD(count_allpfit::TEXT, 10);
    RAISE NOTICE '║ Banco geniai (t_id=1): % registros     ║', LPAD(count_geniai::TEXT, 10);
    RAISE NOTICE '╚════════════════════════════════════════════════╝';
    RAISE NOTICE '';

    IF count_geniai = 0 THEN
        RAISE NOTICE '⚠️  Nenhum dado migrado. A migração está comentada por segurança.';
        RAISE NOTICE 'Descomente o bloco INSERT na linha ~120 após revisão.';
    ELSIF count_allpfit > 0 AND count_geniai != count_allpfit THEN
        RAISE WARNING 'Contagens diferentes! Verificar se migração foi completa.';
    ELSIF count_geniai > 0 THEN
        RAISE NOTICE '✅ Migração aparenta estar OK!';
    END IF;
END $$;

-- Estatísticas por tenant
SELECT
    '=== ESTATÍSTICAS POR TENANT ===' AS section,
    t.id AS tenant_id,
    t.name AS tenant_name,
    COUNT(ca.conversation_id) AS conversations,
    COUNT(ai.conversation_id) AS ai_analysis
FROM tenants t
LEFT JOIN conversations_analytics ca ON ca.tenant_id = t.id
LEFT JOIN conversas_analytics_ai ai ON ai.tenant_id = t.id
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.name
ORDER BY t.id;

-- Verificar inbox_ids únicos no tenant AllpFit
SELECT
    '=== INBOXES NO TENANT ALLPFIT ===' AS section,
    inbox_id,
    inbox_name,
    COUNT(*) AS conversation_count
FROM conversations_analytics
WHERE tenant_id = 1
GROUP BY inbox_id, inbox_name
ORDER BY inbox_id;

-- ============================================================================
-- ATUALIZAR tenant.inbox_ids BASEADO NOS DADOS MIGRADOS
-- ============================================================================

\echo '=== ATUALIZANDO tenant.inbox_ids ==='

-- Atualizar array de inbox_ids do AllpFit baseado nos dados migrados
UPDATE tenants
SET inbox_ids = (
    SELECT ARRAY_AGG(DISTINCT inbox_id ORDER BY inbox_id)
    FROM conversations_analytics
    WHERE tenant_id = 1 AND inbox_id IS NOT NULL
)
WHERE id = 1;

-- Mostrar resultado
SELECT
    'Tenant inbox_ids atualizado:' AS info,
    id,
    name,
    inbox_ids
FROM tenants
WHERE id = 1;

-- Atualizar inbox_tenant_mapping baseado nos dados reais
INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, inbox_name, channel_type, is_active)
SELECT DISTINCT
    inbox_id,
    1 AS tenant_id,
    inbox_name,
    inbox_channel_type AS channel_type,
    TRUE AS is_active
FROM conversations_analytics
WHERE tenant_id = 1 AND inbox_id IS NOT NULL
ON CONFLICT (inbox_id) DO UPDATE SET
    inbox_name = EXCLUDED.inbox_name,
    channel_type = EXCLUDED.channel_type,
    updated_at = NOW();

-- ============================================================================
-- INSTRUÇÕES FINAIS
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║              MIGRAÇÃO DE DADOS - INSTRUÇÕES                    ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ⚠️  ATENÇÃO: Por segurança, os blocos INSERT estão comentados ║'
\echo '║                                                                ║'
\echo '║  Para executar a migração:                                     ║'
\echo '║  1. FAZER BACKUP do banco allpfit:                             ║'
\echo '║     pg_dump allpfit > allpfit_backup_$(date +%Y%m%d).sql       ║'
\echo '║                                                                ║'
\echo '║  2. DESCOMENTAR os blocos INSERT neste arquivo (linhas ~120)   ║'
\echo '║                                                                ║'
\echo '║  3. EXECUTAR novamente este script:                            ║'
\echo '║     psql -d geniai_analytics -f sql/multi_tenant/04_migrate... ║'
\echo '║                                                                ║'
\echo '║  4. VALIDAR que contagens estão corretas                       ║'
\echo '║                                                                ║'
\echo '║  5. TESTAR isolamento (script 06_test_isolation.sql)           ║'
\echo '║                                                                ║'
\echo '║  📋 Alternativa (se não tem banco allpfit):                    ║'
\echo '║  - Pular esta migração e popular dados diretamente via ETL     ║'
\echo '║                                                                ║'
\echo '║  📋 Próximo passo:                                             ║'
\echo '║  - Executar sql/multi_tenant/05_row_level_security.sql         ║'
\echo '║  - Ou criar 06_test_isolation.sql para validar RLS             ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================