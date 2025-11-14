-- ============================================================================
-- SCRIPT: 03b_fix_users_and_seed.sql
-- Descrição: Corrige constraint e insere usuários
-- ============================================================================

\c geniai_analytics

-- ============================================================================
-- 1. ADICIONAR CONSTRAINT UNIQUE SEM CONDIÇÃO
-- ============================================================================

-- Dropar índice condicional
DROP INDEX IF EXISTS idx_users_email;

-- Criar constraint UNIQUE normal (sem WHERE)
ALTER TABLE users
ADD CONSTRAINT users_email_unique UNIQUE (email);

\echo '✅ Constraint UNIQUE adicionada!'
\echo ''

-- ============================================================================
-- 2. INSERIR USUÁRIOS
-- ============================================================================

\echo '👥 Inserindo usuários...'

-- Admin GeniAI (Super Admin)
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    0,
    'admin@geniai.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',
    'Administrador GeniAI',
    'super_admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Suporte GeniAI (Admin)
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    0,
    'suporte@geniai.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',
    'Suporte GeniAI',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Cliente AllpFit - Admin
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified, phone)
VALUES (
    1,
    'isaac@allpfit.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',
    'Isaac Santos',
    'admin',
    TRUE,
    TRUE,
    '+55 11 98765-4321'
)
ON CONFLICT (email) DO NOTHING;

-- Cliente AllpFit - Usuário Visualizador
INSERT INTO users (tenant_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    1,
    'visualizador@allpfit.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWx.GN8xW5CG',
    'Visualizador AllpFit',
    'client',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;

\echo '✅ Usuários inseridos!'
\echo ''

-- ============================================================================
-- 3. CRIAR ÍNDICE PARCIAL DE VOLTA (PARA PERFORMANCE)
-- ============================================================================

-- Criar índice parcial adicional (não substitui a constraint)
CREATE INDEX IF NOT EXISTS idx_users_email_active
ON users(email) WHERE deleted_at IS NULL;

\echo '✅ Índice parcial criado!'
\echo ''

-- ============================================================================
-- 4. VERIFICAÇÃO
-- ============================================================================

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

-- Estatísticas atualizadas
SELECT
    '=== ESTATÍSTICAS ===' AS section,
    (SELECT COUNT(*) FROM tenants WHERE deleted_at IS NULL) AS total_tenants,
    (SELECT COUNT(*) FROM users WHERE deleted_at IS NULL) AS total_users,
    (SELECT COUNT(*) FROM sessions WHERE is_active = TRUE) AS active_sessions,
    (SELECT COUNT(*) FROM inbox_tenant_mapping WHERE is_active = TRUE) AS active_inboxes;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║                  ✅ CORREÇÃO COMPLETA!                         ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ✅ Constraint UNIQUE corrigida                                ║'
\echo '║  ✅ 4 usuários criados com sucesso                             ║'
\echo '║                                                                ║'
\echo '║  🔑 Credenciais de login:                                      ║'
\echo '║  - admin@geniai.com.br / senha123                              ║'
\echo '║  - suporte@geniai.com.br / senha123                            ║'
\echo '║  - isaac@allpfit.com.br / senha123                             ║'
\echo '║  - visualizador@allpfit.com.br / senha123                      ║'
\echo '║                                                                ║'
\echo '║  📋 Próximo passo:                                             ║'
\echo '║  Executar: 05_row_level_security.sql                           ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''
