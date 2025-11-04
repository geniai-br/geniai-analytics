-- ============================================================================
-- SCRIPT: 03_seed_data.sql
-- Descrição: Popula dados iniciais (tenants, users, inbox mappings)
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/03_seed_data.sql

\c geniai_analytics

-- ============================================================================
-- 1. SEED: TENANTS
-- ============================================================================

-- Tenant ID 0: GeniAI Admin (especial - para administradores)
INSERT INTO tenants (id, name, slug, inbox_ids, status, plan, max_conversations, max_users)
VALUES (
    0,
    'GeniAI Admin',
    'geniai-admin',
    '{}',                    -- Sem inboxes (não é cliente real)
    'active',
    'internal',
    -1,                      -- Ilimitado
    -1                       -- Ilimitado
)
ON CONFLICT (id) DO NOTHING;

-- Tenant ID 1: AllpFit (primeiro cliente real - migrar dados existentes)
INSERT INTO tenants (id, name, slug, inbox_ids, status, plan, max_conversations, max_users, account_id)
VALUES (
    1,
    'AllpFit CrossFit',
    'allpfit',
    '{1, 2}',                -- Inboxes 1 e 2 do Chatwoot (será atualizado após consultar banco real)
    'active',
    'pro',
    -1,                      -- Ilimitado
    10,
    1                        -- Account ID no Chatwoot (ajustar se necessário)
)
ON CONFLICT (id) DO NOTHING;

-- Ajustar sequence para próximos tenants começarem do ID 2
SELECT setval('tenants_id_seq', (SELECT MAX(id) FROM tenants), true);

-- ============================================================================
-- 2. SEED: USERS
-- ============================================================================

-- Nota: Senhas hasheadas com bcrypt (custo 12)
-- Senha padrão para desenvolvimento: "senha123"
-- Hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG

-- 2.1 Admin GeniAI (Super Admin)
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    0,
    'admin@geniai.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',  -- senha123
    'Administrador GeniAI',
    'super_admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- 2.2 Suporte GeniAI (Admin)
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    0,
    'suporte@geniai.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',  -- senha123
    'Suporte GeniAI',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- 2.3 Cliente AllpFit - Admin
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified, phone)
VALUES (
    1,
    'isaac@allpfit.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',  -- senha123
    'Isaac Santos',
    'admin',
    TRUE,
    TRUE,
    '+55 11 98765-4321'
)
ON CONFLICT (email) DO NOTHING;

-- 2.4 Cliente AllpFit - Usuário Visualizador
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    1,
    'visualizador@allpfit.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',  -- senha123
    'Visualizador AllpFit',
    'client',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- 3. SEED: INBOX_TENANT_MAPPING
-- ============================================================================

-- IMPORTANTE: Ajustar inbox_ids reais consultando o banco Chatwoot
-- Query para descobrir: SELECT DISTINCT inbox_id, inbox_name FROM vw_conversations_analytics_final;

-- Mapeamento AllpFit (ajustar IDs reais)
INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, inbox_name, channel_type, is_active)
VALUES
    (1, 1, 'AllpFit WhatsApp Principal', 'whatsapp', TRUE),
    (2, 1, 'AllpFit Telegram', 'telegram', TRUE)
ON CONFLICT (inbox_id) DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    inbox_name = EXCLUDED.inbox_name,
    channel_type = EXCLUDED.channel_type,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- ============================================================================
-- 4. SEED: TENANT_CONFIGS
-- ============================================================================

-- Config para GeniAI Admin
INSERT INTO tenant_configs (tenant_id, logo_url, primary_color, secondary_color, features)
VALUES (
    0,
    NULL,  -- Sem logo (admin interno)
    '#6366F1',  -- Indigo
    '#8B5CF6',  -- Purple
    '{
        "ai_analysis": true,
        "crm_integration": true,
        "custom_reports": true,
        "api_access": true,
        "export_data": true,
        "webhooks": true
    }'::jsonb
)
ON CONFLICT (tenant_id) DO NOTHING;

-- Config para AllpFit
INSERT INTO tenant_configs (tenant_id, logo_url, primary_color, secondary_color, features, dashboard_config)
VALUES (
    1,
    'https://allpfit.com.br/logo.png',  -- URL do logo (ajustar se necessário)
    '#FF6B35',  -- Laranja AllpFit
    '#004E89',  -- Azul AllpFit
    '{
        "ai_analysis": true,
        "crm_integration": true,
        "custom_reports": true,
        "api_access": false,
        "export_data": true,
        "webhooks": false
    }'::jsonb,
    '{
        "show_welcome_message": true,
        "default_date_range": "30d",
        "kpi_cards_order": ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
    }'::jsonb
)
ON CONFLICT (tenant_id) DO NOTHING;

-- ============================================================================
-- 5. LOG DE AUDITORIA: Criação Inicial
-- ============================================================================

