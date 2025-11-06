-- ============================================================================
-- SCRIPT: 06_tenant_configs.sql
-- Descrição: Cria e popula tabela tenant_configs com personalizações visuais
--            e configurações específicas por cliente (logo, cores, CSS, features)
-- Autor: GeniAI
-- Data: 2025-11-06
-- Banco: geniai_analytics (PostgreSQL)
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/06_tenant_configs.sql

\c geniai_analytics

-- ============================================================================
-- 1. TABELA: tenant_configs (Configurações de personalização por cliente)
-- ============================================================================

-- Dropa tabela anterior se existir (para rebuild completo)
DROP TABLE IF EXISTS tenant_configs CASCADE;

CREATE TABLE tenant_configs (
    -- Identificação
    tenant_id INTEGER PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,

    -- ========================================================================
    -- SEÇÃO 1: BRANDING (Logo e Cores)
    -- ========================================================================
    logo_url TEXT,
        CONSTRAINT chk_logo_url_format CHECK (
            logo_url IS NULL
            OR (logo_url ~ '^https?://' AND length(logo_url) <= 500)
        ),
    favicon_url TEXT,
        CONSTRAINT chk_favicon_url_format CHECK (
            favicon_url IS NULL
            OR (favicon_url ~ '^https?://' AND length(favicon_url) <= 500)
        ),

    -- Cor primária (hex format)
    primary_color VARCHAR(7) DEFAULT '#1E40AF' NOT NULL,
        CONSTRAINT chk_primary_color_format CHECK (
            primary_color ~ '^#[0-9A-Fa-f]{6}$'
        ),

    -- Cor secundária (hex format)
    secondary_color VARCHAR(7) DEFAULT '#10B981' NOT NULL,
        CONSTRAINT chk_secondary_color_format CHECK (
            secondary_color ~ '^#[0-9A-Fa-f]{6}$'
        ),

    -- Cor de destaque/acento (hex format)
    accent_color VARCHAR(7) DEFAULT '#F59E0B' NOT NULL,
        CONSTRAINT chk_accent_color_format CHECK (
            accent_color ~ '^#[0-9A-Fa-f]{6}$'
        ),

    -- ========================================================================
    -- SEÇÃO 2: CSS CUSTOMIZADO
    -- ========================================================================
    custom_css TEXT,
        CONSTRAINT chk_custom_css_size CHECK (
            custom_css IS NULL OR length(custom_css) <= 50000
        ),

    -- ========================================================================
    -- SEÇÃO 3: FEATURES (Funcionalidades habilitadas/desabilitadas)
    -- ========================================================================
    -- Formato JSONB para máxima flexibilidade
    -- Exemplo:
    -- {
    --   "export_csv": true,
    --   "advanced_filters": true,
    --   "custom_reports": false,
    --   "api_access": false,
    --   "webhooks": false,
    --   "ai_analysis": true
    -- }
    features JSONB DEFAULT '{
        "export_csv": true,
        "export_pdf": true,
        "export_excel": true,
        "advanced_filters": true,
        "custom_reports": false,
        "api_access": false,
        "webhooks": false,
        "ai_analysis": true,
        "crm_integration": true,
        "scheduled_reports": false
    }'::jsonb NOT NULL,
        CONSTRAINT chk_features_is_object CHECK (
            jsonb_typeof(features) = 'object'
        ),

    -- ========================================================================
    -- SEÇÃO 4: CONFIGURAÇÕES DE NOTIFICAÇÃO
    -- ========================================================================
    notifications JSONB DEFAULT '{
        "email_reports": false,
        "email_alerts": false,
        "sms_alerts": false,
        "webhook_url": null,
        "alert_threshold": 100,
        "alert_email": null
    }'::jsonb NOT NULL,
        CONSTRAINT chk_notifications_is_object CHECK (
            jsonb_typeof(notifications) = 'object'
        ),

    -- ========================================================================
    -- SEÇÃO 5: CONFIGURAÇÕES DO DASHBOARD
    -- ========================================================================
    dashboard_config JSONB DEFAULT '{
        "show_welcome_message": true,
        "default_date_range": "30d",
        "show_revenue_widget": true,
        "show_customer_satisfaction": true,
        "show_ai_analysis": true,
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
    }'::jsonb NOT NULL,
        CONSTRAINT chk_dashboard_config_is_object CHECK (
            jsonb_typeof(dashboard_config) = 'object'
        ),

    -- ========================================================================
    -- SEÇÃO 6: INTEGRAÇÕES EXTERNAS
    -- ========================================================================
    -- Armazena credenciais e configurações de APIs externas (criptografadas em produção)
    -- Exemplo:
    -- {
    --   "slack": { "webhook_url": "https://hooks.slack.com/...", "enabled": true },
    --   "google_analytics": { "tracking_id": "UA-...", "enabled": false },
    --   "hubspot": { "api_key": "...", "enabled": false }
    -- }
    integrations JSONB DEFAULT '{}'::jsonb NOT NULL,
        CONSTRAINT chk_integrations_is_object CHECK (
            jsonb_typeof(integrations) = 'object'
        ),

    -- ========================================================================
    -- SEÇÃO 7: CONFIGURAÇÕES AVANÇADAS
    -- ========================================================================
    advanced_config JSONB DEFAULT '{
        "rate_limit_api": 1000,
        "max_concurrent_sessions": 5,
        "data_retention_days": 365,
        "timezone": "America/Sao_Paulo"
    }'::jsonb NOT NULL,
        CONSTRAINT chk_advanced_config_is_object CHECK (
            jsonb_typeof(advanced_config) = 'object'
        ),

    -- ========================================================================
    -- SEÇÃO 8: AUDITORIA E METADADOS
    -- ========================================================================
    -- Versão da configuração (para controle de mudanças)
    version INTEGER DEFAULT 1 NOT NULL,

    -- JSON com histórico de mudanças recentes
    change_log JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================================
