-- ============================================================================
-- FASE 10: Permissões para tabelas de Campanhas
-- ============================================================================
-- Descrição: Adiciona GRANTs necessários para as tabelas campaigns,
--            campaign_leads e campaign_exports
--
-- Este script deve ser executado APÓS o 12_create_campaigns_tables.sql
--
-- Autor: Isaac (via Claude Code)
-- Data: 2025-11-26
-- ============================================================================

-- Verificar conexão
SELECT current_database(), current_user, now() as execution_time;

-- ============================================================================
-- 1. GRANTS PARA authenticated_users (usuários autenticados do dashboard)
-- ============================================================================

-- Tabela: campaigns
GRANT SELECT ON campaigns TO authenticated_users;
GRANT INSERT ON campaigns TO authenticated_users;
GRANT UPDATE ON campaigns TO authenticated_users;
GRANT DELETE ON campaigns TO authenticated_users;

-- Tabela: campaign_leads
GRANT SELECT ON campaign_leads TO authenticated_users;
GRANT INSERT ON campaign_leads TO authenticated_users;
GRANT UPDATE ON campaign_leads TO authenticated_users;
GRANT DELETE ON campaign_leads TO authenticated_users;

-- Tabela: campaign_exports
GRANT SELECT ON campaign_exports TO authenticated_users;
GRANT INSERT ON campaign_exports TO authenticated_users;

-- Sequences (para INSERT com SERIAL)
GRANT USAGE, SELECT ON SEQUENCE campaigns_id_seq TO authenticated_users;
GRANT USAGE, SELECT ON SEQUENCE campaign_leads_id_seq TO authenticated_users;
GRANT USAGE, SELECT ON SEQUENCE campaign_exports_id_seq TO authenticated_users;

-- ============================================================================
-- 2. GRANTS PARA admin_users (admins do sistema)
-- ============================================================================

GRANT ALL ON campaigns TO admin_users;
GRANT ALL ON campaign_leads TO admin_users;
GRANT ALL ON campaign_exports TO admin_users;

-- Sequences
GRANT USAGE, SELECT ON SEQUENCE campaigns_id_seq TO admin_users;
GRANT USAGE, SELECT ON SEQUENCE campaign_leads_id_seq TO admin_users;
GRANT USAGE, SELECT ON SEQUENCE campaign_exports_id_seq TO admin_users;

-- ============================================================================
-- 3. GRANTS PARA etl_service (serviço de ETL para processar leads)
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON campaigns TO etl_service;
GRANT SELECT, INSERT, UPDATE ON campaign_leads TO etl_service;
GRANT SELECT, INSERT ON campaign_exports TO etl_service;

-- Sequences
GRANT USAGE, SELECT ON SEQUENCE campaigns_id_seq TO etl_service;
GRANT USAGE, SELECT ON SEQUENCE campaign_leads_id_seq TO etl_service;
GRANT USAGE, SELECT ON SEQUENCE campaign_exports_id_seq TO etl_service;

-- ============================================================================
-- 4. VERIFICAÇÃO
-- ============================================================================

-- Verificar grants aplicados
SELECT
    grantee,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE table_name IN ('campaigns', 'campaign_leads', 'campaign_exports')
AND grantee IN ('authenticated_users', 'admin_users', 'etl_service')
ORDER BY table_name, grantee, privilege_type;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
-- Para executar:
-- psql -U johan_geniai -d geniai_analytics -f sql/12b_grant_campaigns_permissions.sql
-- ============================================================================