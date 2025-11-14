#!/bin/bash
# ============================================================================
# Script: Setup Completo do Banco Multi-Tenant
# Executa via superuser (postgres)
# ============================================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        SETUP COMPLETO - BANCO MULTI-TENANT GENIAI              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Executar como superuser
sudo -u postgres psql <<'EOF'

-- ============================================================================
-- 1. CRIAR BANCO DE DADOS
-- ============================================================================

\echo '📦 Criando banco geniai_analytics...'

-- Dropar se já existir (cuidado!)
-- DROP DATABASE IF EXISTS geniai_analytics;

CREATE DATABASE geniai_analytics
WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

COMMENT ON DATABASE geniai_analytics IS
'Banco de dados multi-tenant para GeniAI Analytics Platform.
Cada cliente (tenant) possui dados isolados via Row-Level Security (RLS).';

\echo '✅ Banco criado!'
\echo ''

-- ============================================================================
-- 2. CONECTAR AO BANCO E INSTALAR EXTENSÕES
-- ============================================================================

\c geniai_analytics

\echo '🔌 Instalando extensões...'

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "dblink";

\echo '✅ Extensões instaladas!'
\echo ''

-- ============================================================================
-- 3. CRIAR ROLES
-- ============================================================================

\echo '👥 Criando roles...'

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated_users') THEN
        CREATE ROLE authenticated_users;
        RAISE NOTICE 'Role authenticated_users criada';
    ELSE
        RAISE NOTICE 'Role authenticated_users já existe';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_users') THEN
        CREATE ROLE admin_users;
        RAISE NOTICE 'Role admin_users criada';
    ELSE
        RAISE NOTICE 'Role admin_users já existe';
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_service') THEN
        CREATE ROLE etl_service LOGIN PASSWORD 'ETL_Service_2024@Secure';
        RAISE NOTICE 'Role etl_service criada';
    ELSE
        RAISE NOTICE 'Role etl_service já existe';
    END IF;
END
$$;

COMMENT ON ROLE authenticated_users IS 'Role para clientes autenticados (acesso restrito ao próprio tenant)';
COMMENT ON ROLE admin_users IS 'Role para administradores GeniAI (acesso irrestrito)';
COMMENT ON ROLE etl_service IS 'Role para pipeline ETL (bypass RLS)';

\echo '✅ Roles criadas!'
\echo ''

-- ============================================================================
-- 4. DAR PERMISSÕES AO USUÁRIO integracao_user
-- ============================================================================

\echo '🔑 Dando permissões ao integracao_user...'

GRANT ALL PRIVILEGES ON DATABASE geniai_analytics TO integracao_user;
GRANT USAGE ON SCHEMA public TO integracao_user;
GRANT ALL ON SCHEMA public TO integracao_user;

-- Permitir criar objetos no schema public
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO integracao_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO integracao_user;

\echo '✅ Permissões concedidas!'
\echo ''

-- ============================================================================
-- 5. CONFIGURAÇÕES DO BANCO
-- ============================================================================

\echo '⚙️  Configurando banco...'

ALTER DATABASE geniai_analytics SET log_min_duration_statement = 1000;
ALTER DATABASE geniai_analytics SET timezone = 'America/Sao_Paulo';
ALTER DATABASE geniai_analytics SET lc_time = 'pt_BR.UTF-8';

\echo '✅ Configurações aplicadas!'
\echo ''

-- ============================================================================
-- 6. VERIFICAÇÃO FINAL
-- ============================================================================

\echo '📊 VERIFICAÇÃO FINAL:'
\echo ''

-- Extensões
SELECT
    '  Extensão: ' || extname || ' v' || extversion AS status
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'dblink')
ORDER BY extname;

-- Roles
SELECT
    '  Role: ' || rolname AS status
FROM pg_roles
WHERE rolname IN ('authenticated_users', 'admin_users', 'etl_service')
ORDER BY rolname;

-- Database info
SELECT
    '  Owner: ' || pg_catalog.pg_get_userbyid(d.datdba) AS status
FROM pg_database d
WHERE d.datname = 'geniai_analytics';

EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ SETUP COMPLETO!                            ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  ✅ Database geniai_analytics criado                           ║"
echo "║  ✅ Extensões instaladas (uuid-ossp, pgcrypto, dblink)         ║"
echo "║  ✅ Roles criadas (authenticated_users, admin_users, etl)      ║"
echo "║  ✅ Permissões concedidas ao integracao_user                   ║"
echo "║                                                                ║"
echo "║  📋 PRÓXIMO PASSO:                                             ║"
echo "║  Executar: sql/multi_tenant/02_create_schema.sql               ║"
echo "║                                                                ║"
echo "║  PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql \\                ║"
echo "║    -h localhost -p 5432 -U integracao_user \\                  ║"
echo "║    -d geniai_analytics \\                                       ║"
echo "║    -f sql/multi_tenant/02_create_schema.sql                    ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