-- 2. ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Índice para buscar configs por tenant (already PRIMARY KEY, but explicit)
CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);

-- Índices em JSONB para queries otimizadas
CREATE INDEX IF NOT EXISTS idx_tenant_configs_features_gin ON tenant_configs USING GIN(features);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_notifications_gin ON tenant_configs USING GIN(notifications);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_dashboard_gin ON tenant_configs USING GIN(dashboard_config);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_integrations_gin ON tenant_configs USING GIN(integrations);

-- Índice para timestamps (para encontrar configs alteradas recentemente)
CREATE INDEX IF NOT EXISTS idx_tenant_configs_updated_at ON tenant_configs(updated_at DESC);

-- ============================================================================
-- 3. FUNÇÕES HELPER
-- ============================================================================

-- ============================================================================
-- FUNÇÃO: get_default_tenant_config()
-- Descrição: Retorna configuração padrão (baseline) para novos tenants
-- Uso: INSERT INTO tenant_configs (...) VALUES (tenant_id, (get_default_tenant_config()).*)
-- ============================================================================
CREATE OR REPLACE FUNCTION get_default_tenant_config()
RETURNS TABLE (
    logo_url TEXT,
    favicon_url TEXT,
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    custom_css TEXT,
    features JSONB,
    notifications JSONB,
    dashboard_config JSONB,
    integrations JSONB,
    advanced_config JSONB
) AS $$
SELECT
    NULL::TEXT,                                          -- logo_url
    NULL::TEXT,                                          -- favicon_url
    '#1E40AF'::VARCHAR(7),                              -- primary_color (azul padrão)
    '#10B981'::VARCHAR(7),                              -- secondary_color (verde padrão)
    '#F59E0B'::VARCHAR(7),                              -- accent_color (âmbar padrão)
    NULL::TEXT,                                          -- custom_css
    '{
        "export_csv": true,
        "export_pdf": true,
        "export_excel": true,
        "advanced_filters": true,
        "custom_reports": false,
        "api_access": false,
        "webhooks": false,
        "ai_analysis": true,
        "crm_integration": true,
        "scheduled_reports": false
    }'::JSONB,                                           -- features
    '{
        "email_reports": false,
        "email_alerts": false,
        "sms_alerts": false,
        "webhook_url": null,
        "alert_threshold": 100,
        "alert_email": null
    }'::JSONB,                                           -- notifications
    '{
        "show_welcome_message": true,
        "default_date_range": "30d",
        "show_revenue_widget": true,
        "show_customer_satisfaction": true,
        "show_ai_analysis": true,
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
    }'::JSONB,                                           -- dashboard_config
    '{}'::JSONB,                                         -- integrations
    '{
        "rate_limit_api": 1000,
        "max_concurrent_sessions": 5,
        "data_retention_days": 365,
        "timezone": "America/Sao_Paulo"
    }'::JSONB;                                           -- advanced_config
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_default_tenant_config() IS
'Retorna configuração padrão para novos tenants. Útil para manter valores padrão centralizados.';

