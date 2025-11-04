-- ============================================================================
-- SCRIPT: 06_test_isolation.sql
-- Descrição: Testa isolamento de dados entre tenants (RLS)
-- Autor: GeniAI
-- Data: 2025-11-04
-- ============================================================================

-- EXECUTAR CONECTADO AO BANCO geniai_analytics
-- psql -U postgres -d geniai_analytics -f sql/multi_tenant/06_test_isolation.sql

\c geniai_analytics

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║          TESTES DE ISOLAMENTO MULTI-TENANT (RLS)               ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  Este script testa se Row-Level Security está funcionando      ║'
\echo '║  corretamente e garantindo isolamento entre tenants.           ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- SETUP: Criar dados de teste
-- ============================================================================

\echo '=== CRIANDO DADOS DE TESTE ==='

-- Criar tenant de teste (ID 99)
INSERT INTO tenants (id, name, slug, inbox_ids, status, plan)
VALUES (99, 'Tenant Teste', 'tenant-teste', '{999}', 'active', 'basic')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    slug = EXCLUDED.slug,
    inbox_ids = EXCLUDED.inbox_ids;

-- Criar conversas de teste
-- Tenant 1 (AllpFit) - 3 conversas
INSERT INTO conversations_analytics (
    conversation_id, tenant_id, inbox_id, contact_name, status,
    conversation_created_at, conversation_date
)
VALUES
    (9001, 1, 1, 'Teste Cliente AllpFit 1', 0, NOW(), CURRENT_DATE),
    (9002, 1, 1, 'Teste Cliente AllpFit 2', 1, NOW(), CURRENT_DATE),
    (9003, 1, 2, 'Teste Cliente AllpFit 3', 0, NOW(), CURRENT_DATE)
ON CONFLICT (conversation_id) DO NOTHING;

-- Tenant 99 (Teste) - 2 conversas
INSERT INTO conversations_analytics (
    conversation_id, tenant_id, inbox_id, contact_name, status,
    conversation_created_at, conversation_date
)
VALUES
    (9099, 99, 999, 'Teste Cliente Tenant99 1', 0, NOW(), CURRENT_DATE),
    (9100, 99, 999, 'Teste Cliente Tenant99 2', 1, NOW(), CURRENT_DATE)
ON CONFLICT (conversation_id) DO NOTHING;

\echo '✅ Dados de teste criados'

-- ============================================================================
-- TESTE 1: Tenant Isolation (Cliente vê apenas próprios dados)
-- ============================================================================

\echo ''
\echo '=== TESTE 1: ISOLAMENTO DE TENANT (CLIENTES) ==='

-- Configurar como Tenant 1 (AllpFit)
SET app.current_tenant_id = 1;
SET app.current_user_role = 'client';
SET ROLE authenticated_users;

\echo '  Configurado como: Tenant 1 (AllpFit), Role: authenticated_users'

-- Query sem WHERE (RLS deve filtrar automaticamente)
SELECT
    '  Teste 1.1: SELECT sem WHERE' AS test,
    COUNT(*) AS conversations_visible,
    CASE
        WHEN COUNT(*) >= 3 THEN '✅ OK (vendo dados do tenant 1)'
        ELSE '❌ FALHOU (deveria ver >= 3 conversas)'
    END AS result
FROM conversations_analytics
WHERE conversation_id >= 9000;  -- Apenas dados de teste

-- Verificar que NÃO vê dados de outros tenants
SELECT
    '  Teste 1.2: Não vê outros tenants' AS test,
    COUNT(*) AS conversations_other_tenant,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ OK (não vê tenant 99)'
        ELSE '❌ FALHOU (está vendo dados de outro tenant!)'
    END AS result
FROM conversations_analytics
WHERE tenant_id = 99 AND conversation_id >= 9000;

-- Trocar para Tenant 99
SET app.current_tenant_id = 99;

\echo '  Configurado como: Tenant 99, Role: authenticated_users'

SELECT
    '  Teste 1.3: Tenant 99 vê próprios dados' AS test,
    COUNT(*) AS conversations_visible,
    CASE
        WHEN COUNT(*) >= 2 THEN '✅ OK (vendo dados do tenant 99)'
        ELSE '❌ FALHOU (deveria ver >= 2 conversas)'
    END AS result
FROM conversations_analytics
WHERE conversation_id >= 9000;

-- Verificar que Tenant 99 NÃO vê Tenant 1
SELECT
    '  Teste 1.4: Tenant 99 não vê Tenant 1' AS test,
    COUNT(*) AS conversations_other_tenant,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ OK (não vê tenant 1)'
        ELSE '❌ FALHOU (está vendo dados de outro tenant!)'
    END AS result
