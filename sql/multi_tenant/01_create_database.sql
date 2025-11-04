-- ============================================================================
-- SCRIPT: 01_create_database.sql
-- Descrição: Cria o banco de dados geniai_analytics para sistema multi-tenant
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- IMPORTANTE: Este script deve ser executado como superuser (postgres)
-- Executar: psql -U postgres -f sql/multi_tenant/01_create_database.sql

-- ============================================================================
-- 1. CRIAR BANCO DE DADOS
-- ============================================================================

-- Verificar se banco já existe
SELECT 'Verificando se banco geniai_analytics já existe...' AS status;

-- Criar banco (se não existir)
-- Nota: CREATE DATABASE não suporta IF NOT EXISTS antes do PostgreSQL 9.3
-- Para evitar erro, use psql -U postgres -c "CREATE DATABASE geniai_analytics;" || true

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

-- ============================================================================
-- 2. CRIAR EXTENSÕES NECESSÁRIAS
-- ============================================================================

-- Conectar ao banco recém-criado
\c geniai_analytics

-- UUID para session IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
COMMENT ON EXTENSION "uuid-ossp" IS 'Geração de UUIDs para session tokens';

-- pgcrypto para funções de criptografia (futuro)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
COMMENT ON EXTENSION "pgcrypto" IS 'Funções criptográficas (hashing, encryption)';

-- dblink para migração de dados (será usado no script 04)
CREATE EXTENSION IF NOT EXISTS "dblink";
COMMENT ON EXTENSION "dblink" IS 'Conexão entre databases para migração de dados';

-- ============================================================================
-- 3. CRIAR ROLES (Usuários do PostgreSQL)
-- ============================================================================

-- Role para usuários autenticados (clientes)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated_users') THEN
        CREATE ROLE authenticated_users;
        COMMENT ON ROLE authenticated_users IS 'Role para clientes autenticados (acesso restrito ao próprio tenant)';
    END IF;
END
$$;

-- Role para administradores
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_users') THEN
        CREATE ROLE admin_users;
        COMMENT ON ROLE admin_users IS 'Role para administradores GeniAI (acesso irrestrito)';
    END IF;
END
$$;

-- Role para serviço ETL
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_service') THEN
        CREATE ROLE etl_service LOGIN PASSWORD 'change_me_in_production';
        COMMENT ON ROLE etl_service IS 'Role para pipeline ETL (bypass RLS para inserir dados de todos os tenants)';
    END IF;
END
$$;

-- ============================================================================
-- 4. CONFIGURAÇÕES DO BANCO
-- ============================================================================

-- Habilitar logging de queries lentas (> 1s)
ALTER DATABASE geniai_analytics SET log_min_duration_statement = 1000;

-- Timezone padrão
ALTER DATABASE geniai_analytics SET timezone = 'America/Sao_Paulo';

-- Locale para formatação de datas
ALTER DATABASE geniai_analytics SET lc_time = 'pt_BR.UTF-8';

-- ============================================================================
-- 5. CRIAR SCHEMA CUSTOMIZADO (opcional - vamos usar public)
-- ============================================================================

-- Garantir que schema public existe
CREATE SCHEMA IF NOT EXISTS public;
COMMENT ON SCHEMA public IS 'Schema padrão para tabelas multi-tenant';

-- Dar permissões ao owner
GRANT ALL ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO authenticated_users;
GRANT USAGE ON SCHEMA public TO admin_users;

-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

SELECT 'Banco de dados geniai_analytics criado com sucesso!' AS status;

-- Listar extensões instaladas
SELECT
    'Extensões instaladas:' AS info,
    extname AS extension,
    extversion AS version
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'dblink');

-- Listar roles criadas
SELECT
    'Roles criadas:' AS info,
    rolname AS role,
    CASE
        WHEN rolname = 'authenticated_users' THEN 'Clientes (RLS restrito)'
        WHEN rolname = 'admin_users' THEN 'Admins GeniAI (acesso total)'
        WHEN rolname = 'etl_service' THEN 'Pipeline ETL (bypass RLS)'
    END AS description
FROM pg_roles
WHERE rolname IN ('authenticated_users', 'admin_users', 'etl_service');

-- ============================================================================
-- PRÓXIMO PASSO
-- ============================================================================

-- Executar: psql -U postgres -d geniai_analytics -f sql/multi_tenant/02_create_schema.sql

-- ============================================================================
-- NOTAS DE SEGURANÇA
-- ============================================================================

-- 1. ALTERAR SENHA DO etl_service EM PRODUÇÃO!
--    ALTER ROLE etl_service WITH PASSWORD 'senha_forte_aqui';

-- 2. RESTRINGIR ACESSO POR IP no pg_hba.conf:
--    host geniai_analytics etl_service 127.0.0.1/32 md5

-- 3. HABILITAR SSL para conexões remotas:
--    ssl = on (postgresql.conf)
--    ssl_cert_file = 'server.crt'
--    ssl_key_file = 'server.key'

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
