-- ============================================================================
-- ARQUIVO: 06_tenant_configs_queries.sql
-- Descrição: Exemplos de queries úteis para a tabela tenant_configs
-- Banco: geniai_analytics
-- ============================================================================

-- Conectar ao banco
\c geniai_analytics

-- ============================================================================
-- SEÇÃO 1: QUERIES BÁSICAS DE LEITURA
-- ============================================================================

-- 1.1 Buscar configuração completa de um tenant
\echo '=== 1.1: Configuração completa de um tenant ==='
SELECT
    tenant_id,
    logo_url,
    primary_color,
    secondary_color,
    accent_color,
    features,
    notifications,
    dashboard_config,
    version,
    created_at,
    updated_at
FROM tenant_configs
WHERE tenant_id = 1;  -- AllpFit

-- 1.2 Listar todas as configurações (resumido)
\echo '=== 1.2: Lista resumida de todas as configs ==='
SELECT
    tc.tenant_id,
    t.name AS tenant_name,
    tc.primary_color,
    tc.secondary_color,
    tc.version,
    tc.updated_at
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.deleted_at IS NULL
ORDER BY tc.tenant_id;

-- 1.3 Verificar features habilitados por tenant
\echo '=== 1.3: Features habilitados por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.features
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active'
ORDER BY tc.tenant_id;

-- ============================================================================
-- SEÇÃO 2: QUERIES COM FEATURES
-- ============================================================================

-- 2.1 Buscar tenants com feature específico ativado (export_csv)
\echo '=== 2.1: Tenants com export_csv ativado ==='
SELECT
    tc.tenant_id,
    t.name AS tenant_name,
    tc.features->>'export_csv' AS export_csv_enabled
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"export_csv": true}'::JSONB
  AND t.status = 'active'
ORDER BY t.name;

-- 2.2 Tenants com api_access habilitado
\echo '=== 2.2: Tenants com API access habilitado ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.features->>'api_access' AS api_access
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"api_access": true}'::JSONB;

-- 2.3 Tenants COM ai_analysis E custom_reports habilitados
\echo '=== 2.3: Tenants com AI analysis E custom reports ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.features->>'ai_analysis' AS ai_analysis,
    tc.features->>'custom_reports' AS custom_reports
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"ai_analysis": true, "custom_reports": true}'::JSONB;

-- 2.4 Listar TODOS os features para um tenant específico
\echo '=== 2.4: Todos os features para AllpFit (tenant_id=1) ==='
SELECT
    key AS feature_name,
    value AS is_enabled
FROM tenant_configs,
     jsonb_each(features)
WHERE tenant_id = 1
ORDER BY key;

-- 2.5 Contar features ativados por tenant
\echo '=== 2.5: Contagem de features ativados por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    COUNT(*) FILTER (WHERE (value)::BOOLEAN = true) AS enabled_features,
    COUNT(*) FILTER (WHERE (value)::BOOLEAN = false) AS disabled_features,
    COUNT(*) AS total_features
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id,
     jsonb_each(tc.features)
GROUP BY tc.tenant_id, t.name
ORDER BY tc.tenant_id;

-- ============================================================================
-- SEÇÃO 3: QUERIES COM NOTIFICAÇÕES
-- ============================================================================

-- 3.1 Tenants com email alerts ativado
\echo '=== 3.1: Tenants com email alerts ativado ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.notifications->>'email_alerts' AS email_alerts,
    tc.notifications->>'alert_threshold' AS threshold,
    tc.notifications->>'alert_email' AS alert_email
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.notifications @> '{"email_alerts": true}'::JSONB;

-- 3.2 Tenants com webhook configurado
\echo '=== 3.2: Tenants com webhook configurado ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.notifications->>'webhook_url' AS webhook_url,
    tc.notifications->>'webhook_url' IS NOT NULL AS has_webhook
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.notifications->>'webhook_url' IS NOT NULL;

-- 3.3 Email de alerta por tenant
\echo '=== 3.3: Email de alerta configurado por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.notifications->>'alert_email' AS alert_email,
    tc.notifications->>'alert_threshold' AS alert_threshold
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.notifications->>'alert_email' IS NOT NULL
ORDER BY t.name;

-- ============================================================================
-- SEÇÃO 4: QUERIES COM DASHBOARD CONFIG
-- ============================================================================

-- 4.1 KPI cards order por tenant
\echo '=== 4.1: Ordem de KPI cards por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.dashboard_config->'kpi_cards_order' AS kpi_order
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
ORDER BY tc.tenant_id;

-- 4.2 Tenants com welcome message habilitado
\echo '=== 4.2: Tenants com welcome message ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.dashboard_config->>'show_welcome_message' AS show_welcome,
    tc.dashboard_config->>'default_date_range' AS default_range
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE (tc.dashboard_config->>'show_welcome_message')::BOOLEAN = true;