FROM conversations_analytics
WHERE tenant_id = 1 AND conversation_id >= 9000;

-- ============================================================================
-- TESTE 2: Admin Access (Admin vê todos os dados)
-- ============================================================================

\echo ''
\echo '=== TESTE 2: ACESSO ADMIN (VÊ TODOS OS TENANTS) ==='

SET ROLE admin_users;
SET app.current_user_role = 'super_admin';

\echo '  Configurado como: Admin, Role: admin_users'

-- Admin deve ver TODOS os dados
SELECT
    '  Teste 2.1: Admin vê todos os tenants' AS test,
    COUNT(*) AS total_conversations,
    CASE
        WHEN COUNT(*) >= 5 THEN '✅ OK (admin vê todos os dados)'
        ELSE '❌ FALHOU (admin deveria ver todos os dados)'
    END AS result
FROM conversations_analytics
WHERE conversation_id >= 9000;

-- Admin pode filtrar por tenant específico
SELECT
    '  Teste 2.2: Admin filtra Tenant 1' AS test,
    COUNT(*) AS tenant1_conversations,
    CASE
        WHEN COUNT(*) >= 3 THEN '✅ OK (filtro funciona para admin)'
        ELSE '❌ FALHOU (filtro não funcionou)'
    END AS result
FROM conversations_analytics
WHERE tenant_id = 1 AND conversation_id >= 9000;

SELECT
    '  Teste 2.3: Admin filtra Tenant 99' AS test,
    COUNT(*) AS tenant99_conversations,
    CASE
        WHEN COUNT(*) >= 2 THEN '✅ OK (filtro funciona para admin)'
        ELSE '❌ FALHOU (filtro não funcionou)'
    END AS result
FROM conversations_analytics
WHERE tenant_id = 99 AND conversation_id >= 9000;

-- ============================================================================
-- TESTE 3: Tenant não existente (deve retornar vazio)
-- ============================================================================

\echo ''
\echo '=== TESTE 3: TENANT INEXISTENTE ==='

SET ROLE authenticated_users;
SET app.current_tenant_id = 999999;  -- Tenant que não existe

\echo '  Configurado como: Tenant 999999 (inexistente), Role: authenticated_users'

SELECT
    '  Teste 3.1: Tenant inexistente retorna vazio' AS test,
    COUNT(*) AS conversations_visible,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ OK (nenhum dado visível)'
        ELSE '❌ FALHOU (não deveria ver dados!)'
    END AS result
FROM conversations_analytics;

-- ============================================================================
-- TESTE 4: Session variables não configuradas
-- ============================================================================

\echo ''
\echo '=== TESTE 4: SEM SESSION VARIABLES ==='

-- Reset session variables
RESET app.current_tenant_id;
RESET app.current_user_role;

\echo '  Session variables resetadas (sem tenant_id)'

SELECT
    '  Teste 4.1: Sem tenant_id retorna vazio' AS test,
    COUNT(*) AS conversations_visible,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ OK (sem acesso)'
        ELSE '❌ FALHOU (não deveria ver dados sem tenant_id!)'
    END AS result
FROM conversations_analytics
WHERE conversation_id >= 9000;

-- ============================================================================
-- TESTE 5: Outras tabelas (AI, ETL Control, etc)
-- ============================================================================

\echo ''
\echo '=== TESTE 5: OUTRAS TABELAS (AI Analysis) ==='

-- Inserir dados de teste AI
INSERT INTO conversas_analytics_ai (
    conversation_id, tenant_id, analise_ia, sugestao_disparo,
    probabilidade_conversao, modelo_ia, analisado_em
)
VALUES
    (9001, 1, 'Teste análise IA 1', 'Sugestão 1', 3, 'gpt-4', NOW()),
    (9099, 99, 'Teste análise IA 99', 'Sugestão 99', 4, 'gpt-4', NOW())
ON CONFLICT (conversation_id) DO NOTHING;

-- Configurar como Tenant 1
SET app.current_tenant_id = 1;
SET ROLE authenticated_users;

SELECT
    '  Teste 5.1: AI analysis - Tenant 1' AS test,
    COUNT(*) AS ai_analysis_visible,
    CASE
        WHEN COUNT(*) = 1 THEN '✅ OK (vê apenas própria análise)'
        ELSE '❌ FALHOU (isolamento de AI não funcionou)'
    END AS result
