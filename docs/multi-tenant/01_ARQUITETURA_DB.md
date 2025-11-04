# 🗄️ ARQUITETURA DE BANCO DE DADOS MULTI-TENANT

> **Database:** `geniai_analytics`
> **Estratégia:** Single Database + Row-Level Security (Isolamento Lógico)
> **PostgreSQL:** 14+

---

## 📐 DECISÃO ARQUITETURAL

### Por que Single Database?

| Aspecto | Single DB | Multiple DBs | Decisão |
|---------|-----------|--------------|---------|
| **Manutenção** | ✅ Simples (1 schema) | ❌ Complexa (N schemas) | Single DB |
| **Custos** | ✅ Menor overhead | ❌ N × recursos | Single DB |
| **ETL** | ✅ Pipeline único | ❌ N pipelines | Single DB |
| **Backups** | ✅ Processo único | ❌ N processos | Single DB |
| **Queries Cross-Tenant** | ✅ Possível (admin) | ❌ Requer federação | Single DB |
| **Isolamento** | ⚠️ Lógico (RLS) | ✅ Físico | Single DB* |
| **Escalabilidade** | ⚠️ Horizontal futura | ✅ Inerente | Single DB** |

\* *RLS do PostgreSQL é enterprise-grade e usado por grandes SaaS*
\** *Para >100 tenants, podemos particionar ou migrar para múltiplos DBs*

**Conclusão:** Single Database com RLS é **ideal para 1-50 clientes**, que é nosso cenário atual e projetado.

---

## 🏗️ ESTRUTURA DO BANCO

### Banco Atual vs. Novo

```
┌─────────────────────────────────────────────────────────────┐
│ ANTES (Single-Tenant)                                        │
├─────────────────────────────────────────────────────────────┤
│ Database: allpfit                                            │
│ ├── conversas_analytics (sem tenant_id)                     │
│ ├── conversas_analytics_ai                                  │
│ ├── etl_control                                             │
│ └── crm_conversions                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ DEPOIS (Multi-Tenant)                                        │
├─────────────────────────────────────────────────────────────┤
│ Database: geniai_analytics                                   │
│ ├── AUTENTICAÇÃO                                            │
│ │   ├── tenants (clientes da GeniAI)                        │
│ │   ├── users (usuários de cada tenant + admins)            │
│ │   └── sessions (controle de login)                        │
│ ├── CONFIGURAÇÃO                                            │
│ │   ├── inbox_tenant_mapping (inbox_id → tenant_id)         │
│ │   └── tenant_configs (branding, features)                 │
│ ├── DADOS (com tenant_id)                                   │
│ │   ├── conversations_analytics + tenant_id                 │
│ │   ├── conversas_analytics_ai + tenant_id                  │
│ │   └── crm_conversions + tenant_id                         │
│ ├── CONTROLE                                                │
│ │   └── etl_control + tenant_id                             │
│ └── AUDITORIA                                               │
│     └── audit_logs (ações de admin)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 MODELAGEM DE DADOS

### 1. Tabela: `tenants`

**Objetivo:** Representar cada cliente da GeniAI

```sql
CREATE TABLE tenants (
    -- Identificação
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- "AllpFit CrossFit", "Academia XYZ"
    slug VARCHAR(100) UNIQUE NOT NULL,       -- "allpfit", "academia-xyz" (URL-friendly)

    -- Configuração Chatwoot
    inbox_ids INTEGER[] NOT NULL,            -- Array: {1, 2, 3} - inboxes deste cliente
    account_id INTEGER,                      -- ID da conta no Chatwoot (opcional)

    -- Status e Plano
    status VARCHAR(20) DEFAULT 'active',     -- active, suspended, cancelled, trial
    plan VARCHAR(50) DEFAULT 'basic',        -- basic, pro, enterprise, custom
    trial_ends_at TIMESTAMP,                 -- Data fim do trial (se aplicável)

    -- Limites (futuro)
    max_conversations INTEGER DEFAULT -1,    -- -1 = ilimitado
    max_users INTEGER DEFAULT 5,

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP                     -- Soft delete
);