-- ============================================================================
-- FUNÇÃO: apply_tenant_config_defaults(tenant_id)
-- Descrição: Aplica valores padrão a configurações NULL/vazias de um tenant
-- ============================================================================
CREATE OR REPLACE FUNCTION apply_tenant_config_defaults(p_tenant_id INTEGER)
RETURNS void AS $$
BEGIN
    -- Função idempotente: pode ser chamada múltiplas vezes com segurança
    UPDATE tenant_configs
    SET
        primary_color = COALESCE(primary_color, '#1E40AF'),
        secondary_color = COALESCE(secondary_color, '#10B981'),
        accent_color = COALESCE(accent_color, '#F59E0B'),
        features = COALESCE(features, (get_default_tenant_config()).features),
        notifications = COALESCE(notifications, (get_default_tenant_config()).notifications),
        dashboard_config = COALESCE(dashboard_config, (get_default_tenant_config()).dashboard_config),
        integrations = COALESCE(integrations, (get_default_tenant_config()).integrations),
        advanced_config = COALESCE(advanced_config, (get_default_tenant_config()).advanced_config),
        updated_at = NOW()
    WHERE tenant_id = p_tenant_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION apply_tenant_config_defaults(INTEGER) IS
'Aplica valores padrão a campos NULL em uma configuração de tenant. Idempotente.';

