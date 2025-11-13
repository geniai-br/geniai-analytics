-- ============================================================================
-- SCRIPT: 05_row_level_security.sql
-- Descrição: Implementa Row-Level Security (RLS) para isolamento multi-tenant
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/05_row_level_security.sql

\c geniai_analytics

-- ============================================================================
-- IMPORTANTE: O QUE É ROW-LEVEL SECURITY (RLS)?
-- ============================================================================

-- RLS é um mecanismo do PostgreSQL que filtra AUTOMATICAMENTE linhas de tabelas
-- baseado em políticas (policies) configuradas no banco de dados.
--
-- Benefícios:
-- 1. Segurança em nível de banco (não depende de código da aplicação)
-- 2. Impossível burlar via SQL injection
-- 3. Desenvolvedor pode esquecer WHERE e RLS ainda protege
-- 4. Performance otimizada (PostgreSQL aplica filtros no query planner)

-- ============================================================================
-- 1. HABILITAR RLS NAS TABELAS DE DADOS
-- ============================================================================

-- Conversations Analytics (principal)
ALTER TABLE conversations_analytics ENABLE ROW LEVEL SECURITY;

-- AI Analysis
ALTER TABLE conversas_analytics_ai ENABLE ROW LEVEL SECURITY;

-- ETL Control (apenas leitura para clientes)
ALTER TABLE etl_control ENABLE ROW LEVEL SECURITY;

-- Audit Logs (apenas admin pode ver)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Sessions (usuário só vê próprias sessões)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Tenants (clientes não veem outros tenants)
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Users (usuários só veem users do próprio tenant)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Inbox Mapping (clientes só veem próprios inboxes)
ALTER TABLE inbox_tenant_mapping ENABLE ROW LEVEL SECURITY;

-- Tenant Configs (clientes só veem própria config)
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;

SELECT 'RLS habilitado em todas as tabelas' AS status;

-- ============================================================================
-- 2. CRIAR FUNÇÕES AUXILIARES
-- ============================================================================