-- Índices
CREATE UNIQUE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_tenants_inbox_ids ON tenants USING GIN(inbox_ids);

-- Comentários
COMMENT ON TABLE tenants IS 'Clientes da GeniAI (cada cliente = 1 tenant)';
COMMENT ON COLUMN tenants.inbox_ids IS 'Array de inbox_ids do Chatwoot pertencentes a este cliente';
COMMENT ON COLUMN tenants.slug IS 'Identificador URL-friendly para login (ex: allpfit.geniai.com.br)';
```

**Dados exemplo:**
```sql
INSERT INTO tenants (id, name, slug, inbox_ids, status, plan) VALUES
(0, 'GeniAI Admin', 'geniai-admin', '{}', 'active', 'internal'),  -- Especial para admin
(1, 'AllpFit CrossFit', 'allpfit', '{1, 2}', 'active', 'pro'),
(2, 'Academia Corpo em Forma', 'corpo-em-forma', '{5, 6, 7}', 'active', 'basic'),
(3, 'Smart Gym', 'smart-gym', '{10}', 'trial', 'pro');
```

---

### 2. Tabela: `users`

**Objetivo:** Usuários de cada tenant + admins da GeniAI

```sql
CREATE TABLE users (
    -- Identificação
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Credenciais
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,     -- bcrypt hash

    -- Dados pessoais
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,

    -- Autorização
    role VARCHAR(20) DEFAULT 'client',       -- client, admin, super_admin
    permissions JSONB DEFAULT '{}',          -- Futuro: permissões granulares

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,

    -- Auditoria
    last_login TIMESTAMP,
    last_login_ip INET,
    login_count INTEGER DEFAULT 0,

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- Índices
CREATE UNIQUE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_role ON users(role);

-- Comentários
COMMENT ON TABLE users IS 'Usuários do sistema (clientes de tenants + admins GeniAI)';
COMMENT ON COLUMN users.role IS 'client: usuário normal do tenant | admin: admin do tenant | super_admin: admin GeniAI';
COMMENT ON COLUMN users.tenant_id IS 'Tenant ao qual este usuário pertence (0 = GeniAI admin)';
```

**Dados exemplo:**
```sql
-- Admins GeniAI (tenant_id = 0)
INSERT INTO users (tenant_id, email, password_hash, full_name, role) VALUES
(0, 'admin@geniai.com.br', '$2b$12$...', 'Admin GeniAI', 'super_admin'),
(0, 'suporte@geniai.com.br', '$2b$12$...', 'Suporte GeniAI', 'admin');

-- Usuários clientes
INSERT INTO users (tenant_id, email, password_hash, full_name, role) VALUES
(1, 'isaac@allpfit.com.br', '$2b$12$...', 'Isaac Santos', 'client'),
(1, 'admin@allpfit.com.br', '$2b$12$...', 'Admin AllpFit', 'admin'),
(2, 'contato@corpoemforma.com', '$2b$12$...', 'João Silva', 'client'),
(3, 'dono@smartgym.com', '$2b$12$...', 'Maria Oliveira', 'client');
```

---

### 3. Tabela: `sessions`

**Objetivo:** Gerenciar sessões de login (segurança)

```sql
CREATE TABLE sessions (
    -- Identificação
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Metadados da sessão
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),                 -- desktop, mobile, tablet

    -- Validade
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    -- Auditoria
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_active ON sessions(is_active, expires_at);

-- Auto-delete sessões expiradas (PostgreSQL 15+)
-- Ou usar cron job para limpar periodicamente

COMMENT ON TABLE sessions IS 'Controle de sessões de login (JWT alternative)';
COMMENT ON COLUMN sessions.expires_at IS 'Data de expiração da sessão (default: 24h após login)';
```

---

### 4. Tabela: `inbox_tenant_mapping`

**Objetivo:** Mapear inbox_id do Chatwoot → tenant_id

```sql
CREATE TABLE inbox_tenant_mapping (
    -- Mapeamento
    inbox_id INTEGER PRIMARY KEY,            -- ID do inbox no Chatwoot
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Metadados
    inbox_name VARCHAR(255),                 -- Nome do inbox (ex: "AllpFit WhatsApp")
    channel_type VARCHAR(50),                -- whatsapp, telegram, email, etc
    is_active BOOLEAN DEFAULT TRUE,

    -- Auditoria
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_inbox_tenant_id ON inbox_tenant_mapping(tenant_id);
CREATE INDEX idx_inbox_active ON inbox_tenant_mapping(is_active);

COMMENT ON TABLE inbox_tenant_mapping IS 'Mapeia inbox_id (Chatwoot) para tenant_id (GeniAI)';
COMMENT ON COLUMN inbox_tenant_mapping.inbox_id IS 'ID do inbox no banco Chatwoot';
```

**Dados exemplo:**
```sql
INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, inbox_name, channel_type) VALUES
(1, 1, 'AllpFit WhatsApp Principal', 'whatsapp'),
(2, 1, 'AllpFit Telegram', 'telegram'),
(5, 2, 'Corpo em Forma WhatsApp', 'whatsapp'),
(6, 2, 'Corpo em Forma Instagram', 'instagram'),
(7, 2, 'Corpo em Forma Email', 'email'),
(10, 3, 'Smart Gym WhatsApp', 'whatsapp');
```

---

### 5. Tabela: `tenant_configs`

**Objetivo:** Configurações e personalização por tenant

```sql
CREATE TABLE tenant_configs (
    tenant_id INTEGER PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,

    -- Branding
    logo_url TEXT,
    favicon_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#1E40AF',    -- Hex color
    secondary_color VARCHAR(7) DEFAULT '#10B981',
    custom_css TEXT,

    -- Features habilitadas
    features JSONB DEFAULT '{
        "ai_analysis": true,
        "crm_integration": true,
        "custom_reports": false,
        "api_access": false
    }',

    -- Configurações de notificação
    notifications JSONB DEFAULT '{
        "email_reports": false,
        "webhook_url": null,
        "alert_threshold": 100
    }',

    -- Personalização de dashboard
    dashboard_config JSONB DEFAULT '{}',

    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE tenant_configs IS 'Configurações e personalizações por tenant (logo, cores, features)';