-- 4.3 Período de data padrão por tenant
\echo '=== 4.3: Período de data padrão por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.dashboard_config->>'default_date_range' AS default_range
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
ORDER BY tc.tenant_id;

-- ============================================================================
-- SEÇÃO 5: QUERIES COM CORES (BRANDING)
-- ============================================================================

-- 5.1 Esquema de cores por tenant
\echo '=== 5.1: Esquema de cores por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.primary_color,
    tc.secondary_color,
    tc.accent_color,
    CONCAT(tc.primary_color, ', ', tc.secondary_color, ', ', tc.accent_color) AS color_scheme
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active'
ORDER BY t.name;

-- 5.2 Tenants com cor primária específica
\echo '=== 5.2: Tenants com cor primária #FF6B35 (AllpFit) ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.primary_color,
    tc.logo_url
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.primary_color = '#FF6B35';

-- 5.3 Logo customizado por tenant
\echo '=== 5.3: Tenants com logo customizado ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.logo_url,
    tc.favicon_url,
    tc.created_at
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.logo_url IS NOT NULL
ORDER BY t.name;

-- ============================================================================
-- SEÇÃO 6: QUERIES COM INTEGRAÇÕES
-- ============================================================================

-- 6.1 Tenants com integrações configuradas
\echo '=== 6.1: Tenants com integrações configuradas ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.integrations,
    jsonb_object_keys(tc.integrations) AS integration_names
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.integrations != '{}'::JSONB
ORDER BY tc.tenant_id;

-- 6.2 Tenants com Slack integrado
\echo '=== 6.2: Tenants com Slack integrado ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.integrations->'slack' AS slack_config,
    (tc.integrations->'slack'->>'enabled')::BOOLEAN AS slack_enabled
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.integrations @> '{"slack": {"enabled": true}}'::JSONB;

-- ============================================================================
-- SEÇÃO 7: QUERIES COM ADVANCED CONFIG
-- ============================================================================

-- 7.1 Configurações avançadas por tenant
\echo '=== 7.1: Configurações avançadas por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.advanced_config->>'rate_limit_api' AS rate_limit,
    tc.advanced_config->>'max_concurrent_sessions' AS max_sessions,
    tc.advanced_config->>'data_retention_days' AS retention_days,
    tc.advanced_config->>'timezone' AS timezone
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
ORDER BY tc.tenant_id;

-- 7.2 Timezone por tenant
\echo '=== 7.2: Timezone configurado por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.advanced_config->>'timezone' AS timezone
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active'
ORDER BY t.name;

-- ============================================================================
-- SEÇÃO 8: QUERIES DE AUDITORIA (VERSIONAMENTO E HISTÓRICO)
-- ============================================================================

-- 8.1 Versão atual de cada configuração
\echo '=== 8.1: Versão atual de cada configuração ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.version,
    tc.updated_at,
    u.full_name AS updated_by
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
LEFT JOIN users u ON u.id = tc.updated_by_user_id
ORDER BY tc.tenant_id;

-- 8.2 Tenants com mais mudanças (histórico mais longo)
\echo '=== 8.2: Tenants com mais mudanças ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.version,
    jsonb_array_length(tc.change_log) AS changes_logged
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
ORDER BY tc.version DESC
LIMIT 10;

-- 8.3 Histórico de mudanças de um tenant (AllpFit)
\echo '=== 8.3: Histórico de mudanças AllpFit ==='
SELECT
    tc.tenant_id,
    tc.version,
    jsonb_array_elements(tc.change_log)->>'timestamp' AS change_time,
    jsonb_array_elements(tc.change_log)->'changed_fields' AS changes
FROM tenant_configs tc
WHERE tc.tenant_id = 1
ORDER BY tc.updated_at DESC
LIMIT 10;

-- 8.4 Última mudança por tenant
\echo '=== 8.4: Última mudança por tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.updated_at,
    COALESCE(u.full_name, 'Sistema') AS updated_by,
    jsonb_array_elements(tc.change_log)->>'timestamp' AS last_change_time
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
LEFT JOIN users u ON u.id = tc.updated_by_user_id,
     LATERAL (
        SELECT jsonb_array_elements(tc.change_log) AS first_change
        LIMIT 1
     ) AS latest
ORDER BY tc.updated_at DESC;

-- ============================================================================
-- SEÇÃO 9: QUERIES DE UPDATE
-- ============================================================================

-- 9.1 Alterar cores de um tenant
\echo '=== 9.1: Atualizar cores AllpFit ==='
-- SELECT 'Para executar, remova o comentário:';
-- UPDATE tenant_configs
-- SET
--     primary_color = '#FF6B35',
--     secondary_color = '#1E90FF',
--     updated_by_user_id = NULL  -- Ou ID do usuário que fez a mudança
-- WHERE tenant_id = 1;