-- ============================================================================
-- FUNÇÃO: is_feature_enabled(tenant_id, feature_name)
-- Descrição: Verifica se um feature específico está habilitado para um tenant
-- Retorna: BOOLEAN (true = ativado, false = desativado ou null = feature não existe)
-- ============================================================================
CREATE OR REPLACE FUNCTION is_feature_enabled(
    p_tenant_id INTEGER,
    p_feature_name TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_enabled BOOLEAN;
BEGIN
    SELECT (tc.features ->> p_feature_name)::BOOLEAN INTO v_is_enabled
    FROM tenant_configs tc
    WHERE tc.tenant_id = p_tenant_id;

    RETURN COALESCE(v_is_enabled, FALSE);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION is_feature_enabled(INTEGER, TEXT) IS
'Verifica se um feature específico está habilitado para um tenant. Retorna FALSE se feature não existe.';

-- ============================================================================
-- FUNÇÃO: get_notification_config(tenant_id)
-- Descrição: Retorna configurações de notificação de um tenant
-- ============================================================================
CREATE OR REPLACE FUNCTION get_notification_config(p_tenant_id INTEGER)
RETURNS JSONB AS $$
SELECT COALESCE(notifications, '{}'::JSONB)
FROM tenant_configs
WHERE tenant_id = p_tenant_id;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_notification_config(INTEGER) IS
'Retorna configurações de notificação de um tenant';

-- ============================================================================
-- TRIGGER: Atualizar updated_at automaticamente
-- ============================================================================
CREATE OR REPLACE FUNCTION update_tenant_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    -- Incrementar versão
    NEW.version = COALESCE(NEW.version, 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tenant_configs_updated_at
    BEFORE UPDATE ON tenant_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_configs_updated_at();

-- ============================================================================
-- TRIGGER: Log de alterações em change_log
-- ============================================================================
CREATE OR REPLACE FUNCTION log_tenant_configs_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_change JSONB;
BEGIN
    -- Registrar mudanças em change_log
    v_change := jsonb_build_object(
        'timestamp', NOW(),
        'version', NEW.version,
        'changed_fields', (
            SELECT jsonb_object_agg(key, value)
            FROM jsonb_each(to_jsonb(NEW) - to_jsonb(OLD))
            WHERE key NOT IN ('updated_at', 'version', 'change_log')
        )
    );

    NEW.change_log = CASE
        WHEN jsonb_array_length(NEW.change_log) >= 50 THEN
            -- Manter apenas últimas 50 mudanças
            NEW.change_log[0:49] || jsonb_build_array(v_change)
        ELSE
            jsonb_build_array(v_change) || NEW.change_log
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_tenant_configs_changes
    BEFORE UPDATE ON tenant_configs
    FOR EACH ROW
    WHEN (OLD IS DISTINCT FROM NEW)
    EXECUTE FUNCTION log_tenant_configs_changes();

-- ============================================================================
-- 4. COMENTÁRIOS NA TABELA
-- ============================================================================

COMMENT ON TABLE tenant_configs IS
'Configurações de personalização e funcionalidades por tenant (cliente).
Armazena: branding (logo, cores), features habilitadas, notificações, dashboard config, integrações externas.
Arquitetura JSONB permite flexibilidade para diferentes tipos de clientes.';

COMMENT ON COLUMN tenant_configs.tenant_id IS
'ID do tenant (cliente). Foreign key para tenants(id) - delete em cascata.';

COMMENT ON COLUMN tenant_configs.logo_url IS
'URL do logo do cliente (HTTPS obrigatório, máximo 500 chars). NULL = usar logo padrão GeniAI.';

COMMENT ON COLUMN tenant_configs.favicon_url IS
'URL do favicon personalizado (HTTPS obrigatório, máximo 500 chars). NULL = usar favicon padrão.';

COMMENT ON COLUMN tenant_configs.primary_color IS
'Cor primária em formato hexadecimal (ex: #FF6B35). Validação: ^#[0-9A-Fa-f]{6}$ - Obrigatório.';

COMMENT ON COLUMN tenant_configs.secondary_color IS
'Cor secundária em formato hexadecimal (ex: #1E90FF). Validação: ^#[0-9A-Fa-f]{6}$ - Obrigatório.';

COMMENT ON COLUMN tenant_configs.accent_color IS
'Cor de destaque/acento em formato hexadecimal. Validação: ^#[0-9A-Fa-f]{6}$ - Obrigatório.';

COMMENT ON COLUMN tenant_configs.custom_css IS
'CSS personalizado adicional para o tenant. Máximo 50KB. NULL = sem CSS customizado.
Exemplo: body { font-family: Roboto; } .header { background-color: #FF6B35; }';

COMMENT ON COLUMN tenant_configs.features IS
'JSON com features habilitadas/desabilitadas. Exemplo: {"export_csv": true, "api_access": false}.
Permite adicionar novos features sem migração de schema (evolutivo).';

COMMENT ON COLUMN tenant_configs.notifications IS
'Configurações de notificações (email reports, alerts, webhooks). Formato JSON.
Exemplo: {"email_reports": true, "alert_threshold": 100, "webhook_url": "https://..."}';

COMMENT ON COLUMN tenant_configs.dashboard_config IS
'Personalização do dashboard (ordem de KPIs, período padrão, widgets visíveis). Formato JSON.
Permite cada tenant customizar sua experiência no dashboard.';

COMMENT ON COLUMN tenant_configs.integrations IS
'Configurações de integrações externas (Slack, Google Analytics, HubSpot, etc). Formato JSON.
Credenciais devem ser criptografadas em produção (usar pgcrypto).';

COMMENT ON COLUMN tenant_configs.advanced_config IS
'Configurações avançadas (rate limits, session limits, data retention, timezone). Formato JSON.';

COMMENT ON COLUMN tenant_configs.version IS
'Número de versão da configuração. Incrementado a cada UPDATE para controle de mudanças.';

COMMENT ON COLUMN tenant_configs.change_log IS
'JSON array com histórico das últimas 50 mudanças (timestamp, versão, campos alterados).
Useful para auditoria e reverter alterações recentes.';

COMMENT ON COLUMN tenant_configs.created_at IS
'Timestamp de criação da configuração. Definido automaticamente por DEFAULT NOW().';

COMMENT ON COLUMN tenant_configs.updated_at IS
'Timestamp da última atualização. Mantido automaticamente por TRIGGER.';

COMMENT ON COLUMN tenant_configs.updated_by_user_id IS
'ID do usuário que fez a última atualização. FK para users(id). NULL se atualizado por sistema.';

-- ============================================================================
-- 5. INSERIR SEED DATA
-- ============================================================================

-- Config para GeniAI Admin (Tenant ID: 0)
INSERT INTO tenant_configs (
    tenant_id,
    logo_url,
    favicon_url,
    primary_color,
    secondary_color,
    accent_color,
    custom_css,
    features,
    notifications,
    dashboard_config,
    integrations,
    advanced_config,
    version,
    change_log,
    created_at,
    updated_at
)
VALUES (
    0,
    NULL,                                  -- logo_url (sem logo para admin interno)
    NULL,                                  -- favicon_url
    '#6366F1',                            -- primary_color (indigo)
    '#8B5CF6',                            -- secondary_color (purple)
    '#EC4899',                            -- accent_color (pink)
    NULL,                                  -- custom_css
    '{
        "export_csv": true,
        "export_pdf": true,
        "export_excel": true,
        "advanced_filters": true,
        "custom_reports": true,
        "api_access": true,
        "webhooks": true,
        "ai_analysis": true,
        "crm_integration": true,
        "scheduled_reports": true
    }'::JSONB,                            -- features (todas habilitadas)
    '{
        "email_reports": true,
        "email_alerts": true,
        "sms_alerts": true,
        "webhook_url": null,
        "alert_threshold": 50,
        "alert_email": "admin@geniai.com.br"
    }'::JSONB,                            -- notifications
    '{
        "show_welcome_message": false,
        "default_date_range": "90d",
        "show_revenue_widget": true,
        "show_customer_satisfaction": true,
        "show_ai_analysis": true,
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "revenue", "visits_scheduled"]
    }'::JSONB,                            -- dashboard_config
    '{}'::JSONB,                          -- integrations
    '{
        "rate_limit_api": -1,
        "max_concurrent_sessions": -1,
        "data_retention_days": 0,
        "timezone": "America/Sao_Paulo"
    }'::JSONB,                            -- advanced_config (ilimitado para admin)
    1,                                     -- version
    '[]'::JSONB,                          -- change_log (vazio na criação)
    NOW(),                                 -- created_at
    NOW()                                  -- updated_at
)
ON CONFLICT (tenant_id) DO UPDATE SET
    primary_color = EXCLUDED.primary_color,
    secondary_color = EXCLUDED.secondary_color,
    accent_color = EXCLUDED.accent_color,
    features = EXCLUDED.features,
    notifications = EXCLUDED.notifications,
    dashboard_config = EXCLUDED.dashboard_config,
    integrations = EXCLUDED.integrations,
    advanced_config = EXCLUDED.advanced_config,
    updated_at = NOW(),
    version = version + 1;

