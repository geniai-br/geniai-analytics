# 🗄️ DOCUMENTAÇÃO DO BANCO DE DADOS - geniai_analytics

> **Banco:** `geniai_analytics`
> **Host:** localhost
> **User:** isaac
> **Tipo:** PostgreSQL (Multi-Tenant com Row-Level Security)
> **Última Atualização:** 2025-11-05 (Fase 1 Completa)

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Credenciais de Acesso](#credenciais-de-acesso)
3. [Estrutura do Banco](#estrutura-do-banco)
4. [Tabelas Principais](#tabelas-principais)
5. [Usuários e Tenants](#usuários-e-tenants)
6. [Row-Level Security (RLS)](#row-level-security-rls)
7. [Queries Úteis](#queries-úteis)
8. [Dados de Teste](#dados-de-teste)

---

## 🎯 VISÃO GERAL

### Propósito
Banco de dados centralizado para o sistema multi-tenant da GeniAI, onde:
- **1 banco** gerencia múltiplos clientes (tenants)
- **Isolamento lógico** via Row-Level Security (RLS)
- **Segregação por tenant_id** em todas as tabelas de dados

### Arquitetura
```
┌──────────────────────────────────────────┐
│      DATABASE: geniai_analytics          │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────────┐    │
│  │  AUTENTICAÇÃO & CONTROLE        │    │
│  │  • tenants                      │    │
│  │  • users                        │    │
│  │  • sessions                     │    │
│  │  • tenant_configs               │    │
│  │  • audit_logs                   │    │
│  └─────────────────────────────────┘    │
│                                          │
│  ┌─────────────────────────────────┐    │
│  │  DADOS DE ANALYTICS             │    │
│  │  • conversations_analytics      │    │
│  │  • conversations_analytics_ai   │    │
│  │  • etl_control                  │    │
│  │  • inbox_tenant_mapping         │    │
│  └─────────────────────────────────┘    │
│                                          │
│  🔒 Row-Level Security (RLS)            │
│     31+ políticas ativas                │
└──────────────────────────────────────────┘
```

---

## 🔐 CREDENCIAIS DE ACESSO

### Conexão PostgreSQL
```bash
Host: localhost
Port: 5432
Database: geniai_analytics
User: isaac
Password: AllpFit2024@Analytics
```

### String de Conexão
```python
# SQLAlchemy
DATABASE_URL = "postgresql://isaac:AllpFit2024@Analytics@localhost:5432/geniai_analytics"

# psql CLI
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics
```

### Variável de Ambiente (.env)
```bash
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=geniai_analytics
LOCAL_DB_USER=isaac
LOCAL_DB_PASSWORD=AllpFit2024@Analytics
```

---

## 📊 ESTRUTURA DO BANCO

### Lista de Tabelas (9 tabelas)
```sql
-- Ver todas as tabelas
\dt

 Schema |            Name            | Type  |      Owner
--------+----------------------------+-------+-----------------
 public | audit_logs                 | table | integracao_user
 public | conversations_analytics    | table | integracao_user
 public | conversations_analytics_ai | table | integracao_user
 public | etl_control                | table | integracao_user
 public | inbox_tenant_mapping       | table | integracao_user
 public | sessions                   | table | integracao_user
 public | tenant_configs             | table | integracao_user
 public | tenants                    | table | integracao_user
 public | users                      | table | integracao_user
```

### Categorias
1. **Autenticação:** tenants, users, sessions
2. **Configuração:** tenant_configs, inbox_tenant_mapping
3. **Dados:** conversations_analytics, conversations_analytics_ai
4. **Controle:** etl_control, audit_logs

---

## 🏢 TABELAS PRINCIPAIS

### 1. `tenants` - Clientes da GeniAI

**Descrição:** Cadastro de todos os clientes (tenants) que usam a plataforma.

```sql
CREATE TABLE tenants (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(255) NOT NULL,           -- Nome do cliente
    slug              VARCHAR(100) UNIQUE NOT NULL,    -- URL slug
    inbox_ids         INTEGER[] NOT NULL,              -- IDs do Chatwoot
    account_id        INTEGER,                         -- Conta no Chatwoot
    status            VARCHAR(20) DEFAULT 'active',    -- active, suspended, cancelled
    plan              VARCHAR(50) DEFAULT 'basic',     -- basic, pro, enterprise
    max_users         INTEGER DEFAULT 10,              -- Limite de usuários
    max_inboxes       INTEGER DEFAULT 5,               -- Limite de inboxes
    features          JSONB DEFAULT '{}',              -- Features habilitadas
    metadata          JSONB DEFAULT '{}',              -- Metadados customizados
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    deleted_at        TIMESTAMP                        -- Soft delete
);
```

**Campos Importantes:**
- `id`: 0 = GeniAI Admin, 1+ = Clientes
- `slug`: Usado em URLs (ex: allpfit.geniai.com.br)
- `inbox_ids`: Array de inboxes do Chatwoot pertencentes ao tenant
- `status`: Controla se tenant está ativo

**Índices:**
- `idx_tenants_slug` - Busca rápida por slug
- `idx_tenants_status` - Filtrar tenants ativos

---

### 2. `users` - Usuários do Sistema

**Descrição:** Todos os usuários (admins GeniAI + clientes).

```sql
CREATE TABLE users (
    id                    SERIAL PRIMARY KEY,
    tenant_id             INTEGER NOT NULL REFERENCES tenants(id),
    email                 VARCHAR(255) UNIQUE NOT NULL,
    password_hash         VARCHAR(255) NOT NULL,      -- bcrypt hash
    full_name             VARCHAR(255) NOT NULL,
    avatar_url            TEXT,
    phone                 VARCHAR(50),
    role                  VARCHAR(20) DEFAULT 'client', -- super_admin, admin, client
    permissions           JSONB DEFAULT '{}',
    is_active             BOOLEAN DEFAULT TRUE,
    email_verified        BOOLEAN DEFAULT FALSE,
    email_verified_at     TIMESTAMP,
    last_login            TIMESTAMP,
    last_login_ip         INET,
    login_count           INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until          TIMESTAMP,
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW(),
    deleted_at            TIMESTAMP                    -- Soft delete
);
```

**Roles (Hierarquia):**
1. `super_admin` - Administrador GeniAI (acesso total)
2. `admin` - Administrador de Tenant ou Suporte GeniAI
3. `client` - Usuário cliente (apenas leitura)

**Campos Importantes:**
- `tenant_id`: Liga usuário ao tenant (0 = GeniAI)
- `password_hash`: Hash bcrypt (cost factor 12)
- `role`: Define permissões
- `is_active`: Controla acesso

**Índices:**
- `users_email_unique` - Email único
- `idx_users_tenant_id` - Buscar usuários por tenant
- `idx_users_role` - Filtrar por role
- `idx_users_active` - Apenas usuários ativos

---

### 3. `sessions` - Controle de Sessões

**Descrição:** Sessões ativas de login (Streamlit session management).

```sql
CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
    ip_address  INET,
    user_agent  TEXT,
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

**Uso:**
- Cada login cria uma nova sessão
- `expires_at`: Expiração (padrão: 24h)
- `id`: UUID armazenado em `st.session_state`

**Índices:**
- `idx_sessions_user_id` - Buscar sessões de um usuário
- `idx_sessions_expires` - Limpar sessões expiradas

---

### 4. `conversations_analytics` - Dados de Conversas

**Descrição:** Dados das conversas do Chatwoot (sincronizados via ETL).

```sql
CREATE TABLE conversations_analytics (
    id                       SERIAL PRIMARY KEY,
    tenant_id                INTEGER NOT NULL REFERENCES tenants(id), -- 🔑 Multi-tenant
    conversation_id          BIGINT NOT NULL,
    conversation_display_id  INTEGER,
    inbox_id                 INTEGER,
    inbox_name               VARCHAR(255),
    contact_id               BIGINT,
    contact_name             VARCHAR(255),
    contact_phone            VARCHAR(50),
    contact_email            VARCHAR(255),

    -- Timestamps
    conversation_created_at  TIMESTAMP,
    conversation_updated_at  TIMESTAMP,
    conversation_date        DATE,
    first_message_at         TIMESTAMP,
    last_message_at          TIMESTAMP,

    -- Métricas
    total_messages           INTEGER,
    contact_messages         INTEGER,
    agent_messages           INTEGER,
    bot_messages             INTEGER,
    human_messages           INTEGER,

    -- Status e classificação
    conversation_status      VARCHAR(50),
    conversation_label       TEXT,
    is_lead                  BOOLEAN DEFAULT FALSE,
    visit_scheduled          BOOLEAN DEFAULT FALSE,
    crm_converted            BOOLEAN DEFAULT FALSE,

    -- Análise de IA (se disponível)
    ai_analysis_status       VARCHAR(50),
    ai_probability_label     VARCHAR(50),
    ai_probability_score     NUMERIC(5,2),

    -- Controle
    synced_at                TIMESTAMP DEFAULT NOW(),
    created_at               TIMESTAMP DEFAULT NOW(),
    updated_at               TIMESTAMP DEFAULT NOW()
);
```

**Campos Críticos:**
- `tenant_id`: 🔑 Campo que separa dados entre tenants
- `conversation_id`: ID único da conversa no Chatwoot
- `inbox_id`: Pertence a qual inbox
- `is_lead`: Se é um lead qualificado
- `visit_scheduled`: Se agendou visita
- `crm_converted`: Se converteu no CRM

**Índices Importantes:**
- `idx_conversations_tenant_id` - 🔥 Filtro multi-tenant
- `idx_conversations_tenant_date` - Queries por período
- `idx_conversations_inbox` - Por inbox
- `idx_conversations_is_lead` - Filtrar leads

**⚠️ Status Atual:** Tabela VAZIA (será populada na Fase 3 - ETL)

---

### 5. `inbox_tenant_mapping` - Mapeamento Inbox → Tenant

**Descrição:** Relaciona inboxes do Chatwoot com tenants.

```sql
CREATE TABLE inbox_tenant_mapping (
    inbox_id    INTEGER PRIMARY KEY,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
    inbox_name  VARCHAR(255),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

**Uso:**
- ETL usa para saber qual tenant pertence cada inbox
- Permite que um tenant tenha múltiplos inboxes

**Exemplo:**
```sql
INSERT INTO inbox_tenant_mapping VALUES
(14, 1, 'AllpFit WhatsApp', TRUE),
(61, 1, 'AllpFit Instagram', TRUE),
(102, 2, 'Academia XYZ WhatsApp', TRUE);
```

**⚠️ Status Atual:** Tabela VAZIA (será populada na Fase 3)

---

### 6. `tenant_configs` - Configurações por Tenant

**Descrição:** Personalização visual e funcional de cada tenant.

```sql
CREATE TABLE tenant_configs (
    tenant_id         INTEGER PRIMARY KEY REFERENCES tenants(id),
    logo_url          TEXT,                          -- URL do logo
    primary_color     VARCHAR(7) DEFAULT '#1E90FF',  -- Cor primária (hex)
    secondary_color   VARCHAR(7) DEFAULT '#FF8C00',  -- Cor secundária
    custom_css        TEXT,                          -- CSS customizado
    features          JSONB DEFAULT '{}',            -- Features específicas
    dashboard_config  JSONB DEFAULT '{}',            -- Config do dashboard
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);
```

**Uso:**
- Personalizar cores do dashboard por cliente
- Habilitar/desabilitar features específicas
- Logo customizado

---

### 7. `etl_control` - Controle do ETL

**Descrição:** Log de execuções do ETL multi-tenant.

```sql
CREATE TABLE etl_control (
    id                SERIAL PRIMARY KEY,
    tenant_id         INTEGER REFERENCES tenants(id),  -- NULL = todos
    execution_type    VARCHAR(50),                     -- full, incremental
    status            VARCHAR(20),                     -- running, success, error
    watermark_start   TIMESTAMP,
    watermark_end     TIMESTAMP,
    records_extracted INTEGER,
    records_inserted  INTEGER,
    records_updated   INTEGER,
    error_message     TEXT,
    started_at        TIMESTAMP DEFAULT NOW(),
    finished_at       TIMESTAMP
);
```

**Uso:**
- Controla watermark (último sync) por tenant
- Log de erros do ETL
- Métricas de cada execução

---

### 8. `audit_logs` - Auditoria

**Descrição:** Log de todas as ações importantes no sistema.

```sql
CREATE TABLE audit_logs (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(id),
    tenant_id    INTEGER REFERENCES tenants(id),
    action       VARCHAR(100),           -- create_user, delete_tenant, etc
    entity_type  VARCHAR(50),            -- user, tenant, config
    entity_id    INTEGER,
    old_value    JSONB,
    new_value    JSONB,
    ip_address   INET,
    created_at   TIMESTAMP DEFAULT NOW()
);
```

**Uso:**
- Compliance (LGPD, GDPR)
- Rastreabilidade de mudanças
- Debug de problemas

---

## 👥 USUÁRIOS E TENANTS

### Tenants Cadastrados

| ID | Nome | Slug | Status | Inboxes | Usuários |
|----|------|------|--------|---------|----------|
| 0 | GeniAI Admin | geniai-admin | active | [] | 2 |
| 1 | AllpFit CrossFit | allpfit | active | [14, 61] | 2 |

```sql
-- Query para ver tenants
SELECT id, name, slug, status, inbox_ids,
       (SELECT COUNT(*) FROM users WHERE tenant_id = t.id) as total_users
FROM tenants t
ORDER BY id;
```

---

### Usuários Cadastrados

#### 🔹 GeniAI (Tenant 0) - Administradores

| ID | Email | Nome | Role | Acesso |
|----|-------|------|------|--------|
| 1 | admin@geniai.com.br | Administrador GeniAI | super_admin | ✅ TODOS os tenants |
| 2 | suporte@geniai.com.br | Suporte GeniAI | admin | ✅ TODOS os tenants |

#### 🔹 AllpFit (Tenant 1) - Cliente

| ID | Email | Nome | Role | Acesso |
|----|-------|------|------|--------|
| 3 | isaac@allpfit.com.br | Isaac Santos | admin | ⚠️ Apenas AllpFit |
| 4 | visualizador@allpfit.com.br | Visualizador AllpFit | client | 👁️ Apenas leitura |

---

### Senhas (Desenvolvimento)

**⚠️ TODAS as senhas de DEV:** `senha123`

**Hash bcrypt:** `$2b$12$d5.8XFOKH8.SDo4rHUTKpOWfzlPiGMr5wJ0rqXXqE3M3bGvPqZY.C`

```sql
-- Verificar hashes
SELECT id, email, LEFT(password_hash, 30) as hash_preview, role
FROM users
ORDER BY id;
```

**⚠️ ATENÇÃO:** Alterar senhas em produção!

---

## 🔒 ROW-LEVEL SECURITY (RLS)

### O que é RLS?
Row-Level Security é uma feature do PostgreSQL que **filtra automaticamente** as linhas retornadas de uma query baseado no usuário conectado.

### Como funciona no nosso sistema?

1. **Aplicação configura variáveis de sessão:**
```sql
SET app.current_tenant_id = 1;
SET app.current_user_id = 3;
```

2. **PostgreSQL aplica filtros automaticamente:**
```sql
-- Usuário client faz:
SELECT * FROM conversations_analytics;

-- PostgreSQL executa (internamente):
SELECT * FROM conversations_analytics
WHERE tenant_id = current_setting('app.current_tenant_id')::INTEGER;
-- Retorna APENAS dados do tenant 1
```

3. **Admins veem tudo:**
```sql
-- Super admin faz a mesma query
SELECT * FROM conversations_analytics;

-- PostgreSQL NÃO filtra (policy permite)
-- Retorna dados de TODOS os tenants
```

---

### Políticas RLS Criadas (31 políticas)

**Tabelas com RLS habilitado:**
- ✅ conversations_analytics
- ✅ conversations_analytics_ai
- ✅ etl_control
- ✅ inbox_tenant_mapping
- ✅ sessions
- ✅ tenant_configs
- ✅ tenants
- ✅ users
- ✅ audit_logs

**Verificar políticas:**
```sql
SELECT tablename, policyname
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

---

### Roles PostgreSQL

| Role | Permissões | Uso |
|------|------------|-----|
| `authenticated_users` | SELECT (próprio tenant) | App web (clientes) |
| `admin_users` | SELECT ALL (todos os tenants) | App web (admins) |
| `etl_service` | BYPASS RLS | ETL scripts |

---

### Exemplo Prático de RLS

```sql
-- CENÁRIO 1: Cliente AllpFit (tenant_id=1)
SET app.current_tenant_id = 1;
SET ROLE authenticated_users;

SELECT COUNT(*) FROM conversations_analytics;
-- Retorna: APENAS conversas do AllpFit (tenant_id=1)

-- CENÁRIO 2: Super Admin GeniAI (tenant_id=0)
SET ROLE admin_users;

SELECT tenant_id, COUNT(*)
FROM conversations_analytics
GROUP BY tenant_id;
-- Retorna: Conversas de TODOS os tenants (1, 2, 3, ...)

-- CENÁRIO 3: ETL (sem filtro)
SET ROLE etl_service;

INSERT INTO conversations_analytics (...) VALUES (...);
-- INSERE sem restrições (necessário para popular dados)
```

---

## 📖 QUERIES ÚTEIS

### 1. Ver estrutura de uma tabela
```sql
\d users
\d+ conversations_analytics
```

### 2. Contar usuários por tenant
```sql
SELECT
    t.name AS tenant,
    COUNT(u.id) AS total_users,
    SUM(CASE WHEN u.role = 'admin' THEN 1 ELSE 0 END) AS admins,
    SUM(CASE WHEN u.role = 'client' THEN 1 ELSE 0 END) AS clients
FROM tenants t
LEFT JOIN users u ON t.id = u.tenant_id
WHERE t.deleted_at IS NULL
  AND u.deleted_at IS NULL
GROUP BY t.id, t.name
ORDER BY t.id;
```

### 3. Ver sessões ativas
```sql
SELECT
    s.id AS session_id,
    u.email,
    u.full_name,
    t.name AS tenant,
    s.ip_address,
    s.created_at,
    s.expires_at,
    CASE
        WHEN s.expires_at > NOW() THEN 'Ativa'
        ELSE 'Expirada'
    END AS status
FROM sessions s
JOIN users u ON s.user_id = u.id
JOIN tenants t ON s.tenant_id = t.id
ORDER BY s.created_at DESC
LIMIT 10;
```

### 4. Dados de conversas por tenant
```sql
SELECT
    t.name AS tenant,
    COUNT(c.id) AS total_conversas,
    SUM(CASE WHEN c.is_lead THEN 1 ELSE 0 END) AS leads,
    SUM(CASE WHEN c.visit_scheduled THEN 1 ELSE 0 END) AS visitas_agendadas,
    MIN(c.conversation_date) AS primeira_conversa,
    MAX(c.conversation_date) AS ultima_conversa
FROM tenants t
LEFT JOIN conversations_analytics c ON t.id = c.tenant_id
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.name
ORDER BY t.id;
```

### 5. Últimas execuções do ETL
```sql
SELECT
    e.id,
    t.name AS tenant,
    e.execution_type,
    e.status,
    e.records_extracted,
    e.records_inserted,
    e.started_at,
    e.finished_at,
    (e.finished_at - e.started_at) AS duracao
FROM etl_control e
LEFT JOIN tenants t ON e.tenant_id = t.id
ORDER BY e.started_at DESC
LIMIT 10;
```

### 6. Limpar sessões expiradas
```sql
DELETE FROM sessions
WHERE expires_at < NOW();
```

### 7. Verificar integridade dos dados
```sql
-- Conversas sem tenant (ERRO)
SELECT COUNT(*)
FROM conversations_analytics
WHERE tenant_id IS NULL;

-- Usuários sem tenant (ERRO)
SELECT COUNT(*)
FROM users
WHERE tenant_id IS NULL;

-- Inboxes não mapeados
SELECT DISTINCT inbox_id
FROM conversations_analytics c
WHERE NOT EXISTS (
    SELECT 1 FROM inbox_tenant_mapping m
    WHERE m.inbox_id = c.inbox_id
);
```

---

## 🧪 DADOS DE TESTE

### Credenciais para Login

**Para testar autenticação:**

1. **Super Admin GeniAI:**
   - Email: `admin@geniai.com.br`
   - Senha: `senha123`
   - Acesso: Todos os tenants

2. **Admin AllpFit:**
   - Email: `isaac@allpfit.com.br`
   - Senha: `senha123`
   - Acesso: Apenas AllpFit

3. **Cliente AllpFit:**
   - Email: `visualizador@allpfit.com.br`
   - Senha: `senha123`
   - Acesso: Apenas leitura AllpFit

---

### Criar Novo Usuário (Teste)

```sql
-- Criar hash da senha "teste123"
-- (executar em Python):
-- import bcrypt
-- bcrypt.hashpw("teste123".encode(), bcrypt.gensalt()).decode()

INSERT INTO users (
    tenant_id, email, password_hash, full_name, role
) VALUES (
    1,  -- AllpFit
    'teste@allpfit.com.br',
    '$2b$12$novohash...',
    'Usuário Teste',
    'client'
);
```

---

### Criar Novo Tenant (Teste)

```sql
-- 1. Criar tenant
INSERT INTO tenants (name, slug, inbox_ids, status, plan) VALUES
('Academia Teste', 'academia-teste', '{999}', 'active', 'basic')
RETURNING id;

-- 2. Criar admin do tenant (usar ID retornado acima)
INSERT INTO users (tenant_id, email, password_hash, full_name, role) VALUES
(2, 'admin@academiateste.com', '$2b$12$...', 'Admin Teste', 'admin');

-- 3. Configurar tenant
INSERT INTO tenant_configs (tenant_id, primary_color, secondary_color) VALUES
(2, '#FF5722', '#4CAF50');
```

---

## 🚀 PRÓXIMOS PASSOS

### Fase 3: ETL Multi-Tenant
- [ ] Popular `inbox_tenant_mapping`
- [ ] Executar ETL para AllpFit (tenant_id=1)
- [ ] Validar dados em `conversations_analytics`

### Fase 4: Dashboard
- [ ] Filtrar queries por `tenant_id`
- [ ] Aplicar branding por tenant (tenant_configs)
- [ ] Dashboards diferenciados (admin vs client)

---

## 📞 REFERÊNCIAS RÁPIDAS

### Comandos PostgreSQL Úteis
```bash
# Conectar
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics

# Listar tabelas
\dt

# Descrever tabela
\d users

# Ver políticas RLS
\d+ conversations_analytics

# Sair
\q
```

### Arquivos Relacionados
- [00_CRONOGRAMA_MASTER.md](./00_CRONOGRAMA_MASTER.md) - Plano completo
- [01_ARQUITETURA_DB.md](./01_ARQUITETURA_DB.md) - Design detalhado
- [PROGRESS.md](./PROGRESS.md) - Progresso do projeto
- [sql/multi_tenant/](../../sql/multi_tenant/) - Scripts SQL

---

**Última atualização:** 2025-11-05
**Mantido por:** Isaac (via Claude Code)
**Status:** ✅ Fase 1 Completa - Banco 100% funcional