-- 9.2 Habilitar feature para um tenant
\echo '=== 9.2: Habilitar api_access para AllpFit ==='
-- SELECT 'Para executar, remova o comentário:';
-- UPDATE tenant_configs
-- SET features = jsonb_set(
--     features,
--     '{api_access}',
--     'true'::jsonb
-- )
-- WHERE tenant_id = 1;

-- 9.3 Desabilitar múltiplos features
\echo '=== 9.3: Desabilitar features específicos ==='
-- SELECT 'Para executar, remova o comentário:';
-- UPDATE tenant_configs
-- SET features = features - 'webhooks' - 'api_access'
-- WHERE tenant_id = 1;

-- 9.4 Atualizar email de alerta
\echo '=== 9.4: Atualizar email de alerta ==='
-- SELECT 'Para executar, remova o comentário:';
-- UPDATE tenant_configs
-- SET notifications = jsonb_set(
--     notifications,
--     '{alert_email}',
--     '"newemail@allpfit.com.br"'::jsonb
-- )
-- WHERE tenant_id = 1;

-- 9.5 Atualizar dashboard config (ordem de KPIs)
\echo '=== 9.5: Alterar ordem de KPI cards ==='
-- SELECT 'Para executar, remova o comentário:';
-- UPDATE tenant_configs
-- SET dashboard_config = jsonb_set(
--     dashboard_config,
--     '{kpi_cards_order}',
--     '["ai_resolved", "total_conversations", "conversion_rate"]'::jsonb
-- )
-- WHERE tenant_id = 1;

-- ============================================================================
-- SEÇÃO 10: USO DE FUNÇÕES HELPER
-- ============================================================================

-- 10.1 Verificar se feature está habilitado usando função
\echo '=== 10.1: Verificar features com função helper ==='
SELECT
    tc.tenant_id,
    t.name,
    is_feature_enabled(tc.tenant_id, 'export_csv') AS export_csv_enabled,
    is_feature_enabled(tc.tenant_id, 'api_access') AS api_access_enabled,
    is_feature_enabled(tc.tenant_id, 'custom_reports') AS custom_reports_enabled,
    is_feature_enabled(tc.tenant_id, 'webhooks') AS webhooks_enabled
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active';

-- 10.2 Obter notificações usando função
\echo '=== 10.2: Obter notificações com função helper ==='
SELECT
    tenant_id,
    get_notification_config(tenant_id) AS notification_config
FROM tenant_configs
WHERE tenant_id IN (0, 1);

-- ============================================================================
-- SEÇÃO 11: QUERIES ÚTEIS PARA APLICAÇÃO
-- ============================================================================

-- 11.1 Dados para renderizar tema visual do frontend
\echo '=== 11.1: Dados de branding para frontend ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.logo_url,
    tc.favicon_url,
    tc.primary_color,
    tc.secondary_color,
    tc.accent_color,
    tc.custom_css
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.tenant_id = 1;

-- 11.2 Verificar permissões do tenant para UI
\echo '=== 11.2: Verificar permissões do tenant ==='
SELECT
    tc.tenant_id,
    t.name,
    CASE WHEN is_feature_enabled(tc.tenant_id, 'export_csv') THEN 'mostrar' ELSE 'esconder' END AS botao_export_csv,
    CASE WHEN is_feature_enabled(tc.tenant_id, 'api_access') THEN 'mostrar' ELSE 'esconder' END AS botao_api,
    CASE WHEN is_feature_enabled(tc.tenant_id, 'custom_reports') THEN 'mostrar' ELSE 'esconder' END AS botao_reports
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id;

-- 11.3 Dados para dashboard initialization
\echo '=== 11.3: Config para inicializar dashboard ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.dashboard_config->>'default_date_range' AS date_range,
    tc.dashboard_config->>'show_welcome_message' AS show_welcome,
    tc.dashboard_config->'kpi_cards_order' AS kpi_order,
    tc.advanced_config->>'timezone' AS timezone
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.tenant_id = 1;

-- ============================================================================
-- SEÇÃO 12: QUERIES DE ANÁLISE / REPORTING
-- ============================================================================

-- 12.1 Resumo de features por plano
\echo '=== 12.1: Features habilitados por plano ==='
SELECT
    t.plan,
    COUNT(DISTINCT tc.tenant_id) AS tenant_count,
    ARRAY_AGG(DISTINCT t.name) AS tenant_names,
    AVG(tc.version) AS avg_version
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.deleted_at IS NULL
GROUP BY t.plan
ORDER BY t.plan;