```

**Dados exemplo:**
```sql
INSERT INTO tenant_configs (tenant_id, logo_url, primary_color, features) VALUES
(1, 'https://allpfit.com.br/logo.png', '#FF6B35', '{
    "ai_analysis": true,
    "crm_integration": true,
    "custom_reports": true
}'),
(2, NULL, '#2563EB', '{
    "ai_analysis": true,
    "crm_integration": false
}');
```

---

### 6. Tabela: `conversations_analytics` (MODIFICADA)

**Objetivo:** Adicionar `tenant_id` à tabela existente

```sql
-- NÃO recriar a tabela, apenas adicionar colunas
ALTER TABLE conversations_analytics
ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
ADD COLUMN inbox_id INTEGER;  -- Redundante mas útil para performance

-- Popular tenant_id baseado no inbox_id
UPDATE conversations_analytics ca
SET tenant_id = itm.tenant_id
FROM inbox_tenant_mapping itm
WHERE ca.inbox_id = itm.inbox_id;

-- Tornar NOT NULL após popular
ALTER TABLE conversations_analytics
ALTER COLUMN tenant_id SET NOT NULL;

-- Índices para performance multi-tenant
CREATE INDEX idx_conversations_tenant_id ON conversations_analytics(tenant_id);
CREATE INDEX idx_conversations_tenant_date ON conversations_analytics(tenant_id, conversation_date);
CREATE INDEX idx_conversations_tenant_inbox ON conversations_analytics(tenant_id, inbox_id);

