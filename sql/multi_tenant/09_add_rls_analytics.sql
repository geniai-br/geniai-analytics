-- ============================================================================
-- SCRIPT: 09_add_rls_analytics.sql
-- Descrição: Adiciona Row-Level Security nas tabelas de analytics
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -h localhost -p 5432 -U integracao_user -d geniai_analytics -f sql/multi_tenant/09_add_rls_analytics.sql

\c geniai_analytics

\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║       ADICIONANDO RLS NAS TABELAS DE ANALYTICS                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- 1. HABILITAR RLS NAS TABELAS
-- ============================================================================

\echo '🔒 Habilitando Row-Level Security...'
\echo ''

ALTER TABLE conversations_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations_analytics_ai ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_control ENABLE ROW LEVEL SECURITY;

\echo '✅ RLS habilitado em 3 tabelas!'
\echo ''

-- ============================================================================
-- 2. POLÍTICAS PARA conversations_analytics
-- ============================================================================

\echo '📊 Criando políticas para conversations_analytics...'

-- Política: Clientes veem apenas conversas do próprio tenant
CREATE POLICY tenant_own_conversations ON conversations_analytics
    FOR SELECT
    TO authenticated_users
    USING (tenant_id = get_current_tenant_id());

-- Política: Admins veem todas as conversas
CREATE POLICY admin_all_conversations ON conversations_analytics
    FOR SELECT
    TO admin_users
    USING (TRUE);

-- Política: Admins podem gerenciar (INSERT, UPDATE, DELETE) conversas
CREATE POLICY admin_manage_conversations ON conversations_analytics
    FOR ALL
    TO admin_users
    USING (TRUE)
    WITH CHECK (TRUE);

-- Política: ETL pode inserir/atualizar conversas (bypass RLS)
CREATE POLICY etl_manage_conversations ON conversations_analytics
    FOR ALL
    TO etl_service
    USING (TRUE)
    WITH CHECK (TRUE);

\echo '✅ 4 políticas criadas para conversations_analytics'
\echo ''

-- ============================================================================
-- 3. POLÍTICAS PARA conversations_analytics_ai
-- ============================================================================

\echo '🤖 Criando políticas para conversations_analytics_ai...'

-- Política: Clientes veem apenas análises do próprio tenant
CREATE POLICY tenant_own_ai_analysis ON conversations_analytics_ai
    FOR SELECT
    TO authenticated_users
    USING (tenant_id = get_current_tenant_id());

-- Política: Admins veem todas as análises
CREATE POLICY admin_all_ai_analysis ON conversations_analytics_ai
    FOR SELECT
    TO admin_users
    USING (TRUE);

-- Política: Admins podem gerenciar análises
CREATE POLICY admin_manage_ai_analysis ON conversations_analytics_ai
    FOR ALL
    TO admin_users
    USING (TRUE)
    WITH CHECK (TRUE);

-- Política: ETL pode inserir/atualizar análises
CREATE POLICY etl_manage_ai_analysis ON conversations_analytics_ai
    FOR ALL
    TO etl_service
    USING (TRUE)
    WITH CHECK (TRUE);

\echo '✅ 4 políticas criadas para conversations_analytics_ai'
\echo ''

-- ============================================================================
-- 4. POLÍTICAS PARA etl_control
-- ============================================================================

\echo '⚙️  Criando políticas para etl_control...'

-- Política: Clientes veem apenas logs ETL do próprio tenant
CREATE POLICY tenant_own_etl_logs ON etl_control
    FOR SELECT
    TO authenticated_users
    USING (tenant_id = get_current_tenant_id() OR tenant_id IS NULL);

-- Política: Admins veem todos os logs ETL
CREATE POLICY admin_all_etl_logs ON etl_control
    FOR SELECT
    TO admin_users
    USING (TRUE);

-- Política: Admins podem gerenciar logs ETL
CREATE POLICY admin_manage_etl_logs ON etl_control
    FOR ALL
    TO admin_users
    USING (TRUE)
    WITH CHECK (TRUE);

-- Política: ETL pode inserir/atualizar logs (bypass RLS)
CREATE POLICY etl_manage_own_logs ON etl_control
    FOR ALL
    TO etl_service
    USING (TRUE)
    WITH CHECK (TRUE);

\echo '✅ 4 políticas criadas para etl_control'
\echo ''

-- ============================================================================
-- 5. GRANTS - Conceder permissões aos roles
-- ============================================================================

\echo '🔑 Configurando permissões...'
\echo ''

-- Authenticated users (clientes) - READ ONLY
GRANT SELECT ON conversations_analytics TO authenticated_users;
GRANT SELECT ON conversations_analytics_ai TO authenticated_users;
GRANT SELECT ON etl_control TO authenticated_users;

-- Admin users - FULL ACCESS
GRANT ALL ON conversations_analytics TO admin_users;
GRANT ALL ON conversations_analytics_ai TO admin_users;
GRANT ALL ON etl_control TO admin_users;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO admin_users;

-- ETL service - INSERT/UPDATE only
GRANT SELECT, INSERT, UPDATE ON conversations_analytics TO etl_service;
GRANT SELECT, INSERT, UPDATE ON conversations_analytics_ai TO etl_service;
GRANT SELECT, INSERT, UPDATE ON etl_control TO etl_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO etl_service;

\echo '✅ Permissões concedidas!'
\echo ''

-- ============================================================================
-- 6. VERIFICAÇÃO
-- ============================================================================

\echo '═══════════════════════════════════════════════════════════════'
\echo '  VERIFICAÇÃO DE RLS'
\echo '═══════════════════════════════════════════════════════════════'
\echo ''

-- Listar políticas criadas
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE tablename IN ('conversations_analytics', 'conversations_analytics_ai', 'etl_control')
ORDER BY tablename, policyname;

\echo ''
\echo '═══════════════════════════════════════════════════════════════'
\echo '  VERIFICAÇÃO DE RLS HABILITADO'
\echo '═══════════════════════════════════════════════════════════════'
\echo ''

SELECT
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('conversations_analytics', 'conversations_analytics_ai', 'etl_control')
ORDER BY tablename;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║              ✅ RLS CONFIGURADO COM SUCESSO!                   ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  🔒 Row-Level Security habilitado em 3 tabelas                 ║'
\echo '║  ✅ 12 políticas criadas (4 por tabela)                        ║'
\echo '║  ✅ Permissões concedidas aos roles                            ║'
\echo '║                                                                ║'
\echo '║  📋 Políticas por role:                                        ║'
\echo '║  • authenticated_users: Vê apenas próprio tenant               ║'
\echo '║  • admin_users: Vê e gerencia todos os tenants                 ║'
\echo '║  • etl_service: Insere/atualiza dados (bypass RLS)             ║'
\echo '║                                                                ║'
\echo '║  📋 PRÓXIMO PASSO:                                             ║'
\echo '║  Executar: 10_test_rls_analytics.sql                           ║'
\echo '║  (Testar isolamento com dados reais)                           ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''