-- Config para AllpFit (Tenant ID: 1)
INSERT INTO tenant_configs (
    tenant_id,
    logo_url,
    favicon_url,
    primary_color,
    secondary_color,
    accent_color,
    custom_css,
    features,
    notifications,
    dashboard_config,
    integrations,
    advanced_config,
    version,
    change_log,
    created_at,
    updated_at
)
VALUES (
    1,
    'https://allpfit.com.br/logo.png',   -- logo_url (placeholder - ajustar URL real)
    'https://allpfit.com.br/favicon.ico', -- favicon_url (placeholder)
    '#FF6B35',                            -- primary_color (laranja vibrante AllpFit)
    '#1E90FF',                            -- secondary_color (azul)
    '#00CED1',                            -- accent_color (turquoise)
    NULL,                                  -- custom_css (sem CSS customizado)
    '{
        "export_csv": true,
        "export_pdf": true,
        "export_excel": false,
        "advanced_filters": true,
        "custom_reports": true,
        "api_access": false,
        "webhooks": false,
        "ai_analysis": true,
        "crm_integration": true,
        "scheduled_reports": true
    }'::JSONB,                            -- features (customizado para AllpFit)
    '{
        "email_reports": false,
        "email_alerts": true,
        "sms_alerts": false,
        "webhook_url": null,
        "alert_threshold": 100,
        "alert_email": "isaac@allpfit.com.br"
    }'::JSONB,                            -- notifications
    '{
        "show_welcome_message": true,
        "default_date_range": "30d",
        "show_revenue_widget": true,
        "show_customer_satisfaction": true,
        "show_ai_analysis": true,
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
    }'::JSONB,                            -- dashboard_config
    '{}'::JSONB,                          -- integrations
    '{
        "rate_limit_api": 1000,
        "max_concurrent_sessions": 5,
        "data_retention_days": 365,
        "timezone": "America/Sao_Paulo"
    }'::JSONB,                            -- advanced_config
    1,                                     -- version
    '[]'::JSONB,                          -- change_log (vazio na criação)
    NOW(),                                 -- created_at
    NOW()                                  -- updated_at
)
ON CONFLICT (tenant_id) DO UPDATE SET
    logo_url = EXCLUDED.logo_url,
    favicon_url = EXCLUDED.favicon_url,
    primary_color = EXCLUDED.primary_color,
    secondary_color = EXCLUDED.secondary_color,
    accent_color = EXCLUDED.accent_color,
    features = EXCLUDED.features,
    notifications = EXCLUDED.notifications,
    dashboard_config = EXCLUDED.dashboard_config,
    integrations = EXCLUDED.integrations,
    advanced_config = EXCLUDED.advanced_config,
    updated_at = NOW(),
    version = version + 1;