-- Índice composto para queries comuns do dashboard
CREATE INDEX idx_conversations_tenant_status_date
ON conversations_analytics(tenant_id, status, conversation_date DESC);
```

---

### 7. Tabela: `etl_control` (MODIFICADA)

**Objetivo:** Controlar watermark por tenant

```sql
ALTER TABLE etl_control
ADD COLUMN tenant_id INTEGER REFERENCES tenants(id),
ADD COLUMN inbox_ids INTEGER[];  -- Quais inboxes foram sincronizados nesta execução

-- Índices
CREATE INDEX idx_etl_control_tenant ON etl_control(tenant_id);
CREATE INDEX idx_etl_control_tenant_status ON etl_control(tenant_id, status, finished_at DESC);

COMMENT ON COLUMN etl_control.tenant_id IS 'Tenant sincronizado nesta execução (NULL = sync global)';
COMMENT ON COLUMN etl_control.inbox_ids IS 'Array de inbox_ids sincronizados nesta execução';
```

---

### 8. Tabela: `audit_logs`

**Objetivo:** Rastrear ações de admins (compliance)

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,

    -- Quem fez
    user_id INTEGER REFERENCES users(id),
    user_email VARCHAR(255),                 -- Cache para caso user seja deletado
    user_role VARCHAR(20),

    -- Contexto
    tenant_id INTEGER REFERENCES tenants(id),  -- Tenant afetado (NULL = sistema)
    ip_address INET,

    -- Ação
    action VARCHAR(100) NOT NULL,            -- create_tenant, delete_user, update_config, etc
    entity_type VARCHAR(50),                 -- tenant, user, config, etc
    entity_id INTEGER,
    description TEXT,

    -- Dados (antes/depois)
    old_value JSONB,
    new_value JSONB,

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS 'Log de auditoria de ações administrativas (compliance, segurança)';
```

---

## 🔒 ROW-LEVEL SECURITY (RLS)

### Objetivo
Garantir que **usuários só vejam dados do próprio tenant**, mesmo se houver bug no código de aplicação.

### Como funciona
1. PostgreSQL valida **todas as queries** contra políticas RLS
2. Se policy retornar `FALSE`, linha é **invisível** para o usuário
3. Admin pode ter policy especial que retorna `TRUE` (vê tudo)

### Implementação

#### 1. Criar ROLES no PostgreSQL

```sql
-- Role para clientes (usuários normais)
CREATE ROLE authenticated_users;

-- Role para admins GeniAI
CREATE ROLE admin_users;

-- Cada conexão da aplicação assume um desses roles
-- SET ROLE authenticated_users;  -- Para clientes
-- SET ROLE admin_users;          -- Para admins
```

#### 2. Configurar session variables

```sql
-- A aplicação define o tenant_id da sessão atual
SET app.current_tenant_id = 1;  -- AllpFit
SET app.current_user_role = 'client';
```

#### 3. Habilitar RLS nas tabelas

```sql
-- Tabelas de dados
ALTER TABLE conversations_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversas_analytics_ai ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_conversions ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_control ENABLE ROW LEVEL SECURITY;
```

#### 4. Criar Políticas (Policies)

**A) Política para CLIENTES (só veem seu tenant)**

```sql
-- Conversations
CREATE POLICY tenant_isolation_conversations
ON conversations_analytics
FOR ALL
TO authenticated_users
USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- AI Analysis
CREATE POLICY tenant_isolation_ai
ON conversas_analytics_ai
FOR ALL
TO authenticated_users
USING (
    conversation_id IN (
        SELECT conversation_id FROM conversations_analytics
        WHERE tenant_id = current_setting('app.current_tenant_id')::INTEGER
    )
);

-- CRM Conversions (quando for criada)
CREATE POLICY tenant_isolation_crm
ON crm_conversions
FOR ALL
TO authenticated_users
USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- ETL Control (clientes só veem ETL do próprio tenant)
CREATE POLICY tenant_isolation_etl
ON etl_control
FOR SELECT
TO authenticated_users
USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
```

**B) Política para ADMINS (veem tudo)**

