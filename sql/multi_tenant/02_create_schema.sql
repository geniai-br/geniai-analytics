-- ============================================================================
-- SCRIPT: 02_create_schema.sql
-- Descrição: Cria schema multi-tenant (tenants, users, sessions, configs)
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/02_create_schema.sql

\c geniai_analytics

-- ============================================================================
-- 1. TABELA: tenants (Clientes da GeniAI)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    -- Identificação
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- Ex: "AllpFit CrossFit", "Academia XYZ"
    slug VARCHAR(100) UNIQUE NOT NULL,       -- Ex: "allpfit", "academia-xyz" (URL-friendly)

    -- Configuração Chatwoot
    inbox_ids INTEGER[] NOT NULL DEFAULT '{}',  -- Array: {1, 2, 3} - inboxes deste cliente
    account_id INTEGER,                      -- ID da conta no Chatwoot (opcional)

    -- Status e Plano
    status VARCHAR(20) DEFAULT 'active'      -- active, suspended, cancelled, trial
        CHECK (status IN ('active', 'suspended', 'cancelled', 'trial')),
    plan VARCHAR(50) DEFAULT 'basic'         -- basic, pro, enterprise, custom
        CHECK (plan IN ('basic', 'pro', 'enterprise', 'custom', 'internal')),
    trial_ends_at TIMESTAMP,                 -- Data fim do trial (se aplicável)

    -- Limites (futuro)
    max_conversations INTEGER DEFAULT -1,    -- -1 = ilimitado
    max_users INTEGER DEFAULT 5,
    max_inboxes INTEGER DEFAULT 10,

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP                     -- Soft delete
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_inbox_ids ON tenants USING GIN(inbox_ids);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_tenants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_tenants_updated_at();

-- Comentários
COMMENT ON TABLE tenants IS 'Clientes da GeniAI (cada cliente = 1 tenant)';
COMMENT ON COLUMN tenants.inbox_ids IS 'Array de inbox_ids do Chatwoot pertencentes a este cliente';
COMMENT ON COLUMN tenants.slug IS 'Identificador URL-friendly para login (ex: allpfit.geniai.com.br)';
COMMENT ON COLUMN tenants.status IS 'Status do tenant: active (ativo), suspended (suspenso), cancelled (cancelado), trial (período de teste)';
COMMENT ON COLUMN tenants.max_conversations IS '-1 significa ilimitado';

-- ============================================================================
-- 2. TABELA: users (Usuários de cada tenant + admins GeniAI)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    -- Identificação
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Credenciais
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,     -- bcrypt hash

    -- Dados pessoais
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    phone VARCHAR(50),

    -- Autorização
    role VARCHAR(20) DEFAULT 'client'        -- client, admin, super_admin
        CHECK (role IN ('client', 'admin', 'super_admin')),
    permissions JSONB DEFAULT '{}',          -- Futuro: permissões granulares

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,

    -- Auditoria
    last_login TIMESTAMP,
    last_login_ip INET,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,                  -- Account lockout após X tentativas

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP                     -- Soft delete
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Trigger updated_at
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_updated_at();

-- Comentários
COMMENT ON TABLE users IS 'Usuários do sistema (clientes de tenants + admins GeniAI)';
COMMENT ON COLUMN users.role IS 'client: usuário normal do tenant | admin: admin do tenant | super_admin: admin GeniAI';
COMMENT ON COLUMN users.tenant_id IS 'Tenant ao qual este usuário pertence (0 = GeniAI admin)';
COMMENT ON COLUMN users.password_hash IS 'Hash bcrypt da senha (nunca armazenar senha em plain text)';
COMMENT ON COLUMN users.failed_login_attempts IS 'Contador de tentativas falhas (reset após login bem-sucedido)';
COMMENT ON COLUMN users.locked_until IS 'Timestamp até quando a conta está bloqueada (após muitas tentativas falhas)';

-- ============================================================================
-- 3. TABELA: sessions (Controle de sessões)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Metadados da sessão
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),                 -- desktop, mobile, tablet
    device_name VARCHAR(100),                -- Chrome/Windows, Safari/iPhone, etc

    -- Validade
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    -- Auditoria
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active, expires_at) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_tenant_id ON sessions(tenant_id);

-- Função para limpar sessões expiradas automaticamente
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM sessions
    WHERE expires_at < NOW() OR is_active = FALSE;
END;
$$ LANGUAGE plpgsql;