-- ============================================================================
-- 6. VALIDAÇÕES PÓS-SEED
-- ============================================================================

-- Aplicar defaults para garantir nenhum campo NULL sem reason
SELECT apply_tenant_config_defaults(0);
SELECT apply_tenant_config_defaults(1);

-- ============================================================================
-- 7. LOG DE AUDITORIA
-- ============================================================================

-- Registrar criação da tabela e seed data
INSERT INTO audit_logs (
    user_email,
    user_role,
    tenant_id,
    action,
    entity_type,
    description,
    severity,
    created_at
)
VALUES
    ('system', 'system', NULL, 'create_table', 'table', 'Tabela tenant_configs criada com constraints e triggers', 'info', NOW()),
    ('system', 'system', 0, 'seed_data', 'tenant_config', 'Seed data para GeniAI Admin (tenant_id=0) inserido', 'info', NOW()),
    ('system', 'system', 1, 'seed_data', 'tenant_config', 'Seed data para AllpFit (tenant_id=1) inserido - Logo: https://allpfit.com.br/logo.png', 'info', NOW());

-- ============================================================================
-- 8. VERIFICAÇÃO FINAL
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║             TABELA tenant_configs CRIADA COM SUCESSO           ║'
\echo '╠════════════════════════════════════════════════════════════════╣'

-- Exibir estrutura da tabela
\echo '║ ESTRUTURA DA TABELA:'
SELECT
    '║ ' || column_name || ': ' || data_type ||
    CASE WHEN is_nullable = 'NO' THEN ' (NOT NULL)' ELSE '' END AS info
FROM information_schema.columns
WHERE table_name = 'tenant_configs' AND table_schema = 'public'
ORDER BY ordinal_position;

\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ SEED DATA INSERIDO:'