```sql
-- Admins têm acesso irrestrito
CREATE POLICY admin_all_access_conversations
ON conversations_analytics
FOR ALL
TO admin_users
USING (TRUE);

CREATE POLICY admin_all_access_ai
ON conversas_analytics_ai
FOR ALL
TO admin_users
USING (TRUE);

CREATE POLICY admin_all_access_crm
ON crm_conversions
FOR ALL
TO admin_users
USING (TRUE);

CREATE POLICY admin_all_access_etl
ON etl_control
FOR ALL
TO admin_users
USING (TRUE);
```

#### 5. Bypass RLS para ETL (necessário)

```sql
-- ETL precisa inserir dados de todos os tenants
-- Criar role especial
CREATE ROLE etl_service;

-- Dar permissão para BYPASSAR RLS
ALTER TABLE conversations_analytics
ALTER TABLE conversas_analytics_ai
ALTER TABLE etl_control
FORCE ROW LEVEL SECURITY;  -- Força RLS para todos EXCETO superusers

-- ETL usa conexão com superuser OU
GRANT BYPASS RLS ON conversations_analytics TO etl_service;
```

### Uso na Aplicação (Python)

```python
# src/multi_tenant/database.py

def get_connection(session_data):
    """
    Conecta ao banco e configura RLS baseado na sessão
    """
    conn = psycopg2.connect(DATABASE_URL)

    # Configurar role baseado no papel do usuário
    if session_data['user_role'] in ['admin', 'super_admin']:
        conn.execute("SET ROLE admin_users;")
    else:
        conn.execute("SET ROLE authenticated_users;")

    # Definir tenant da sessão
    conn.execute(f"SET app.current_tenant_id = {session_data['tenant_id']};")
    conn.execute(f"SET app.current_user_role = '{session_data['user_role']}';")

    return conn

# Exemplo de uso
session = validate_session(session_id)
conn = get_connection(session)

# Esta query SÓ retorna dados do tenant correto (RLS garante)
df = pd.read_sql("SELECT * FROM conversations_analytics", conn)
# Mesmo que desenvolvedor esqueça WHERE tenant_id = ?, RLS protege!
```

---

## 🔄 MIGRAÇÃO DE DADOS

### Estratégia

1. ✅ **Criar banco `geniai_analytics`** vazio
2. ✅ **Executar DDL** (CREATE TABLE, índices, RLS)
3. ✅ **Seed dados** iniciais (tenants, users)
4. ✅ **Migrar dados** do banco `allpfit` → `geniai_analytics`
5. ✅ **Validar** integridade e isolamento
6. ✅ **Atualizar aplicação** para usar novo banco
7. ✅ **Backup** banco antigo e desativar

### Scripts de Migração

#### 1. Criar banco e schema

```bash
# sql/multi_tenant/01_create_database.sql
CREATE DATABASE geniai_analytics
WITH
    ENCODING = 'UTF8'
    LC_COLLATE = 'pt_BR.UTF-8'
    LC_CTYPE = 'pt_BR.UTF-8'
    TEMPLATE = template0;

# Executar
psql -U postgres -c "CREATE DATABASE geniai_analytics;"
```

#### 2. Criar tabelas

```bash
psql -U postgres -d geniai_analytics -f sql/multi_tenant/02_create_schema.sql
```

#### 3. Seed dados iniciais

```bash
psql -U postgres -d geniai_analytics -f sql/multi_tenant/03_seed_data.sql
```

#### 4. Migrar dados AllpFit