-- Função para obter tenant_id da sessão atual
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(
        current_setting('app.current_tenant_id', TRUE)::INTEGER,
        -1  -- Default: nenhum tenant (retorna vazio)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN -1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_current_tenant_id() IS
'Retorna tenant_id da sessão atual (configurado pela aplicação via SET app.current_tenant_id)';

-- Função para verificar se usuário é admin
CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN current_setting('app.current_user_role', TRUE) IN ('admin', 'super_admin');
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_admin_user() IS
'Retorna TRUE se role do usuário é admin ou super_admin';

-- Função para obter user_id da sessão
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(
        current_setting('app.current_user_id', TRUE)::INTEGER,
        -1
    );
EXCEPTION WHEN OTHERS THEN
    RETURN -1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_current_user_id() IS
'Retorna user_id da sessão atual';

-- ============================================================================
-- 3. POLÍTICAS PARA CONVERSATIONS_ANALYTICS
-- ============================================================================

-- Policy para CLIENTES: só veem conversas do próprio tenant
CREATE POLICY tenant_isolation_conversations_select
ON conversations_analytics
FOR SELECT
TO authenticated_users
USING (tenant_id = get_current_tenant_id());

-- Policy para ADMINS: veem todas as conversas
CREATE POLICY admin_all_conversations_select
ON conversations_analytics
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para INSERT (apenas ETL pode inserir)
CREATE POLICY etl_insert_conversations
ON conversations_analytics
FOR INSERT
TO etl_service
WITH CHECK (TRUE);

-- Policy para UPDATE (apenas ETL pode atualizar)
CREATE POLICY etl_update_conversations
ON conversations_analytics
FOR UPDATE
TO etl_service
USING (TRUE)
WITH CHECK (TRUE);

COMMENT ON POLICY tenant_isolation_conversations_select ON conversations_analytics IS
'Clientes só visualizam conversas do próprio tenant';

COMMENT ON POLICY admin_all_conversations_select ON conversations_analytics IS
'Admins visualizam todas as conversas de todos os tenants';

-- ============================================================================
-- 4. POLÍTICAS PARA CONVERSAS_ANALYTICS_AI
-- ============================================================================

-- Policy para CLIENTES: só veem análises de IA do próprio tenant
CREATE POLICY tenant_isolation_ai_select
ON conversas_analytics_ai
FOR SELECT
TO authenticated_users
USING (
    conversation_id IN (
        SELECT conversation_id
        FROM conversations_analytics
        WHERE tenant_id = get_current_tenant_id()
    )
);

-- Policy para ADMINS: veem todas as análises
CREATE POLICY admin_all_ai_select
ON conversas_analytics_ai
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para INSERT/UPDATE (apenas ETL e análise de IA)
CREATE POLICY etl_insert_ai
ON conversas_analytics_ai
FOR INSERT
TO etl_service
WITH CHECK (TRUE);

CREATE POLICY etl_update_ai
ON conversas_analytics_ai
FOR UPDATE
TO etl_service
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 5. POLÍTICAS PARA ETL_CONTROL
-- ============================================================================

-- Policy para CLIENTES: só veem ETL executions do próprio tenant
CREATE POLICY tenant_isolation_etl_select
ON etl_control
FOR SELECT
TO authenticated_users
USING (tenant_id = get_current_tenant_id() OR tenant_id IS NULL);

-- Policy para ADMINS: veem todos os ETL logs
CREATE POLICY admin_all_etl_select
ON etl_control
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para ETL service (pode fazer tudo)
CREATE POLICY etl_full_access
ON etl_control
FOR ALL
TO etl_service
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 6. POLÍTICAS PARA AUDIT_LOGS
-- ============================================================================

-- Policy para CLIENTES: não veem audit logs
-- (Sem policy = sem acesso)

-- Policy para ADMINS: veem todos os logs
CREATE POLICY admin_all_audit_logs
ON audit_logs
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para INSERT (qualquer authenticated user pode logar ações)
CREATE POLICY insert_audit_logs
ON audit_logs
FOR INSERT
TO authenticated_users, admin_users
WITH CHECK (TRUE);

-- ============================================================================
-- 7. POLÍTICAS PARA SESSIONS
-- ============================================================================

-- Policy para usuários: só veem próprias sessões
CREATE POLICY user_own_sessions
ON sessions
FOR SELECT
TO authenticated_users
USING (user_id = get_current_user_id());

-- Policy para ADMINS: veem todas as sessões
CREATE POLICY admin_all_sessions
ON sessions
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para INSERT/UPDATE/DELETE (próprias sessões)
CREATE POLICY user_manage_own_sessions
ON sessions
FOR ALL
TO authenticated_users
USING (user_id = get_current_user_id())
WITH CHECK (user_id = get_current_user_id());

-- Policy para ADMINS gerenciar sessões (ex: forçar logout)
CREATE POLICY admin_manage_all_sessions
ON sessions
FOR ALL
TO admin_users
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 8. POLÍTICAS PARA TENANTS
-- ============================================================================

-- Policy para CLIENTES: só veem próprio tenant
CREATE POLICY tenant_own_info
ON tenants
FOR SELECT
TO authenticated_users
USING (id = get_current_tenant_id());

-- Policy para ADMINS: veem todos os tenants
CREATE POLICY admin_all_tenants
ON tenants
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para ADMINS gerenciar tenants
CREATE POLICY admin_manage_tenants
ON tenants
FOR ALL
TO admin_users
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 9. POLÍTICAS PARA USERS
-- ============================================================================

-- Policy para CLIENTES: só veem usuários do próprio tenant
CREATE POLICY tenant_own_users
ON users
FOR SELECT
TO authenticated_users
USING (tenant_id = get_current_tenant_id());

-- Policy para ADMINS: veem todos os usuários
CREATE POLICY admin_all_users
ON users
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para ADMINS gerenciar usuários
CREATE POLICY admin_manage_users
ON users
FOR ALL
TO admin_users
USING (TRUE)
WITH CHECK (TRUE);

-- Policy para usuário atualizar próprio perfil
CREATE POLICY user_update_own_profile
ON users
FOR UPDATE
TO authenticated_users
USING (id = get_current_user_id())
WITH CHECK (id = get_current_user_id() AND tenant_id = get_current_tenant_id());

-- ============================================================================
-- 10. POLÍTICAS PARA INBOX_TENANT_MAPPING
-- ============================================================================

-- Policy para CLIENTES: só veem inboxes do próprio tenant
CREATE POLICY tenant_own_inboxes
ON inbox_tenant_mapping
FOR SELECT
TO authenticated_users
USING (tenant_id = get_current_tenant_id());

-- Policy para ADMINS: veem todos os inboxes
CREATE POLICY admin_all_inboxes
ON inbox_tenant_mapping
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para ADMINS gerenciar mapeamentos
CREATE POLICY admin_manage_inbox_mapping
ON inbox_tenant_mapping
FOR ALL
TO admin_users
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 11. POLÍTICAS PARA TENANT_CONFIGS
-- ============================================================================

-- Policy para CLIENTES: só veem própria config
CREATE POLICY tenant_own_config
ON tenant_configs
FOR SELECT
TO authenticated_users
USING (tenant_id = get_current_tenant_id());

-- Policy para ADMINS: veem todas as configs
CREATE POLICY admin_all_configs
ON tenant_configs
FOR SELECT
TO admin_users
USING (TRUE);

-- Policy para ADMINS gerenciar configs
CREATE POLICY admin_manage_configs
ON tenant_configs
FOR ALL
TO admin_users
USING (TRUE)
WITH CHECK (TRUE);

-- ============================================================================
-- 12. GRANTS - PERMISSÕES DE TABELA
-- ============================================================================

-- Authenticated Users (clientes)
GRANT SELECT ON conversations_analytics TO authenticated_users;
GRANT SELECT ON conversas_analytics_ai TO authenticated_users;
GRANT SELECT ON etl_control TO authenticated_users;
GRANT SELECT ON sessions TO authenticated_users;
GRANT UPDATE ON sessions TO authenticated_users;  -- Para renovar sessão
GRANT DELETE ON sessions TO authenticated_users;  -- Para logout
GRANT INSERT ON audit_logs TO authenticated_users;
GRANT SELECT ON tenants TO authenticated_users;
GRANT SELECT ON users TO authenticated_users;
GRANT UPDATE ON users TO authenticated_users;  -- Para atualizar próprio perfil
GRANT SELECT ON inbox_tenant_mapping TO authenticated_users;
GRANT SELECT ON tenant_configs TO authenticated_users;

-- Admin Users
GRANT ALL ON conversations_analytics TO admin_users;
GRANT ALL ON conversas_analytics_ai TO admin_users;
GRANT ALL ON etl_control TO admin_users;
GRANT ALL ON audit_logs TO admin_users;
GRANT ALL ON sessions TO admin_users;
GRANT ALL ON tenants TO admin_users;
GRANT ALL ON users TO admin_users;
GRANT ALL ON inbox_tenant_mapping TO admin_users;
GRANT ALL ON tenant_configs TO admin_users;

-- ETL Service (bypass RLS)
GRANT ALL ON conversations_analytics TO etl_service;
GRANT ALL ON conversas_analytics_ai TO etl_service;
GRANT ALL ON etl_control TO etl_service;
GRANT INSERT ON audit_logs TO etl_service;

-- Permissões em sequences (para INSERTs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO admin_users;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO etl_service;

-- ============================================================================
-- 13. FORÇAR RLS PARA SUPERUSER (SEGURANÇA EXTRA)
-- ============================================================================

-- Por padrão, superusers (postgres) bypassam RLS
-- Para maior segurança, podemos forçar RLS até para superuser:
-- (Comentado por padrão - descomentar em produção se desejado)

-- ALTER TABLE conversations_analytics FORCE ROW LEVEL SECURITY;
-- ALTER TABLE conversas_analytics_ai FORCE ROW LEVEL SECURITY;
-- ALTER TABLE etl_control FORCE ROW LEVEL SECURITY;
-- ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
-- ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
-- ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
-- ALTER TABLE users FORCE ROW LEVEL SECURITY;
-- ALTER TABLE inbox_tenant_mapping FORCE ROW LEVEL SECURITY;
-- ALTER TABLE tenant_configs FORCE ROW LEVEL SECURITY;

-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

SELECT 'Row-Level Security configurado com sucesso!' AS status;

-- Listar tabelas com RLS habilitado
SELECT
    '=== TABELAS COM RLS ===' AS section,
    schemaname,
    tablename,
    rowsecurity AS rls_enabled,
    CASE
        WHEN rowsecurity THEN '✅ Protegido'
        ELSE '❌ Desprotegido'
    END AS status
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
      'conversations_analytics',
      'conversas_analytics_ai',
      'etl_control',
      'audit_logs',
      'sessions',
      'tenants',
      'users',
      'inbox_tenant_mapping',
      'tenant_configs'
  )
ORDER BY tablename;

-- Listar policies criadas
SELECT
    '=== POLICIES CRIADAS ===' AS section,
    schemaname,
    tablename,
    policyname,
    CASE cmd
        WHEN 'r' THEN 'SELECT'
        WHEN 'w' THEN 'UPDATE'
        WHEN 'a' THEN 'INSERT'
        WHEN 'd' THEN 'DELETE'
        WHEN '*' THEN 'ALL'
    END AS operation,
    roles::text[]
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Contar policies por tabela
SELECT
    '=== POLICIES POR TABELA ===' AS section,
    tablename,
    COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

-- ============================================================================
-- INSTRUÇÕES PARA USO NA APLICAÇÃO
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║               ROW-LEVEL SECURITY CONFIGURADO                   ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ✅ RLS habilitado em todas as tabelas                         ║'
\echo '║  ✅ Policies criadas para clientes e admins                    ║'
\echo '║  ✅ Funções auxiliares implementadas                           ║'
\echo '║                                                                ║'
\echo '║  📋 COMO USAR NA APLICAÇÃO (Python):                           ║'
\echo '║                                                                ║'
\echo '║  # 1. Após autenticação, configurar sessão:                    ║'
\echo '║  conn.execute("SET app.current_tenant_id = %s", (tenant_id,))  ║'
\echo '║  conn.execute("SET app.current_user_id = %s", (user_id,))      ║'
\echo '║  conn.execute("SET app.current_user_role = %s", (role,))       ║'
\echo '║                                                                ║'
\echo '║  # 2. Definir ROLE do PostgreSQL:                              ║'
\echo '║  if role in ["admin", "super_admin"]:                          ║'
\echo '║      conn.execute("SET ROLE admin_users")                      ║'
\echo '║  else:                                                         ║'
\echo '║      conn.execute("SET ROLE authenticated_users")              ║'
\echo '║                                                                ║'
\echo '║  # 3. Queries são automaticamente filtradas!                   ║'
\echo '║  df = pd.read_sql("SELECT * FROM conversations_analytics", conn)║'
\echo '║  # Retorna APENAS dados do tenant_id configurado ✅            ║'
\echo '║                                                                ║'
\echo '║  ⚠️  IMPORTANTE:                                                ║'
\echo '║  - Sempre configurar app.current_tenant_id antes de queries    ║'
\echo '║  - Sempre configurar ROLE correto (admin_users ou authenticated)║'
\echo '║  - RLS protege mesmo se desenvolvedor esquecer WHERE!          ║'
\echo '║                                                                ║'
\echo '║  📋 Próximo passo:                                             ║'
\echo '║  - Executar 04_migrate_allpfit_data.sql (migrar dados)         ║'
\echo '║  - Implementar módulo de autenticação (src/multi_tenant/auth/) ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- TESTE MANUAL DE RLS (DESCOMENTAR PARA TESTAR)
-- ============================================================================

/*
-- Teste 1: Configurar como Tenant 1 (AllpFit)
SET app.current_tenant_id = 1;
SET ROLE authenticated_users;

SELECT COUNT(*) AS conversations_visible
FROM conversations_analytics;
-- Deve retornar apenas conversas do tenant_id = 1

-- Teste 2: Trocar para Tenant 999 (inexistente)
SET app.current_tenant_id = 999;

SELECT COUNT(*) AS conversations_visible
FROM conversations_analytics;
-- Deve retornar 0 (nenhuma conversa)

-- Teste 3: Admin vê tudo
SET ROLE admin_users;

SELECT COUNT(*) AS conversations_visible
FROM conversations_analytics;
-- Deve retornar TODAS as conversas independente de tenant_id

-- Reset
RESET ROLE;
RESET app.current_tenant_id;
*/

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