FROM conversas_analytics_ai
WHERE conversation_id >= 9000;

-- Verificar que não vê Tenant 99
SELECT
    '  Teste 5.2: AI analysis - Não vê Tenant 99' AS test,
    COUNT(*) AS ai_analysis_other,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ OK (não vê outros tenants)'
        ELSE '❌ FALHOU (está vendo AI de outro tenant!)'
    END AS result
FROM conversas_analytics_ai
WHERE conversation_id = 9099;

-- ============================================================================
-- TESTE 6: Tabelas de configuração (tenants, users, etc)
-- ============================================================================

\echo ''
\echo '=== TESTE 6: TABELAS DE CONFIGURAÇÃO ==='

-- Tenant só vê próprio registro
SET app.current_tenant_id = 1;
SET ROLE authenticated_users;

SELECT
    '  Teste 6.1: Tenants - vê apenas próprio' AS test,
    COUNT(*) AS tenants_visible,
    CASE
        WHEN COUNT(*) = 1 AND MAX(id) = 1 THEN '✅ OK (vê apenas tenant 1)'
        ELSE '❌ FALHOU (vendo outros tenants)'
    END AS result
FROM tenants;

-- Admin vê todos os tenants
SET ROLE admin_users;

SELECT
    '  Teste 6.2: Tenants - Admin vê todos' AS test,
    COUNT(*) AS tenants_visible,
    CASE
        WHEN COUNT(*) >= 3 THEN '✅ OK (admin vê todos)'
        ELSE '❌ FALHOU (admin deveria ver todos)'
    END AS result
FROM tenants;

-- ============================================================================
-- LIMPEZA: Remover dados de teste
-- ============================================================================

\echo ''
\echo '=== LIMPANDO DADOS DE TESTE ==='

-- Reset role para ter permissão de DELETE
RESET ROLE;

-- Deletar conversas de teste
DELETE FROM conversations_analytics WHERE conversation_id >= 9000;
DELETE FROM conversas_analytics_ai WHERE conversation_id >= 9000;
DELETE FROM tenants WHERE id = 99;

\echo '✅ Dados de teste removidos'

-- Reset session
RESET app.current_tenant_id;
RESET app.current_user_role;
RESET ROLE;

-- ============================================================================
-- SUMÁRIO DOS TESTES
-- ============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║                    SUMÁRIO DOS TESTES                          ║'
\echo '╠════════════════════════════════════════════════════════════════╣'
\echo '║                                                                ║'
\echo '║  ✅ Teste 1: Isolamento de Tenant (clientes)                   ║'
\echo '║     - Clientes veem apenas próprios dados                      ║'
\echo '║     - Queries sem WHERE são automaticamente filtradas          ║'
\echo '║                                                                ║'
\echo '║  ✅ Teste 2: Acesso Admin                                      ║'
\echo '║     - Admins veem dados de todos os tenants                    ║'
\echo '║     - Admins podem filtrar por tenant específico               ║'
\echo '║                                                                ║'
\echo '║  ✅ Teste 3: Tenant Inexistente                                ║'
\echo '║     - Tenant que não existe retorna vazio                      ║'
\echo '║                                                                ║'
\echo '║  ✅ Teste 4: Sem Session Variables                             ║'
\echo '║     - Sem tenant_id configurado = sem acesso                   ║'
\echo '║                                                                ║'
\echo '║  ✅ Teste 5: Outras Tabelas (AI Analysis)                      ║'
\echo '║     - RLS funciona em todas as tabelas relacionadas            ║'
\echo '║                                                                ║'
\echo '║  ✅ Teste 6: Tabelas de Configuração                           ║'
\echo '║     - Clientes veem apenas próprio tenant                      ║'
\echo '║     - Admins veem todos os tenants                             ║'
\echo '║                                                                ║'
\echo '║  📋 CONCLUSÃO:                                                 ║'
\echo '║  Se todos os testes acima mostraram ✅ OK, então:              ║'
\echo '║  - Row-Level Security está funcionando corretamente            ║'
\echo '║  - Isolamento entre tenants está garantido                     ║'
\echo '║  - Sistema está pronto para uso multi-tenant                   ║'
\echo '║                                                                ║'
\echo '║  ⚠️  Se algum teste mostrou ❌ FALHOU:                         ║'
\echo '║  - Revisar políticas RLS (05_row_level_security.sql)           ║'
\echo '║  - Verificar se RLS está habilitado nas tabelas                ║'
\echo '║  - Verificar se session variables estão sendo configuradas     ║'
\echo '║                                                                ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================