-- ============================================================================
-- SCRIPT: 07_create_analytics_tables.sql
-- Descrição: Cria tabelas de analytics (conversas + IA + ETL) no geniai_analytics
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -h localhost -p 5432 -U integracao_user -d geniai_analytics -f sql/multi_tenant/07_create_analytics_tables.sql

\c geniai_analytics

\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║     CRIANDO TABELAS DE ANALYTICS (MULTI-TENANT)               ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- 1. TABELA: conversations_analytics
-- ============================================================================

\echo '📊 Criando tabela conversations_analytics...'

CREATE TABLE IF NOT EXISTS conversations_analytics (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Multi-Tenant
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identificadores da conversa
    conversation_id INTEGER NOT NULL,
    display_id INTEGER,
    conversation_uuid UUID,

    -- ETL Control
    etl_inserted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    etl_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    -- Account/Inbox
    account_id INTEGER,
    account_name VARCHAR(255),
    inbox_id INTEGER,
    inbox_name VARCHAR(255),
    inbox_channel_type VARCHAR(50),
    inbox_timezone VARCHAR(50),

    -- Status
    status INTEGER,
    status_label_pt VARCHAR(50),

    -- Prioridade
    priority INTEGER,
    priority_label VARCHAR(20),
    priority_score INTEGER,
    snoozed_until TIMESTAMP WITHOUT TIME ZONE,

    -- Atribuição
    assignee_id INTEGER,
    assignee_name VARCHAR(255),
    assignee_email VARCHAR(255),
    team_id INTEGER,
    team_name VARCHAR(255),

    -- Campanha
    campaign_id INTEGER,

    -- Contato
    contact_id INTEGER,
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_identifier VARCHAR(255),

    -- Timestamps
    conversation_created_at TIMESTAMP WITHOUT TIME ZONE,
    conversation_updated_at TIMESTAMP WITHOUT TIME ZONE,
    last_activity_at TIMESTAMP WITHOUT TIME ZONE,
    first_reply_created_at TIMESTAMP WITHOUT TIME ZONE,
    waiting_since TIMESTAMP WITHOUT TIME ZONE,
    contact_last_seen_at TIMESTAMP WITHOUT TIME ZONE,
    agent_last_seen_at TIMESTAMP WITHOUT TIME ZONE,

    -- Mensagens (JSON)
    message_compiled JSONB,

    -- Cliente
    client_sender_id INTEGER,
    client_phone VARCHAR(50),

    -- Contadores de mensagens
    t_messages INTEGER,
    total_messages_public INTEGER,
    total_messages_private INTEGER,
    mc_first_message_at TIMESTAMP WITHOUT TIME ZONE,
    mc_last_message_at TIMESTAMP WITHOUT TIME ZONE,

    -- CSAT
    csat_response_id INTEGER,
    csat_rating INTEGER,
    csat_feedback TEXT,
    csat_created_at TIMESTAMP WITHOUT TIME ZONE,
    csat_nps_category VARCHAR(50),
    csat_sentiment_category VARCHAR(50),
    has_written_feedback BOOLEAN,
    has_detailed_feedback BOOLEAN,
    has_csat BOOLEAN,

    -- Métricas de tempo (segundos)
    first_response_time_seconds INTEGER,
    first_response_time_minutes NUMERIC(10,1),
    resolution_time_seconds INTEGER,
    waiting_time_seconds INTEGER,
    conversation_duration_seconds INTEGER,
    avg_time_between_messages_seconds NUMERIC(10,1),

    -- Flags booleanas (estado)
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

    -- Flags booleanas (performance)
    is_fast_response BOOLEAN,
    is_slow_response BOOLEAN,
    is_fast_resolution BOOLEAN,
    is_waiting_long BOOLEAN,

    -- Flags booleanas (engagement)
    contact_has_seen BOOLEAN,
    agent_has_seen BOOLEAN,

    -- Contadores de mensagens por tipo
    user_messages_count INTEGER,
    contact_messages_count INTEGER,
    private_notes_count INTEGER,

    -- Conteúdo de mensagens
    first_message_text TEXT,
    last_message_text TEXT,
    first_message_sender_type VARCHAR(50),
    last_message_sender_type VARCHAR(50),

    -- Métricas de mensagens
    avg_message_length INTEGER,
    max_message_length INTEGER,

    -- Flags de tipo de mensagem
    has_user_messages BOOLEAN,
    has_contact_messages BOOLEAN,
    has_private_notes BOOLEAN,
    has_contact_reply BOOLEAN,

    -- Flags de tamanho de conversa
    is_short_conversation BOOLEAN,
    is_long_conversation BOOLEAN,

    -- Ratios
    user_message_ratio NUMERIC(5,2),
    contact_message_ratio NUMERIC(5,2),

    -- Bot vs Human
    has_human_intervention BOOLEAN,
    is_bot_resolved BOOLEAN,

    -- Dimensões temporais
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

    -- Flags temporais
    is_weekday BOOLEAN,
    is_weekend BOOLEAN,
    is_business_hours BOOLEAN,
    is_night_time BOOLEAN,

    -- Cálculos de idade
    days_since_creation INTEGER,
    is_today BOOLEAN,
    is_yesterday BOOLEAN,
    is_this_week BOOLEAN,
    is_this_month BOOLEAN,
    is_this_year BOOLEAN,

    -- Formatações
    conversation_date_formatted VARCHAR(20),
    conversation_datetime_formatted VARCHAR(30),
    conversation_year_month VARCHAR(10),
    conversation_year_week VARCHAR(10)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations_analytics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_conversation_id ON conversations_analytics(tenant_id, conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_date ON conversations_analytics(tenant_id, conversation_date);
CREATE INDEX IF NOT EXISTS idx_conversations_inbox_id ON conversations_analytics(inbox_id);
CREATE INDEX IF NOT EXISTS idx_conversations_contact_id ON conversations_analytics(contact_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations_analytics(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations_analytics(conversation_created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_date ON conversations_analytics(conversation_date);
CREATE INDEX IF NOT EXISTS idx_conversations_year_month ON conversations_analytics(conversation_year_month);
CREATE INDEX IF NOT EXISTS idx_conversations_has_csat ON conversations_analytics(has_csat);
CREATE INDEX IF NOT EXISTS idx_conversations_is_resolved ON conversations_analytics(is_resolved);
CREATE INDEX IF NOT EXISTS idx_conversations_has_human ON conversations_analytics(has_human_intervention);
CREATE INDEX IF NOT EXISTS idx_conversations_is_bot_resolved ON conversations_analytics(is_bot_resolved);

-- Índice único composto (tenant_id + conversation_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_tenant_conv_unique
ON conversations_analytics(tenant_id, conversation_id);

-- Comentários
COMMENT ON TABLE conversations_analytics IS
'Análises de conversas do Chatwoot (multi-tenant). Cada conversa pertence a um tenant específico.';

COMMENT ON COLUMN conversations_analytics.tenant_id IS
'ID do tenant (cliente) dono desta conversa. Usado para isolamento via RLS.';

\echo '✅ Tabela conversations_analytics criada!'
\echo ''

-- ============================================================================
-- 2. TABELA: conversations_analytics_ai
-- ============================================================================

\echo '🤖 Criando tabela conversations_analytics_ai...'

CREATE TABLE IF NOT EXISTS conversations_analytics_ai (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Multi-Tenant
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Foreign Key para conversations_analytics
    conversation_id INTEGER NOT NULL,

    -- Análise de IA
    ai_analysis JSONB,
    ai_summary TEXT,
    ai_sentiment VARCHAR(50),
    ai_intent VARCHAR(100),
    ai_priority_score INTEGER,
    ai_lead_quality VARCHAR(50),
    ai_next_best_action TEXT,

    -- Extração de entidades
    ai_extracted_phone VARCHAR(50),
    ai_extracted_email VARCHAR(255),
    ai_extracted_name VARCHAR(255),
    ai_extracted_location TEXT,

    -- Classificações
    ai_is_lead BOOLEAN,
    ai_is_customer BOOLEAN,
    ai_is_support BOOLEAN,
    ai_is_sales BOOLEAN,
    ai_needs_human BOOLEAN,

    -- Métricas de qualidade
    ai_confidence_score NUMERIC(5,2),
    ai_model_version VARCHAR(50),

    -- Timestamps
    ai_analyzed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    ai_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_ai_tenant_id ON conversations_analytics_ai(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_id ON conversations_analytics_ai(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_tenant_conversation ON conversations_analytics_ai(tenant_id, conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_is_lead ON conversations_analytics_ai(ai_is_lead);
CREATE INDEX IF NOT EXISTS idx_ai_sentiment ON conversations_analytics_ai(ai_sentiment);
CREATE INDEX IF NOT EXISTS idx_ai_lead_quality ON conversations_analytics_ai(ai_lead_quality);

-- Índice único
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_tenant_conv_unique
ON conversations_analytics_ai(tenant_id, conversation_id);

-- Comentários
COMMENT ON TABLE conversations_analytics_ai IS
'Análises de IA das conversas (multi-tenant). Uma análise por conversa.';

\echo '✅ Tabela conversations_analytics_ai criada!'
\echo ''

-- ============================================================================
-- 3. TABELA: etl_control
-- ============================================================================

\echo '⚙️  Criando tabela etl_control...'

CREATE TABLE IF NOT EXISTS etl_control (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Multi-Tenant (NULL = execução global)
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,

    -- Execução
    execution_id UUID DEFAULT uuid_generate_v4(),
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITHOUT TIME ZONE,
    duration_seconds INTEGER,

    -- Tipo de carga
    load_type VARCHAR(20), -- 'full', 'incremental'
    is_full_load BOOLEAN DEFAULT FALSE,

    -- Status
    status VARCHAR(20), -- 'running', 'success', 'failed'
    triggered_by VARCHAR(50), -- 'manual', 'scheduler', 'api'

    -- Watermark
    watermark_start TIMESTAMP WITHOUT TIME ZONE,
    watermark_end TIMESTAMP WITHOUT TIME ZONE,

    -- Estatísticas
    records_extracted INTEGER,
    records_inserted INTEGER,
    records_updated INTEGER,
    records_failed INTEGER,

    -- Erros
    error_message TEXT,
    error_details JSONB,

    -- Metadados
    source_system VARCHAR(50), -- 'chatwoot', 'crm'
    target_table VARCHAR(100),
    etl_version VARCHAR(20)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_etl_tenant_id ON etl_control(tenant_id);
CREATE INDEX IF NOT EXISTS idx_etl_started_at ON etl_control(started_at);
CREATE INDEX IF NOT EXISTS idx_etl_status ON etl_control(status);
CREATE INDEX IF NOT EXISTS idx_etl_execution_id ON etl_control(execution_id);

-- Comentários
COMMENT ON TABLE etl_control IS
'Controle de execuções ETL (multi-tenant). Registra histórico de cargas de dados.';

\echo '✅ Tabela etl_control criada!'
\echo ''

-- ============================================================================
-- 4. TRIGGERS
-- ============================================================================

\echo '🔔 Criando triggers...'

-- Trigger para updated_at em conversations_analytics
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.etl_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_conversations_updated_at
    BEFORE UPDATE ON conversations_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_updated_at();

-- Trigger para updated_at em conversations_analytics_ai
CREATE OR REPLACE FUNCTION update_ai_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.ai_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ai_updated_at
    BEFORE UPDATE ON conversations_analytics_ai
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_updated_at();

\echo '✅ Triggers criados!'
\echo ''

-- ============================================================================
-- 5. VERIFICAÇÃO
-- ============================================================================

\echo '📋 VERIFICAÇÃO FINAL:'
\echo ''

SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as total_columns
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('conversations_analytics', 'conversations_analytics_ai', 'etl_control')
ORDER BY table_name;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║              ✅ TABELAS DE ANALYTICS CRIADAS!                  ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ✅ conversations_analytics (119 colunas)                      ║'
\echo '║  ✅ conversations_analytics_ai (18 colunas)                    ║'
\echo '║  ✅ etl_control (20 colunas)                                   ║'
\echo '║  ✅ Índices criados (21 índices)                               ║'
\echo '║  ✅ Triggers criados (2 triggers)                              ║'
\echo '║                                                                ║'
\echo '║  📋 PRÓXIMO PASSO:                                             ║'
\echo '║  Executar: 08_migrate_data.sql                                 ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''