-- 12.2 Matriz de features por tenant
\echo '=== 12.2: Matriz de features (pivot-like) ==='
SELECT
    t.name AS tenant,
    is_feature_enabled(tc.tenant_id, 'export_csv')::TEXT AS export_csv,
    is_feature_enabled(tc.tenant_id, 'export_pdf')::TEXT AS export_pdf,
    is_feature_enabled(tc.tenant_id, 'api_access')::TEXT AS api_access,
    is_feature_enabled(tc.tenant_id, 'webhooks')::TEXT AS webhooks,
    is_feature_enabled(tc.tenant_id, 'custom_reports')::TEXT AS custom_reports,
    is_feature_enabled(tc.tenant_id, 'ai_analysis')::TEXT AS ai_analysis
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active'
ORDER BY t.name;

-- 12.3 Tenants ativos com mais de 5 versões de config
\echo '=== 12.3: Tenants com histórico ativo de mudanças ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.version,
    tc.updated_at,
    jsonb_array_length(tc.change_log) AS recent_changes,
    EXTRACT(DAY FROM NOW() - tc.created_at) AS days_since_creation
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE t.status = 'active'
  AND tc.version > 1
ORDER BY tc.version DESC;

-- ============================================================================
-- SEÇÃO 13: VALIDAÇÕES E INTEGRIDADE
-- ============================================================================

-- 13.1 Verificar cores inválidas
\echo '=== 13.1: Verificar colors em formato válido ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.primary_color AS color,
    CASE
        WHEN tc.primary_color ~ '^#[0-9A-Fa-f]{6}$' THEN 'VÁLIDO'
        ELSE 'INVÁLIDO'
    END AS primary_color_status,
    CASE
        WHEN tc.secondary_color ~ '^#[0-9A-Fa-f]{6}$' THEN 'VÁLIDO'
        ELSE 'INVÁLIDO'
    END AS secondary_color_status
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id;

-- 13.2 Verificar URLs HTTPS
\echo '=== 13.2: Verificar URLs (HTTPS) ==='
SELECT
    tc.tenant_id,
    t.name,
    tc.logo_url,
    CASE
        WHEN tc.logo_url IS NULL THEN 'NULL'
        WHEN tc.logo_url ~ '^https?://' THEN 'VÁLIDO'
        ELSE 'INVÁLIDO'
    END AS logo_url_status,
    tc.favicon_url,
    CASE
        WHEN tc.favicon_url IS NULL THEN 'NULL'
        WHEN tc.favicon_url ~ '^https?://' THEN 'VÁLIDO'
        ELSE 'INVÁLIDO'
    END AS favicon_url_status
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.logo_url IS NOT NULL OR tc.favicon_url IS NOT NULL;

-- 13.3 Verificar integridade de JSONB
\echo '=== 13.3: Verificar tipos JSON ==='
SELECT
    tc.tenant_id,
    t.name,
    jsonb_typeof(tc.features) AS features_type,
    jsonb_typeof(tc.notifications) AS notifications_type,
    jsonb_typeof(tc.dashboard_config) AS dashboard_config_type,
    jsonb_typeof(tc.integrations) AS integrations_type,
    jsonb_typeof(tc.advanced_config) AS advanced_config_type
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id;

-- ============================================================================
-- SEÇÃO 14: PERFORMANCE / ÍNDICES
-- ============================================================================

-- 14.1 Tamanho da tabela e índices
\echo '=== 14.1: Tamanho da tabela tenant_configs ==='
SELECT
    'tenant_configs' AS table_name,
    pg_size_pretty(pg_total_relation_size('tenant_configs')) AS total_size,
    pg_size_pretty(pg_indexes_size('tenant_configs')) AS indexes_size,
    pg_size_pretty(pg_total_relation_size('tenant_configs') - pg_indexes_size('tenant_configs')) AS table_size;

-- 14.2 Número de linhas
\echo '=== 14.2: Contagem de registros ==='
SELECT
    COUNT(*) AS total_configs,
    COUNT(*) FILTER (WHERE version > 1) AS configs_modified,
    MAX(version) AS max_version,
    AVG(version) AS avg_version
FROM tenant_configs;

-- ============================================================================
-- FIM DO ARQUIVO
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║              EXEMPLOS DE QUERIES - FIM DO ARQUIVO             ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  Para usar: descomente as queries desejadas e execute         ║'
\echo '║                                                                ║'
\echo '║  Exemplos:                                                     ║'
\echo '║  - Seção 1: Leituras básicas                                  ║'
\echo '║  - Seção 2: Buscar por features                               ║'
\echo '║  - Seção 9: Updates (cuidado!)                                ║'
\echo '║  - Seção 10: Usar funções helper                              ║'
\echo '║  - Seção 11: Dados para aplicação                             ║'
\echo '║  - Seção 13: Validações de integridade                        ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'