```sql
-- sql/multi_tenant/04_migrate_allpfit.sql

-- Conectar aos dois bancos
\c geniai_analytics

-- Usar dblink para copiar dados
CREATE EXTENSION IF NOT EXISTS dblink;

-- Copiar conversas
INSERT INTO conversations_analytics
SELECT
    *,
    1 AS tenant_id,  -- AllpFit é tenant_id = 1
    inbox_id
FROM dblink(
    'dbname=allpfit user=isaac',
    'SELECT * FROM conversas_analytics'
) AS t(...);  -- Listar todas as colunas

-- Copiar AI analysis
INSERT INTO conversas_analytics_ai
SELECT *, 1 AS tenant_id
FROM dblink('dbname=allpfit', 'SELECT * FROM conversas_analytics_ai') AS t(...);

-- Copiar ETL control
INSERT INTO etl_control
SELECT *, 1 AS tenant_id, NULL AS inbox_ids
FROM dblink('dbname=allpfit', 'SELECT * FROM etl_control') AS t(...);

-- Validar
SELECT
    'conversations' AS table_name,
    tenant_id,
    COUNT(*) AS row_count
FROM conversations_analytics
GROUP BY tenant_id

UNION ALL

SELECT 'ai_analysis', tenant_id, COUNT(*)
FROM conversas_analytics_ai
GROUP BY tenant_id;
```

#### 5. Habilitar RLS

```bash
psql -U postgres -d geniai_analytics -f sql/multi_tenant/05_row_level_security.sql
```

### Validação Pós-Migração

```sql
-- 1. Verificar contagens
SELECT 'allpfit DB' AS source, COUNT(*) FROM allpfit.conversas_analytics
UNION ALL
SELECT 'geniai_analytics DB', COUNT(*) FROM geniai_analytics.conversations_analytics;

-- 2. Verificar tenant_id
SELECT tenant_id, COUNT(*) FROM conversations_analytics GROUP BY tenant_id;
-- Deve mostrar: tenant_id=1, COUNT=N

-- 3. Testar RLS
SET ROLE authenticated_users;
SET app.current_tenant_id = 1;
SELECT COUNT(*) FROM conversations_analytics;  -- Deve retornar todas

SET app.current_tenant_id = 999;
SELECT COUNT(*) FROM conversations_analytics;  -- Deve retornar 0 (não existe tenant 999)

-- 4. Testar admin
SET ROLE admin_users;
SELECT COUNT(*) FROM conversations_analytics;  -- Deve retornar todas independente de tenant_id
```

---

## 📈 PERFORMANCE E OTIMIZAÇÃO

### Índices Críticos

```sql
-- Multi-tenant queries
CREATE INDEX idx_conv_tenant_date ON conversations_analytics(tenant_id, conversation_date DESC);
CREATE INDEX idx_conv_tenant_status ON conversations_analytics(tenant_id, status);
CREATE INDEX idx_conv_tenant_inbox ON conversations_analytics(tenant_id, inbox_id);

-- Lookups rápidos
CREATE INDEX idx_inbox_mapping_tenant ON inbox_tenant_mapping(tenant_id);
CREATE INDEX idx_users_tenant ON users(tenant_id) WHERE deleted_at IS NULL;

-- Autenticação
CREATE UNIQUE INDEX idx_users_email_active ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_sessions_active ON sessions(user_id, expires_at) WHERE is_active = TRUE;
```

### Particionamento (Futuro - 50+ tenants)

```sql
-- Particionar conversations_analytics por tenant_id
CREATE TABLE conversations_analytics_partitioned (
    LIKE conversations_analytics INCLUDING ALL
) PARTITION BY LIST (tenant_id);

-- Criar partição por tenant
CREATE TABLE conversations_analytics_tenant_1
PARTITION OF conversations_analytics_partitioned
FOR VALUES IN (1);

CREATE TABLE conversations_analytics_tenant_2
PARTITION OF conversations_analytics_partitioned
FOR VALUES IN (2);

-- Migrar dados
INSERT INTO conversations_analytics_partitioned SELECT * FROM conversations_analytics;
```

### Caching (Redis - Futuro)

```python
# Cache de dados frequentes
@cache.memoize(timeout=300)  # 5 minutos
def get_tenant_config(tenant_id):
    return db.query("SELECT * FROM tenant_configs WHERE tenant_id = ?", tenant_id)

@cache.memoize(timeout=60)  # 1 minuto
def get_kpis(tenant_id, date_start, date_end):
    return calculate_metrics(tenant_id, date_start, date_end)
```

