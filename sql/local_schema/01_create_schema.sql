-- ============================================================================
-- SCHEMA DO BANCO LOCAL - allpfit
-- ============================================================================
-- Este script cria a estrutura de tabelas no banco PostgreSQL LOCAL
-- onde os dados extraídos do banco remoto (Chatwoot) serão armazenados
-- ============================================================================

-- ============================================================================
-- TABELA: conversas_analytics
-- ============================================================================
-- Esta tabela armazena TODOS os dados das conversas, replicando localmente
-- os dados da view remota vw_conversations_analytics_final
-- ============================================================================

DROP TABLE IF EXISTS conversas_analytics CASCADE;

CREATE TABLE conversas_analytics (

    -- ========================================
    -- CHAVE PRIMÁRIA E CONTROLE
    -- ========================================
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER UNIQUE NOT NULL,  -- ID original da conversa no Chatwoot
    etl_inserted_at TIMESTAMP DEFAULT NOW(),  -- Quando foi inserido via ETL
    etl_updated_at TIMESTAMP DEFAULT NOW(),   -- Última atualização via ETL

    -- ========================================
    -- IDENTIFICADORES (da view base)
    -- ========================================
    display_id INTEGER,
    conversation_uuid UUID,
    account_id INTEGER,

    -- ========================================
    -- STATUS E CLASSIFICAÇÃO
    -- ========================================
    status INTEGER,  -- 0=open, 1=resolved, 2=pending, 3=snoozed, 4=closed
    status_label_pt VARCHAR(50),  -- Status em português
    priority INTEGER,  -- 0-4 (0=none, 1=low, 2=medium, 3=high, 4=urgent)
    priority_label VARCHAR(20),
    priority_score INTEGER,
    snoozed_until TIMESTAMP,

    -- ========================================
    -- ATRIBUIÇÃO
    -- ========================================
    assignee_id INTEGER,
    assignee_name VARCHAR(255),
    assignee_email VARCHAR(255),
    team_id INTEGER,
    team_name VARCHAR(255),
    campaign_id INTEGER,

    -- ========================================
    -- RELACIONAMENTOS
    -- ========================================
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

    -- ========================================
    -- TIMESTAMPS PRINCIPAIS
    -- ========================================
    conversation_created_at TIMESTAMP,
    conversation_updated_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    first_reply_created_at TIMESTAMP,
    waiting_since TIMESTAMP,
    contact_last_seen_at TIMESTAMP,
    agent_last_seen_at TIMESTAMP,

    -- ========================================
    -- MENSAGENS (JSON e contadores)
    -- ========================================
    message_compiled JSONB,  -- JSON com todas as mensagens
    client_sender_id INTEGER,
    client_phone VARCHAR(50),
    t_messages INTEGER,  -- Total de mensagens
    total_messages_public INTEGER,
    total_messages_private INTEGER,
    mc_first_message_at TIMESTAMP,
    mc_last_message_at TIMESTAMP,

    -- ========================================
    -- CSAT (Satisfação do Cliente)
    -- ========================================
    csat_response_id INTEGER,
    csat_rating INTEGER,
    csat_feedback TEXT,
    csat_created_at TIMESTAMP,
    csat_nps_category VARCHAR(50),
    csat_sentiment_category VARCHAR(50),
    has_written_feedback BOOLEAN,
    has_detailed_feedback BOOLEAN,
    has_csat BOOLEAN,

    -- ========================================
    -- MÉTRICAS DE TEMPO (segundos/minutos)
    -- ========================================
    first_response_time_seconds INTEGER,
    first_response_time_minutes NUMERIC(10,1),
    resolution_time_seconds INTEGER,
    waiting_time_seconds INTEGER,
    conversation_duration_seconds INTEGER,
    avg_time_between_messages_seconds NUMERIC(10,1),

    -- ========================================
    -- FLAGS BOOLEANOS - STATUS
    -- ========================================
    is_assigned BOOLEAN,
    has_team BOOLEAN,
    is_resolved BOOLEAN,
    is_open BOOLEAN,
    is_pending BOOLEAN,
    is_snoozed BOOLEAN,
    has_contact BOOLEAN,
    is_waiting BOOLEAN,

    -- ========================================
    -- FLAGS BOOLEANOS - PRIORIDADE
    -- ========================================
    has_priority BOOLEAN,
    is_high_priority BOOLEAN,
    is_from_campaign BOOLEAN,

    -- ========================================
    -- FLAGS BOOLEANOS - TEMPO
    -- ========================================
    is_fast_response BOOLEAN,
    is_slow_response BOOLEAN,
    is_fast_resolution BOOLEAN,
    is_waiting_long BOOLEAN,

    -- ========================================
    -- FLAGS BOOLEANOS - VISUALIZAÇÃO
    -- ========================================
    contact_has_seen BOOLEAN,
    agent_has_seen BOOLEAN,

    -- ========================================
    -- ESTATÍSTICAS DE MENSAGENS
    -- ========================================
    user_messages_count INTEGER,
    contact_messages_count INTEGER,
    private_notes_count INTEGER,
    first_message_text TEXT,
    last_message_text TEXT,
    first_message_sender_type VARCHAR(50),
    last_message_sender_type VARCHAR(50),
    avg_message_length INTEGER,
    max_message_length INTEGER,

    -- ========================================
    -- FLAGS - MENSAGENS
    -- ========================================
    has_user_messages BOOLEAN,
    has_contact_messages BOOLEAN,
    has_private_notes BOOLEAN,
    has_contact_reply BOOLEAN,
    is_short_conversation BOOLEAN,
    is_long_conversation BOOLEAN,

    -- ========================================
    -- RATIOS E PROPORÇÕES
    -- ========================================
    user_message_ratio NUMERIC(5,2),
    contact_message_ratio NUMERIC(5,2),

    -- ========================================
    -- ANÁLISE IA/BOT
    -- ========================================
    has_human_intervention BOOLEAN,
    is_bot_resolved BOOLEAN,

    -- ========================================
    -- MÉTRICAS TEMPORAIS
    -- ========================================
    conversation_date DATE,
    conversation_year INTEGER,
    conversation_month INTEGER,
    conversation_day INTEGER,
    conversation_day_of_week INTEGER,  -- 0=domingo, 6=sábado
    conversation_hour INTEGER,
    conversation_minute INTEGER,
    conversation_week_of_year INTEGER,
    conversation_quarter INTEGER,

    -- Labels temporais
    conversation_day_name VARCHAR(20),
    conversation_month_name VARCHAR(20),
    conversation_period VARCHAR(20),  -- Manhã, Tarde, Noite, Madrugada

    -- Flags temporais
    is_weekday BOOLEAN,
    is_weekend BOOLEAN,
    is_business_hours BOOLEAN,
    is_night_time BOOLEAN,

    -- Datas relativas
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

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================
-- Índices otimizam consultas no dashboard tornando buscas muito mais rápidas

-- Índice único na chave primária (já criado automaticamente)
-- CREATE UNIQUE INDEX idx_conversas_analytics_id ON conversas_analytics(id);

-- Índice único no conversation_id (já criado pelo UNIQUE)
-- CREATE UNIQUE INDEX idx_conversas_analytics_conversation_id ON conversas_analytics(conversation_id);

-- Índices para filtros comuns no dashboard
CREATE INDEX idx_conversas_analytics_status ON conversas_analytics(status);
CREATE INDEX idx_conversas_analytics_created_at ON conversas_analytics(conversation_created_at);
CREATE INDEX idx_conversas_analytics_date ON conversas_analytics(conversation_date);
CREATE INDEX idx_conversas_analytics_contact_id ON conversas_analytics(contact_id);
CREATE INDEX idx_conversas_analytics_assignee_id ON conversas_analytics(assignee_id);
CREATE INDEX idx_conversas_analytics_team_id ON conversas_analytics(team_id);
CREATE INDEX idx_conversas_analytics_inbox_id ON conversas_analytics(inbox_id);

-- Índices para análises temporais
CREATE INDEX idx_conversas_analytics_year_month ON conversas_analytics(conversation_year_month);
CREATE INDEX idx_conversas_analytics_year ON conversas_analytics(conversation_year);

-- Índices para análises booleanas (flags)
CREATE INDEX idx_conversas_analytics_is_resolved ON conversas_analytics(is_resolved);
CREATE INDEX idx_conversas_analytics_has_csat ON conversas_analytics(has_csat);
CREATE INDEX idx_conversas_analytics_has_human ON conversas_analytics(has_human_intervention);
CREATE INDEX idx_conversas_analytics_is_bot_resolved ON conversas_analytics(is_bot_resolved);

-- Índice composto para análises temporais + status
CREATE INDEX idx_conversas_analytics_date_status ON conversas_analytics(conversation_date, status);

-- ============================================================================
-- COMENTÁRIOS NA TABELA
-- ============================================================================

COMMENT ON TABLE conversas_analytics IS
'Tabela principal de analytics das conversas do Chatwoot.
Armazena dados extraídos da view vw_conversations_analytics_final do banco remoto.
Atualizada diariamente via ETL.
Total de campos: ~100 campos para análise completa.';

COMMENT ON COLUMN conversas_analytics.conversation_id IS 'ID original da conversa no Chatwoot (chave única)';
COMMENT ON COLUMN conversas_analytics.etl_inserted_at IS 'Timestamp de quando o registro foi inserido pelo ETL';
COMMENT ON COLUMN conversas_analytics.etl_updated_at IS 'Timestamp da última atualização pelo ETL';
COMMENT ON COLUMN conversas_analytics.message_compiled IS 'JSON com array de todas as mensagens da conversa';
COMMENT ON COLUMN conversas_analytics.status IS 'Status numérico: 0=open, 1=resolved, 2=pending, 3=snoozed, 4=closed';
COMMENT ON COLUMN conversas_analytics.has_human_intervention IS 'TRUE se teve mensagem de agente humano';
COMMENT ON COLUMN conversas_analytics.is_bot_resolved IS 'TRUE se foi resolvida apenas pelo bot (sem humano)';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