-- Comentários
COMMENT ON TABLE sessions IS 'Controle de sessões de login (alternativa a JWT)';
COMMENT ON COLUMN sessions.expires_at IS 'Data de expiração da sessão (default: 24h após login)';
COMMENT ON COLUMN sessions.last_activity_at IS 'Timestamp da última atividade (para session timeout por inatividade)';

-- ============================================================================
-- 4. TABELA: inbox_tenant_mapping (Mapear inbox_id → tenant_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS inbox_tenant_mapping (
    -- Mapeamento
    inbox_id INTEGER PRIMARY KEY,            -- ID do inbox no Chatwoot
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Metadados do inbox
    inbox_name VARCHAR(255),                 -- Nome do inbox (ex: "AllpFit WhatsApp")
    channel_type VARCHAR(50),                -- whatsapp, telegram, email, instagram, etc
    is_active BOOLEAN DEFAULT TRUE,

    -- Auditoria
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_inbox_tenant_id ON inbox_tenant_mapping(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inbox_active ON inbox_tenant_mapping(is_active);

-- Trigger updated_at
CREATE OR REPLACE FUNCTION update_inbox_mapping_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_inbox_mapping_updated_at
    BEFORE UPDATE ON inbox_tenant_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_mapping_updated_at();

-- Comentários
COMMENT ON TABLE inbox_tenant_mapping IS 'Mapeia inbox_id (Chatwoot) para tenant_id (GeniAI)';
COMMENT ON COLUMN inbox_tenant_mapping.inbox_id IS 'ID do inbox no banco Chatwoot (vw_conversations_analytics_final.inbox_id)';
COMMENT ON COLUMN inbox_tenant_mapping.channel_type IS 'Tipo de canal: whatsapp, telegram, email, instagram, api, etc';

-- ============================================================================
-- 5. TABELA: tenant_configs (Configurações e personalização)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenant_configs (
    tenant_id INTEGER PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,

    -- Branding
    logo_url TEXT,
    favicon_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#1E40AF',    -- Hex color
    secondary_color VARCHAR(7) DEFAULT '#10B981',
    accent_color VARCHAR(7) DEFAULT '#F59E0B',
    custom_css TEXT,

    -- Features habilitadas
    features JSONB DEFAULT '{
        "ai_analysis": true,
        "crm_integration": true,
        "custom_reports": false,
        "api_access": false,
        "export_data": true,
        "webhooks": false
    }'::jsonb,

    -- Configurações de notificação
    notifications JSONB DEFAULT '{
        "email_reports": false,
        "email_alerts": false,
        "webhook_url": null,
        "alert_threshold": 100
    }'::jsonb,

    -- Personalização de dashboard
    dashboard_config JSONB DEFAULT '{
        "show_welcome_message": true,
        "default_date_range": "30d",
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
    }'::jsonb,

    -- Integrações
    integrations JSONB DEFAULT '{}'::jsonb,    -- APIs externas, CRM, etc

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trigger updated_at
CREATE OR REPLACE FUNCTION update_tenant_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tenant_configs_updated_at
    BEFORE UPDATE ON tenant_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_configs_updated_at();

-- Comentários
COMMENT ON TABLE tenant_configs IS 'Configurações e personalizações por tenant (logo, cores, features)';
COMMENT ON COLUMN tenant_configs.features IS 'Features habilitadas para este tenant (formato JSONB para flexibilidade)';
COMMENT ON COLUMN tenant_configs.dashboard_config IS 'Configurações personalizadas do dashboard (ordem de KPIs, período padrão, etc)';

-- ============================================================================
-- 6. TABELA: audit_logs (Log de auditoria)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,

    -- Quem fez
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),                 -- Cache para caso user seja deletado
    user_role VARCHAR(20),

    -- Contexto
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL,  -- Tenant afetado (NULL = sistema)
    ip_address INET,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

    -- Ação
    action VARCHAR(100) NOT NULL,            -- create_tenant, delete_user, update_config, etc
    entity_type VARCHAR(50),                 -- tenant, user, config, etc
    entity_id INTEGER,
    description TEXT,

    -- Dados (antes/depois)
    old_value JSONB,
    new_value JSONB,

    -- Nível de severidade
    severity VARCHAR(20) DEFAULT 'info'      -- debug, info, warning, error, critical
        CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_severity ON audit_logs(severity);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- Comentários