-- Exibir seed data inserido
SELECT
    '║ ' || t.name || ' (tenant_id=' || tc.tenant_id || ')' ||
    ' | Primary: ' || tc.primary_color ||
    ' | Secondary: ' || tc.secondary_color AS info
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.tenant_id IN (0, 1)
ORDER BY tc.tenant_id;

\echo '║'
\echo '║ AllpFit (tenant_id=1):' AS allpfit_config;
SELECT
    '║ - Logo: ' || COALESCE(logo_url, 'N/A') ||
    E'\n║ - Cores: Primary=' || primary_color || ', Secondary=' || secondary_color ||
    E'\n║ - Features habilitadas: ' || COUNT(*) FILTER (WHERE (features -> key)::BOOLEAN = true) ||
    E'\n║ - Versão: ' || version AS config_info
FROM tenant_configs tc,
     jsonb_object_keys(tc.features) AS key
WHERE tc.tenant_id = 1
GROUP BY tc.tenant_id, tc.logo_url, tc.primary_color, tc.secondary_color, tc.version;

\echo '║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ FUNÇÕES HELPER CRIADAS:'
\echo '║ - get_default_tenant_config()        : Retorna config padrão' AS func_info;
\echo '║ - apply_tenant_config_defaults(id)   : Aplica defaults' AS func_info2;
\echo '║ - is_feature_enabled(id, feature)    : Verifica feature' AS func_info3;
\echo '║ - get_notification_config(id)        : Retorna notificações' AS func_info4;
\echo '║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ TRIGGERS CRIADOS:'
\echo '║ - trigger_update_tenant_configs_updated_at    : Atualiza timestamp' AS trigger_info;
\echo '║ - trigger_log_tenant_configs_changes          : Log de mudanças' AS trigger_info2;
\echo '║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ ÍNDICES CRIADOS:'
\echo '║ - idx_tenant_configs_features_gin        : GIN para features JSON' AS index_info;
\echo '║ - idx_tenant_configs_notifications_gin   : GIN para notifications' AS index_info2;
\echo '║ - idx_tenant_configs_dashboard_gin       : GIN para dashboard_config' AS index_info3;
\echo '║ - idx_tenant_configs_updated_at          : B-tree para updated_at DESC' AS index_info4;
\echo '║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ EXEMPLOS DE USO:'
\echo '║'
\echo '║ 1. Verificar se feature está habilitado:'
\echo '║    SELECT is_feature_enabled(1, ''export_csv'');' AS example1;
\echo '║    -> true para AllpFit' AS example1b;
\echo '║'
\echo '║ 2. Buscar configuração por tenant:'
\echo '║    SELECT primary_color, secondary_color, features' AS example2;
\echo '║    FROM tenant_configs WHERE tenant_id = 1;' AS example2b;
\echo '║'
\echo '║ 3. Buscar tenants com feature específico ativado:'
\echo '║    SELECT tc.tenant_id, t.name' AS example3;
\echo '║    FROM tenant_configs tc' AS example3b;
\echo '║    JOIN tenants t ON t.id = tc.tenant_id' AS example3c;
\echo '║    WHERE tc.features ->> ''api_access'' = ''true'';' AS example3d;
\echo '║'
\echo '║ 4. Atualizar cores de um tenant:'
\echo '║    UPDATE tenant_configs' AS example4;
\echo '║    SET primary_color = ''#FF00FF'', secondary_color = ''#00FF00''' AS example4b;
\echo '║    WHERE tenant_id = 1;' AS example4c;
\echo '║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║ PRÓXIMAS MIGRAÇÕES:'
\echo '║'
\echo '║ Executar: psql -d geniai_analytics -f sql/multi_tenant/07_...' AS next_step;
\echo '║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- ESTATÍSTICAS FINAIS
-- ============================================================================

\echo 'ESTATÍSTICAS:'
SELECT
    'Tenants configurados: ' || COUNT(*) AS stat,
    'Mem usage: ' || pg_size_pretty(pg_total_relation_size('tenant_configs')) AS mem
FROM tenant_configs;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================