---

## 🧪 TESTES DE ISOLAMENTO

### 1. Teste Manual (SQL)

```sql
-- Setup: criar 2 tenants com dados
INSERT INTO tenants (name, slug, inbox_ids) VALUES
('Tenant A', 'tenant-a', '{100}'),
('Tenant B', 'tenant-b', '{200}');

INSERT INTO conversations_analytics (conversation_id, tenant_id, inbox_id, ...) VALUES
(1, 1, 100, ...),  -- Tenant A
(2, 1, 100, ...),  -- Tenant A
(3, 2, 200, ...),  -- Tenant B
(4, 2, 200, ...);  -- Tenant B

-- Teste 1: Cliente Tenant A só vê seus dados
SET ROLE authenticated_users;
SET app.current_tenant_id = 1;
SELECT conversation_id FROM conversations_analytics;
-- Esperado: {1, 2}

-- Teste 2: Cliente Tenant B só vê seus dados
SET app.current_tenant_id = 2;
SELECT conversation_id FROM conversations_analytics;
-- Esperado: {3, 4}

-- Teste 3: Admin vê tudo
SET ROLE admin_users;
SELECT conversation_id FROM conversations_analytics;
-- Esperado: {1, 2, 3, 4}
```

### 2. Teste Automatizado (Python/pytest)

```python
# tests/multi_tenant/test_rls.py

def test_tenant_isolation(db):
    """Testa que RLS isola dados corretamente"""
    # Setup: criar 2 tenants
    tenant_a = create_tenant("Tenant A", "tenant-a", [100])
    tenant_b = create_tenant("Tenant B", "tenant-b", [200])

    # Criar dados
    create_conversation(tenant_a.id, conversation_id=1)
    create_conversation(tenant_a.id, conversation_id=2)
    create_conversation(tenant_b.id, conversation_id=3)

    # Teste: usuário Tenant A
    with db.session(tenant_id=tenant_a.id, role='client') as conn:
        result = conn.query("SELECT conversation_id FROM conversations_analytics")
        assert set(result) == {1, 2}

    # Teste: usuário Tenant B
    with db.session(tenant_id=tenant_b.id, role='client') as conn:
        result = conn.query("SELECT conversation_id FROM conversations_analytics")
        assert set(result) == {3}

    # Teste: admin
    with db.session(tenant_id=0, role='super_admin') as conn:
        result = conn.query("SELECT conversation_id FROM conversations_analytics")
        assert set(result) == {1, 2, 3}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Schema
- [ ] Criar database `geniai_analytics`
- [ ] Criar tabelas de autenticação (tenants, users, sessions)
- [ ] Criar tabelas de configuração (inbox_mapping, tenant_configs)
- [ ] Modificar tabelas existentes (ADD tenant_id)
- [ ] Criar índices de performance
- [ ] Documentar schema com comentários

### Fase 2: RLS
- [ ] Criar roles (authenticated_users, admin_users)
- [ ] Habilitar RLS em tabelas
- [ ] Criar policies para clientes
- [ ] Criar policies para admins
- [ ] Testar isolamento (SQL manual)
- [ ] Documentar políticas

### Fase 3: Migração
- [ ] Backup completo banco `allpfit`
- [ ] Seed dados iniciais (tenants, users)
- [ ] Criar inbox_tenant_mapping
- [ ] Migrar conversations_analytics
- [ ] Migrar conversas_analytics_ai
- [ ] Migrar etl_control
- [ ] Validar integridade (counts, checksums)

### Fase 4: Validação
- [ ] Testes SQL de isolamento
- [ ] Testes Python automatizados
- [ ] Performance benchmarks (antes/depois)
- [ ] Documentação de troubleshooting

---

**Próximo arquivo:** [02_AUTENTICACAO.md](02_AUTENTICACAO.md)
**Voltar para:** [00_CRONOGRAMA_MASTER.md](00_CRONOGRAMA_MASTER.md)