COMMENT ON TABLE audit_logs IS 'Log de auditoria de ações administrativas (compliance, segurança)';
COMMENT ON COLUMN audit_logs.action IS 'Ação realizada: create_tenant, delete_user, update_config, login_failed, etc';
COMMENT ON COLUMN audit_logs.severity IS 'Nível de severidade para filtrar logs importantes';

-- ============================================================================
-- 7. MODIFICAR TABELAS EXISTENTES (adicionar tenant_id)
-- ============================================================================

-- Nota: Esta seção assume que as tabelas já existem do sistema single-tenant
-- Se estiver criando do zero, ignore os ALTER TABLE e use CREATE TABLE direto

-- 7.1 Tabela: conversations_analytics
DO $$
BEGIN
    -- Adicionar tenant_id se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations_analytics' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE conversations_analytics
        ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;

        COMMENT ON COLUMN conversations_analytics.tenant_id IS 'Tenant ao qual esta conversa pertence (isolamento multi-tenant)';
    END IF;

    -- Adicionar inbox_id se não existir (para performance)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations_analytics' AND column_name = 'inbox_id'
    ) THEN
        ALTER TABLE conversations_analytics
        ADD COLUMN inbox_id INTEGER;

        COMMENT ON COLUMN conversations_analytics.inbox_id IS 'ID do inbox no Chatwoot (cache para evitar joins)';
    END IF;
END $$;

-- 7.2 Tabela: conversas_analytics_ai
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversas_analytics_ai' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE conversas_analytics_ai
        ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;

        COMMENT ON COLUMN conversas_analytics_ai.tenant_id IS 'Tenant ao qual esta análise pertence';
    END IF;
END $$;

-- 7.3 Tabela: etl_control
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'etl_control' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE etl_control
        ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL;

        COMMENT ON COLUMN etl_control.tenant_id IS 'Tenant sincronizado nesta execução (NULL = sync global de todos os tenants)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'etl_control' AND column_name = 'inbox_ids'
    ) THEN
        ALTER TABLE etl_control
        ADD COLUMN inbox_ids INTEGER[];

        COMMENT ON COLUMN etl_control.inbox_ids IS 'Array de inbox_ids sincronizados nesta execução';
    END IF;
END $$;

-- ============================================================================
-- 8. ÍNDICES DE PERFORMANCE PARA MULTI-TENANT
-- ============================================================================

-- Conversations Analytics
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations_analytics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_date ON conversations_analytics(tenant_id, conversation_date DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_inbox ON conversations_analytics(tenant_id, inbox_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_status_date ON conversations_analytics(tenant_id, status, conversation_date DESC);

-- Analytics AI
CREATE INDEX IF NOT EXISTS idx_analytics_ai_tenant ON conversas_analytics_ai(tenant_id);

-- ETL Control
CREATE INDEX IF NOT EXISTS idx_etl_control_tenant ON etl_control(tenant_id);
CREATE INDEX IF NOT EXISTS idx_etl_control_tenant_status ON etl_control(tenant_id, status, finished_at DESC);

-- ============================================================================
-- 9. VIEWS ÚTEIS
-- ============================================================================

-- View: Tenants com estatísticas
CREATE OR REPLACE VIEW vw_tenants_stats AS
SELECT
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.slug,
    t.status,
    t.plan,
    t.inbox_ids,
    COALESCE(array_length(t.inbox_ids, 1), 0) AS inbox_count,
    COUNT(DISTINCT u.id) AS user_count,
    COUNT(DISTINCT ca.conversation_id) AS conversation_count,
    MAX(ca.conversation_created_at) AS last_conversation_at,
    t.created_at AS tenant_created_at
FROM tenants t
LEFT JOIN users u ON u.tenant_id = t.id AND u.deleted_at IS NULL
LEFT JOIN conversations_analytics ca ON ca.tenant_id = t.id
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.name, t.slug, t.status, t.plan, t.inbox_ids, t.created_at;

COMMENT ON VIEW vw_tenants_stats IS 'Estatísticas agregadas por tenant (usuários, conversas, etc)';

-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

SELECT 'Schema multi-tenant criado com sucesso!' AS status;

-- Listar tabelas criadas
SELECT
    'Tabelas criadas:' AS info,
    tablename AS table_name
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('tenants', 'users', 'sessions', 'inbox_tenant_mapping', 'tenant_configs', 'audit_logs')
ORDER BY tablename;

-- ============================================================================
-- PRÓXIMO PASSO
-- ============================================================================

-- Executar: psql -U postgres -d geniai_analytics -f sql/multi_tenant/03_seed_data.sql

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