INSERT INTO audit_logs (
    user_id,
    user_email,
    user_role,
    tenant_id,
    action,
    entity_type,
    description,
    severity
)
VALUES
    (NULL, 'system', 'system', NULL, 'seed_data', 'database', 'Seed data inicial executado (tenants, users, configs)', 'info'),
    (NULL, 'system', 'system', 0, 'create_tenant', 'tenant', 'Tenant GeniAI Admin criado', 'info'),
    (NULL, 'system', 'system', 1, 'create_tenant', 'tenant', 'Tenant AllpFit criado', 'info'),
    ((SELECT id FROM users WHERE email = 'admin@geniai.com.br'), 'admin@geniai.com.br', 'super_admin', 0, 'create_user', 'user', 'Admin GeniAI criado', 'info'),
    ((SELECT id FROM users WHERE email = 'isaac@allpfit.com.br'), 'isaac@allpfit.com.br', 'admin', 1, 'create_user', 'user', 'Admin AllpFit criado', 'info');

-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

SELECT 'Seed data inserido com sucesso!' AS status;

-- Verificar tenants
SELECT
    '=== TENANTS ===' AS section,
    id,
    name,
    slug,
    status,
    plan,
    inbox_ids
FROM tenants
ORDER BY id;

-- Verificar usuários
SELECT
    '=== USERS ===' AS section,
    u.id,
    u.email,
    u.full_name,
    u.role,
    t.name AS tenant_name,
    u.is_active
FROM users u
JOIN tenants t ON t.id = u.tenant_id
WHERE u.deleted_at IS NULL
ORDER BY u.tenant_id, u.id;

-- Verificar inbox mapping
SELECT
    '=== INBOX MAPPING ===' AS section,
    itm.inbox_id,
    itm.inbox_name,
    itm.channel_type,
    t.name AS tenant_name
FROM inbox_tenant_mapping itm
JOIN tenants t ON t.id = itm.tenant_id
WHERE itm.is_active = TRUE
ORDER BY itm.tenant_id, itm.inbox_id;

-- Verificar configs
SELECT
    '=== TENANT CONFIGS ===' AS section,
    tc.tenant_id,
    t.name AS tenant_name,
    tc.primary_color,
    tc.features->>'ai_analysis' AS ai_analysis_enabled,
    tc.features->>'crm_integration' AS crm_enabled
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
ORDER BY tc.tenant_id;

-- Estatísticas
SELECT
    '=== ESTATÍSTICAS ===' AS section,
    (SELECT COUNT(*) FROM tenants WHERE deleted_at IS NULL) AS total_tenants,
    (SELECT COUNT(*) FROM users WHERE deleted_at IS NULL) AS total_users,
    (SELECT COUNT(*) FROM sessions WHERE is_active = TRUE) AS active_sessions,
    (SELECT COUNT(*) FROM inbox_tenant_mapping WHERE is_active = TRUE) AS active_inboxes;

-- ============================================================================
-- INSTRUÇÕES IMPORTANTES
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║                    SEED DATA COMPLETO                          ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ✅ Tenants criados:                                           ║'
\echo '║     - GeniAI Admin (ID: 0)                                     ║'
\echo '║     - AllpFit (ID: 1)                                          ║'
\echo '║                                                                ║'
\echo '║  ✅ Usuários criados:                                          ║'
\echo '║     - admin@geniai.com.br (super_admin)                        ║'
\echo '║     - suporte@geniai.com.br (admin)                            ║'
\echo '║     - isaac@allpfit.com.br (admin AllpFit)                     ║'
\echo '║     - visualizador@allpfit.com.br (client AllpFit)             ║'
\echo '║                                                                ║'
\echo '║  🔑 Senha padrão (DESENVOLVIMENTO):                            ║'
\echo '║     senha123                                                   ║'
\echo '║                                                                ║'
\echo '║  ⚠️  IMPORTANTE - PRODUÇÃO:                                    ║'
\echo '║     1. ALTERAR TODAS AS SENHAS!                                ║'
\echo '║     2. Verificar inbox_ids reais no Chatwoot                   ║'
\echo '║     3. Atualizar inbox_tenant_mapping com IDs corretos         ║'
\echo '║     4. Atualizar tenants.inbox_ids com array correto           ║'
\echo '║                                                                ║'
\echo '║  📋 Próximo passo:                                             ║'
\echo '║     psql -d geniai_analytics -f sql/multi_tenant/04_migrate... ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- QUERIES ÚTEIS PARA DESCOBRIR INBOX_IDS REAIS
-- ============================================================================

-- Descomentar e executar no banco REMOTO Chatwoot para descobrir inbox_ids:
-- SELECT DISTINCT
--     inbox_id,
--     inbox_name,
--     inbox_channel_type,
--     account_id,
--     COUNT(*) AS conversation_count
-- FROM vw_conversations_analytics_final
-- WHERE account_id = 1  -- Ajustar para account_id do AllpFit
-- GROUP BY inbox_id, inbox_name, inbox_channel_type, account_id
-- ORDER BY inbox_id;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
