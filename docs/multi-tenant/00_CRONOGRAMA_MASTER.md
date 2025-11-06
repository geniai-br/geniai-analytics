# 📋 CRONOGRAMA MASTER - SISTEMA MULTI-TENANT GENIAI

> **Projeto:** Transformação AllpFit Analytics → GeniAI Multi-Tenant SaaS Platform
> **Objetivo:** Dashboard personalizado por cliente com painel admin central
> **Metodologia:** Desenvolvimento incremental, testável e com commits frequentes

---

## 🎯 VISÃO GERAL DO PROJETO

### Contexto Atual
- **Sistema Atual:** AllpFit Analytics (single-tenant)
- **Banco Atual:** PostgreSQL local (`allpfit`) + Remoto Chatwoot (read-only)
- **ETL Atual:** Pipeline V3 incremental com watermark
- **Dashboard Atual:** Streamlit single-user, sem autenticação

### Objetivo Final
- **Sistema Multi-Tenant:** Cada cliente da GeniAI com dashboard isolado
- **Segregação por Inbox:** Dados filtrados por inbox_id do Chatwoot
- **Autenticação:** Login por cliente com sessões seguras
- **Painel Admin:** Dashboard central GeniAI para gestão de todos os clientes
- **Arquitetura:** Dados centralizados com isolamento lógico (row-level security)

---

## 📊 ESTRATÉGIA DE BANCO DE DADOS

### Decisão Arquitetural: **BANCO ÚNICO COM ISOLAMENTO LÓGICO**

**Por que não criar bancos separados?**
1. ✅ **Manutenção simplificada:** Um único schema para atualizar
2. ✅ **ETL centralizado:** Um pipeline busca todos os inboxes
3. ✅ **Custos reduzidos:** Menor overhead de recursos
4. ✅ **Queries cross-tenant:** Admin pode ver métricas agregadas
5. ✅ **Backup e monitoring:** Processo unificado

**Estrutura escolhida:**
```
Database: geniai_analytics (novo banco centralizado)
├── Schema: public
│   ├── Tabelas de autenticação (users, tenants, sessions)
│   ├── Tabelas de configuração (inbox_mappings, client_configs)
│   └── Tabelas de dados (conversations_analytics + tenant_id)
└── Row-Level Security (RLS) para isolamento
```

**Migração do banco atual:**
- ❌ NÃO vamos usar o banco `allpfit` (single-tenant)
- ✅ Vamos criar `geniai_analytics` (multi-tenant)
- ✅ Migrar dados existentes com tenant_id = 1 (AllpFit como primeiro cliente)

---

## 🗓️ FASES DO PROJETO

| Fase | Nome | Duração Est. | Duração Real | Status |
|------|------|--------------|--------------|--------|
| **FASE 0** | Setup e Planejamento | 1 dia | - | ✅ Completa |
| **FASE 1** | Arquitetura de Dados | 2-3 dias | - | ✅ Completa |
| **FASE 2** | Sistema de Autenticação | 2-3 dias | ~9h | ✅ Completa |
| **FASE 3** | ETL Multi-Tenant | 3-4 dias | ~8h | ✅ Completa |
| **FASE 4** | Dashboard Cliente | 2-3 dias | - | 🔄 Próxima |
| **FASE 5** | Dashboard Admin | 2-3 dias | - | ⏳ Pendente |
| **FASE 6** | Testes e Deploy | 2-3 dias | - | ⏳ Pendente |

**Total estimado:** 14-20 dias úteis
**Progresso atual:** 3/6 fases completas (50%)

---

## 📅 FASE 0: SETUP E PLANEJAMENTO (1 dia)

### Objetivos
- [x] Análise completa do código atual
- [x] Documentação da arquitetura atual
- [ ] Criação de branch para desenvolvimento
- [ ] Estrutura de pastas para o projeto
- [ ] Documentação técnica inicial

### Tarefas
#### 0.1 - Controle de Versão
```bash
git checkout -b feature/multi-tenant-system
git push -u origin feature/multi-tenant-system
```

#### 0.2 - Estrutura de Pastas
```
projetos/allpfit-analytics/
├── docs/multi-tenant/              # Documentação do projeto
│   ├── 00_CRONOGRAMA_MASTER.md    # Este arquivo
│   ├── 01_ARQUITETURA_DB.md       # Schema multi-tenant
│   ├── 02_AUTENTICACAO.md         # Fluxo de auth
│   ├── 03_ETL_DESIGN.md           # Pipeline multi-tenant
│   ├── 04_DASHBOARD_SPECS.md      # UI/UX specs
│   └── 05_DEPLOYMENT.md           # Guia de deploy
├── sql/multi_tenant/               # Scripts SQL
│   ├── 01_create_database.sql     # CREATE DATABASE geniai_analytics
│   ├── 02_create_schema.sql       # Tabelas multi-tenant
│   ├── 03_seed_data.sql           # Dados iniciais (tenants, users)
│   ├── 04_migrate_allpfit.sql     # Migração dados AllpFit
│   └── 05_row_level_security.sql  # Políticas RLS
├── src/multi_tenant/               # Código novo
│   ├── auth/                      # Sistema de autenticação
│   ├── models/                    # SQLAlchemy models
│   ├── etl_v4/                    # ETL multi-tenant
│   └── dashboards/                # Dashboards (client + admin)
└── tests/multi_tenant/            # Testes
```

#### 0.3 - Commits Iniciais
- `docs: add multi-tenant master cronograma`
- `docs: add database architecture design`
- `chore: create multi-tenant folder structure`

### Entregáveis
- ✅ Branch `feature/multi-tenant-system` criada
- ✅ Estrutura de pastas completa
- ✅ Documentação inicial (5 arquivos .md)

---

## 📅 FASE 1: ARQUITETURA DE DADOS (2-3 dias)

### Objetivos
- Criar novo banco `geniai_analytics`
- Modelar schema multi-tenant
- Implementar Row-Level Security (RLS)
- Migrar dados existentes do AllpFit

### Tarefas

#### 1.1 - Modelagem do Schema (Dia 1 - manhã)

**Tabelas principais:**

1. **`tenants`** - Clientes da GeniAI
```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- Ex: "AllpFit", "Academia XYZ"
    slug VARCHAR(100) UNIQUE NOT NULL,    -- Ex: "allpfit", "academia-xyz"
    inbox_ids INTEGER[] NOT NULL,         -- Array de inbox_ids do Chatwoot
    status VARCHAR(20) DEFAULT 'active',  -- active, suspended, cancelled
    plan VARCHAR(50) DEFAULT 'basic',     -- basic, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

2. **`users`** - Usuários (clientes + admin GeniAI)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'client',    -- client, admin, super_admin
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

3. **`sessions`** - Controle de sessões
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES tenants(id),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

4. **`conversations_analytics`** - Dados das conversas (MULTI-TENANT)
```sql
-- Adicionar coluna tenant_id à tabela existente
ALTER TABLE conversations_analytics
ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);

-- Índice para performance
CREATE INDEX idx_conversations_tenant_id ON conversations_analytics(tenant_id);
CREATE INDEX idx_conversations_tenant_date ON conversations_analytics(tenant_id, conversation_date);
```

5. **`etl_control`** - Controle ETL (MULTI-TENANT)
```sql
-- Adicionar tenant_id ao controle ETL
ALTER TABLE etl_control
ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
```

#### 1.2 - Row-Level Security (Dia 1 - tarde)

**Objetivo:** Garantir que queries retornem apenas dados do tenant correto

```sql
-- Habilitar RLS
ALTER TABLE conversations_analytics ENABLE ROW LEVEL SECURITY;

-- Política para clientes (só veem seus dados)
CREATE POLICY tenant_isolation_policy ON conversations_analytics
    FOR ALL
    TO authenticated_users
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- Política para admins (veem tudo)
CREATE POLICY admin_all_access_policy ON conversations_analytics
    FOR ALL
    TO admin_users
    USING (TRUE);
```

#### 1.3 - Dados Seed (Dia 2 - manhã)

**Criar tenants iniciais:**
```sql
-- GeniAI (tenant_id = 0, especial para admin)
INSERT INTO tenants (id, name, slug, inbox_ids, status, plan) VALUES
(0, 'GeniAI Admin', 'geniai-admin', '{}', 'active', 'internal');

-- AllpFit (primeiro cliente real)
INSERT INTO tenants (name, slug, inbox_ids, status, plan) VALUES
('AllpFit CrossFit', 'allpfit', '{1, 2, 3}', 'active', 'pro');

-- Usuários admin
INSERT INTO users (tenant_id, email, password_hash, full_name, role) VALUES
(0, 'admin@geniai.com.br', '$2b$...', 'Admin GeniAI', 'super_admin'),
(1, 'isaac@allpfit.com.br', '$2b$...', 'Isaac AllpFit', 'client');
```

#### 1.4 - Migração de Dados (Dia 2 - tarde)

**Migrar dados do banco `allpfit` → `geniai_analytics`**

```sql
-- Inserir dados existentes com tenant_id = 1 (AllpFit)
INSERT INTO geniai_analytics.conversations_analytics
SELECT *, 1 AS tenant_id
FROM allpfit.conversas_analytics;

-- Verificar migração
SELECT tenant_id, COUNT(*)
FROM conversations_analytics
GROUP BY tenant_id;
```

#### 1.5 - Scripts de Teste (Dia 3)

```python
# tests/multi_tenant/test_database.py
def test_tenant_isolation():
    """Verifica que RLS está funcionando"""
    # Conectar como tenant_id = 1
    # Verificar que só retorna dados do tenant 1

def test_admin_access():
    """Verifica que admin vê todos os dados"""
    # Conectar como super_admin
    # Verificar acesso a todos os tenants
```

### Commits
- `feat(db): create geniai_analytics database schema`
- `feat(db): add row-level security policies`
- `feat(db): seed initial tenants and users`
- `feat(db): migrate allpfit data to multi-tenant`
- `test(db): add tenant isolation tests`

### Entregáveis
- ✅ Banco `geniai_analytics` criado
- ✅ Schema multi-tenant modelado
- ✅ RLS implementado e testado
- ✅ Dados AllpFit migrados
- ✅ Scripts de teste validados

---

## 📅 FASE 2: SISTEMA DE AUTENTICAÇÃO & UX MULTI-TENANT ✅ **COMPLETA**

> **Status:** ✅ IMPLEMENTADA, REVISADA E APROVADA (2025-11-06)
> **Duração Real:** ~9h total (6h implementação + 2h debug RLS + 1h melhorias)
> **Estimativa Inicial:** 2-3 dias (16-24h)
> **Economia:** 62% mais rápido que estimado
> **Design Base:** Tema dark da porta 8503 (azul #1E90FF + laranja #FF8C00)
> **URL:** http://localhost:8504

### Objetivos ✅
- ✅ Tela de login moderna (tema dark profissional)
- ✅ Autenticação com bcrypt + sessions no banco
- ✅ **Fluxo diferenciado por role:**
  - ✅ **Super Admin/Admin GeniAI** → Painel de seleção de clientes
  - ✅ **Cliente** → Dashboard direto do seu tenant
- ✅ Dashboard básico protegido com middleware
- ✅ Configuração RLS automática
- ✅ Sistema de logging profissional
- ✅ Cache em queries de dados (TTL 5min)
- ✅ Validação de email no login

### 🔧 Melhorias Aplicadas (Pós-Implementação)
1. **Logging Profissional** - Substituídos 40+ prints por logger estruturado
2. **Performance** - Cache em `load_conversations()` (5min TTL - 94% mais rápido)
3. **Validação** - Regex para formato de email no form de login
4. **Código Limpo** - Removidos todos os logs de debug temporários

### 🐛 Bugs Críticos Resolvidos
1. **RLS Bloqueando Sessions** - Desabilitado RLS na tabela `sessions`
2. **Queries com Colunas Inexistentes** - Adaptadas para usar colunas reais (proxies temporários)

### 📚 Lições Aprendidas
1. **RLS pode bloquear o próprio sistema** - Tabelas de auth devem ter RLS desabilitado
2. **Queries devem usar colunas existentes** - Não assumir estrutura futura
3. **Cache é essencial para UX** - TTL de 5min melhora performance em 94%
4. **Logging profissional desde o início** - Economiza tempo de refactoring
5. **Debugging com Streamlit é difícil** - Usar `st.info()` para debug visual

Ver detalhes completos em: [FASE2_MELHORIAS.md](FASE2_MELHORIAS.md) | [BUG_FIX_LOGIN_RLS.md](BUG_FIX_LOGIN_RLS.md)

---

### 🎨 UX Flow - Experiências por Role

#### **FLUXO 1: Super Admin / Admin GeniAI (tenant_id = 0)**
```
Login → Painel Admin GeniAI
  ↓
┌────────────────────────────────────┐
│  🎛️  PAINEL ADMIN GENIAI          │
│                                    │
│  Bem-vindo, {nome}                 │
│                                    │
│  📊 Overview Geral:                │
│  • Total Clientes: 2               │
│  • Total Conversas: 1.234          │
│  • Total Leads: 567                │
│                                    │
│  👥 Selecione um Cliente:          │
│  ┌─────────────────────────────┐  │
│  │ 📦 AllpFit CrossFit         │  │
│  │ Inboxes: 2 | Usuários: 2    │  │
│  │ [Ver Dashboard] →            │  │
│  └─────────────────────────────┘  │
│                                    │
│  ┌─────────────────────────────┐  │
│  │ 📦 Academia XYZ             │  │
│  │ Inboxes: 1 | Usuários: 3    │  │
│  │ [Ver Dashboard] →            │  │
│  └─────────────────────────────┘  │
│                                    │
│  ⚙️ [Gerenciar Clientes]          │
│  🚪 [Sair]                         │
└────────────────────────────────────┘
```

**Ao clicar em "Ver Dashboard":**
- Redireciona para dashboard filtrado por aquele tenant
- Mantém capacidade de voltar ao painel
- Exibe nome do cliente no topo

---

#### **FLUXO 2: Cliente (ex: AllpFit - tenant_id = 1)**
```
Login → Dashboard Direto
  ↓
┌────────────────────────────────────┐
│  📊 ANALYTICS - ALLPFIT           │
│  👤 Isaac Santos (Admin)           │
│                                    │
│  [Filtros de Data] [Atualizar]    │
│                                    │
│  ┌─────┬─────┬─────┬─────┐       │
│  │ KPI │ KPI │ KPI │ KPI │       │
│  └─────┴─────┴─────┴─────┘       │
│                                    │
│  [Gráficos e Tabelas...]          │
│                                    │
│  🚪 [Sair]                         │
└────────────────────────────────────┘
```

**Características:**
- Sem painel de seleção (só vê seus dados)
- Logo/cores personalizadas (tenant_configs)
- Mesmo layout do dashboard da porta 8503

---

### 📂 Estrutura de Arquivos

```
src/multi_tenant/
├── auth/
│   ├── __init__.py          # Exports
│   ├── auth.py              # Lógica única de autenticação + sessão
│   └── middleware.py        # Proteção de rotas + RLS config
│
└── dashboards/
    ├── app.py               # App principal (entry point)
    ├── login_page.py        # Tela de login
    ├── admin_panel.py       # Painel admin (seleção de clientes)
    ├── client_dashboard.py  # Dashboard do cliente
    └── components/
        ├── header.py        # Header comum
        └── metrics.py       # Reutilizar da porta 8503
```

---

### Tarefas Detalhadas

#### **2.1 - Módulo de Autenticação Unificado (3-4h)**

**Arquivo: `src/multi_tenant/auth/auth.py`**

Funções principais:
```python
def authenticate_user(engine, email, password) -> dict:
    """
    Autentica e cria sessão
    Returns: {
        'session_id': UUID,
        'user_id': int,
        'tenant_id': int,
        'email': str,
        'full_name': str,
        'role': str,  # 'super_admin', 'admin', 'client'
        'tenant_name': str,
        'tenant_slug': str
    }
    """
    # 1. Buscar user + tenant no banco
    # 2. Verificar senha (bcrypt)
    # 3. Criar sessão
    # 4. Retornar dados completos

def validate_session(engine, session_id) -> dict | None:
    """Valida sessão e retorna dados do user + tenant"""
    # SELECT * FROM sessions WHERE id = ? AND expires_at > NOW()
    # JOIN users, tenants

def logout_user(engine, session_id) -> bool:
    """Destroi sessão"""
    # DELETE FROM sessions WHERE id = ?

def get_database_engine() -> Engine:
    """Retorna engine SQLAlchemy com cache"""
    # Cache no st.cache_resource
```

**Arquivo: `src/multi_tenant/auth/middleware.py`**

```python
def require_authentication() -> dict:
    """
    Middleware para proteger páginas
    - Valida sessão
    - Configura RLS context
    - Retorna session_data
    """
    if 'session_id' not in st.session_state:
        # Redirecionar para login
        show_login_page()
        st.stop()

    session = validate_session(engine, st.session_state.session_id)

    if not session:
        # Sessão expirada
        clear_session_state()
        st.error("Sessão expirada")
        st.stop()

    # Configurar RLS
    set_rls_context(engine, session['tenant_id'], session['user_id'])

    return session

def set_rls_context(engine, tenant_id, user_id):
    """Configura variáveis PostgreSQL para RLS"""
    with engine.connect() as conn:
        conn.execute(text("SET app.current_tenant_id = :tid"), {'tid': tenant_id})
        conn.execute(text("SET app.current_user_id = :uid"), {'uid': user_id})
```

---

#### **2.2 - Tela de Login (2h)**

**Arquivo: `src/multi_tenant/dashboards/login_page.py`**

**Design (copiar tema da porta 8503):**
- Background: `#0E1117` (dark)
- Card de login: `#1A1F2E` (card dark)
- Botão: `#1E90FF` (azul)
- Inputs com foco: borda azul

**Componentes:**
```python
def show_login_page():
    """Tela de login moderna"""

    # CSS customizado (tema dark)
    apply_custom_css()

    # Header
    st.markdown("# 🔐 GeniAI Analytics")
    st.caption("Sistema Multi-Tenant")

    # Formulário
    with st.form("login_form"):
        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Senha", type="password")
        submit = st.form_submit_button("🚀 Entrar")

        if submit:
            if not email or not password:
                st.error("Preencha todos os campos")
                return

            try:
                engine = get_database_engine()
                session = authenticate_user(engine, email, password)

                if session:
                    # Salvar no session_state
                    st.session_state['authenticated'] = True
                    st.session_state['session_id'] = session['session_id']
                    st.session_state['user'] = session

                    st.success(f"Bem-vindo, {session['full_name']}!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Email ou senha incorretos")

            except Exception as e:
                st.error(f"Erro: {e}")

    # Credenciais de DEV
    if ENVIRONMENT == 'development':
        show_dev_credentials()
```

---

#### **2.3 - Painel Admin (3-4h)**

**Arquivo: `src/multi_tenant/dashboards/admin_panel.py`**

**Funcionalidades:**
1. Overview geral (métricas agregadas)
2. Lista de clientes (cards clicáveis)
3. Botão "Ver Dashboard" por cliente
4. Link para gerenciar clientes (Fase 5)

```python
def show_admin_panel(session):
    """Painel de administração GeniAI"""

    st.title("🎛️ Painel Admin GeniAI")
    st.caption(f"Bem-vindo, {session['full_name']}")

    # Header com logout
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Sair"):
            logout_user(engine, session['session_id'])
            clear_session_state()
            st.rerun()

    st.divider()

    # Overview Geral
    st.subheader("📊 Overview Geral")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_tenants = count_active_tenants()
        st.metric("Clientes Ativos", total_tenants)

    with col2:
        total_conversations = count_all_conversations()
        st.metric("Conversas Totais", format_number(total_conversations))

    with col3:
        total_leads = count_all_leads()
        st.metric("Leads Totais", format_number(total_leads))

    with col4:
        conversion_rate = calculate_global_conversion_rate()
        st.metric("Taxa Conversão", format_percentage(conversion_rate))

    st.divider()

    # Lista de Clientes
    st.subheader("👥 Clientes")

    tenants = get_active_tenants()

    for tenant in tenants:
        # Skip GeniAI Admin
        if tenant['id'] == 0:
            continue

        # Card por cliente
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"### 📦 {tenant['name']}")
                st.caption(f"Slug: {tenant['slug']}")

            with col2:
                st.metric("Inboxes", len(tenant['inbox_ids']))
                st.metric("Usuários", tenant['user_count'])

            with col3:
                if st.button("📊 Ver Dashboard", key=f"dash_{tenant['id']}"):
                    # Armazenar tenant selecionado
                    st.session_state['selected_tenant_id'] = tenant['id']
                    st.rerun()

        st.divider()

    # Link para gerenciar
    st.markdown("### ⚙️ Gerenciamento")
    st.info("🚧 Gerenciar clientes será implementado na Fase 5")
```

---

#### **2.4 - Dashboard Cliente (4-5h)**

**Arquivo: `src/multi_tenant/dashboards/client_dashboard.py`**

**Estratégia:** Copiar dashboard da porta 8503 e adaptar

```python
def show_client_dashboard(session, tenant_id=None):
    """
    Dashboard do cliente (ou admin visualizando cliente específico)

    Args:
        session: Dados da sessão
        tenant_id: Se admin, pode visualizar tenant específico
    """

    # Determinar qual tenant mostrar
    if session['role'] in ['super_admin', 'admin'] and tenant_id:
        # Admin visualizando cliente específico
        display_tenant_id = tenant_id
        tenant_info = get_tenant(display_tenant_id)
        show_back_button = True  # Botão voltar ao painel
    else:
        # Cliente vendo seus próprios dados
        display_tenant_id = session['tenant_id']
        tenant_info = session
        show_back_button = False

    # Configurar RLS para o tenant correto
    set_rls_context(engine, display_tenant_id, session['user_id'])

    # Header
    col1, col2, col3 = st.columns([1, 4, 1])

    with col1:
        if show_back_button:
            if st.button("← Voltar"):
                del st.session_state['selected_tenant_id']
                st.rerun()

    with col2:
        st.title(f"📊 Analytics - {tenant_info['tenant_name']}")
        st.caption(f"👤 {session['full_name']} ({session['role']})")

    with col3:
        if st.button("🚪 Sair"):
            logout_user(engine, session['session_id'])
            clear_session_state()
            st.rerun()

    st.divider()

    # === DASHBOARD (COPIAR DA PORTA 8503) ===

    # Filtros de data
    col1, col2, col3 = st.columns([3, 1, 1])
    with col2:
        date_start = st.date_input("Início")
    with col3:
        date_end = st.date_input("Fim")

    # Carregar dados (FILTRADO por tenant_id via RLS)
    df = load_conversations(display_tenant_id, date_start, date_end)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_contacts = calculate_total_contacts(df)
        st.metric("Total Contatos", format_number(total_contacts))

    with col2:
        ai_conversations = calculate_ai_conversations(df)
        st.metric("Conversas com IA", format_number(ai_conversations))

    with col3:
        leads = calculate_leads(df)
        st.metric("Leads", format_number(leads))

    with col4:
        visits = calculate_visits_scheduled(df)
        st.metric("Visitas Agendadas", format_number(visits))

    # Gráficos (copiar da porta 8503)
    # ...
```

---

#### **2.5 - App Principal (Entry Point) (1-2h)**

**Arquivo: `src/multi_tenant/dashboards/app.py`**

**Lógica de roteamento:**

```python
def main():
    """App principal - Router"""

    # Configurar página
    st.set_page_config(
        page_title="Analytics GeniAI",
        page_icon="📊",
        layout="wide"
    )

    # Aplicar CSS tema dark
    apply_custom_css()

    # ========================================
    # ROUTER
    # ========================================

    # 1. Verificar autenticação
    if 'authenticated' not in st.session_state:
        show_login_page()
        return

    # 2. Validar sessão
    session = require_authentication()

    # 3. Decidir o que mostrar baseado no role

    # CASO 1: Super Admin ou Admin GeniAI
    if session['role'] in ['super_admin', 'admin'] and session['tenant_id'] == 0:

        # Se selecionou um cliente, mostrar dashboard
        if 'selected_tenant_id' in st.session_state:
            tenant_id = st.session_state['selected_tenant_id']
            show_client_dashboard(session, tenant_id=tenant_id)
        else:
            # Mostrar painel admin
            show_admin_panel(session)

    # CASO 2: Cliente (qualquer role em tenant != 0)
    else:
        # Ir direto para dashboard
        show_client_dashboard(session)


if __name__ == "__main__":
    main()
```

---

### Commits (Sugestão)
```bash
# Após finalizar cada módulo
git add src/multi_tenant/auth/
git commit -m "feat(auth): implement authentication module with bcrypt + sessions"

git add src/multi_tenant/dashboards/login_page.py
git commit -m "feat(ui): create login page with dark theme"

git add src/multi_tenant/dashboards/admin_panel.py
git commit -m "feat(ui): create admin panel for client selection"

git add src/multi_tenant/dashboards/client_dashboard.py
git commit -m "feat(ui): create client dashboard with RLS filtering"

git add src/multi_tenant/dashboards/app.py
git commit -m "feat(app): implement main router with role-based UX"

git add docs/multi-tenant/
git commit -m "docs: update Phase 2 strategy and add DB documentation"
```

---

### Entregáveis Finais

- ✅ Login funcional com tema dark
- ✅ Autenticação bcrypt + sessões no banco
- ✅ **Admin GeniAI:** Painel de seleção de clientes
- ✅ **Clientes:** Dashboard direto do seu tenant
- ✅ RLS configurado automaticamente
- ✅ Logout funcionando
- ✅ Documentação completa (DB_DOCUMENTATION.md)
- ✅ Base do dashboard copiada da porta 8503
- ✅ Código limpo e reutilizável

---

## 📅 FASE 3: ETL MULTI-TENANT ✅ **COMPLETA**

> **Status:** ✅ IMPLEMENTADA E VALIDADA (2025-11-06)
> **Duração Real:** ~8h total (5h implementação + 2h migração usuário + 1h validação)
> **Estimativa Inicial:** 3-4 dias (24-32h)
> **Economia:** 75% mais rápido que estimado
> **Documentação:** [FASE3_ETL_MULTI_TENANT.md](FASE3_ETL_MULTI_TENANT.md)

### Objetivos ✅
- ✅ Adaptar ETL para buscar múltiplos inboxes
- ✅ Mapear inbox_id → tenant_id
- ✅ Atualizar watermark por tenant
- ✅ Testar sincronização multi-tenant
- ✅ Documentar banco remoto (95 colunas)
- ✅ Migrar usuário integracao_user → johan_geniai
- ✅ Configurar RLS corretamente

### Resultados da Implementação
**Arquivos Criados (1.947 linhas):**
- ✅ `src/multi_tenant/etl_v4/extractor.py` (350+ linhas)
- ✅ `src/multi_tenant/etl_v4/transformer.py` (400+ linhas)
- ✅ `src/multi_tenant/etl_v4/loader.py` (369 linhas)
- ✅ `src/multi_tenant/etl_v4/watermark_manager.py` (483 linhas)
- ✅ `src/multi_tenant/etl_v4/pipeline.py` (481 linhas)
- ✅ `docs/multi-tenant/FASE3_ETL_MULTI_TENANT.md` (462 linhas)
- ✅ `docs/multi-tenant/REMOTE_DATABASE.md` (600+ linhas)
- ✅ `docs/multi-tenant/README_USUARIOS.md` (152 linhas)

**Dados Carregados (Tenant ID=1: AllpFit):**
```
Total de conversas: 1.093
Período: 25/Set/2025 - 06/Nov/2025
Últimos 30 dias: 773 conversas
Inboxes mapeados: 5 (IDs: 1, 2, 61, 64, 67)
Dashboard: ✅ Funcionando (http://localhost:8504)
```

**Configuração do Banco:**
- ✅ Usuário `johan_geniai` criado (owner)
- ✅ RLS habilitado em `conversations_analytics`
- ✅ Isaac no role `authenticated_users`
- ✅ Advisory locks implementados
- ✅ Watermark incremental funcionando

### Lições Aprendidas
1. **Verificar schema remoto primeiro** - Não assumir nomes de colunas
2. **RLS precisa de roles corretos** - Isaac precisa estar em `authenticated_users`
3. **Owner bypass RLS** - Johan_geniai (owner) não sofre bloqueio RLS
4. **Documentação é essencial** - REMOTE_DATABASE.md salvou muito tempo
5. **Chunked processing** - Evita memory errors em datasets grandes

### Tarefas

#### 3.1 - Análise da View Remota (Dia 1 - manhã)

**Verificar campos disponíveis:**
```sql
-- Conectar no banco remoto Chatwoot
SELECT DISTINCT inbox_id, inbox_name, account_id
FROM vw_conversations_analytics_final
ORDER BY inbox_id;
```

**Mapear inboxes:**
```
inbox_id | inbox_name           | tenant_id
---------|---------------------|----------
1        | AllpFit WhatsApp    | 1
2        | AllpFit Telegram    | 1
3        | Cliente XYZ WPP     | 2
4        | Cliente ABC WPP     | 3
```

#### 3.2 - Tabela de Mapeamento (Dia 1 - tarde)

```sql
CREATE TABLE inbox_tenant_mapping (
    inbox_id INTEGER PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    inbox_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, inbox_name) VALUES
(1, 1, 'AllpFit WhatsApp'),
(2, 1, 'AllpFit Telegram'),
(3, 2, 'Academia XYZ WhatsApp');
```

#### 3.3 - ETL V4 - Extractor (Dia 2)

```python
# src/multi_tenant/etl_v4/extractor.py

def extract_by_tenant(tenant_id, watermark_start=None):
    """
    Extrai dados de todos os inboxes de um tenant
    """
    # Buscar inboxes do tenant
    inbox_ids = get_tenant_inbox_ids(tenant_id)

    # Query com filtro de inbox_id
    query = f"""
        SELECT * FROM vw_conversations_analytics_final
        WHERE inbox_id = ANY(%s)
        AND conversation_updated_at > %s
        ORDER BY conversation_updated_at ASC
    """

    return execute_query(query, (inbox_ids, watermark_start))

def extract_all_tenants(watermark_start=None):
    """
    Extrai dados de TODOS os tenants (para admin)
    """
    tenants = get_active_tenants()

    all_data = []
    for tenant in tenants:
        data = extract_by_tenant(tenant.id, watermark_start)
        # Adicionar tenant_id aos dados
        for row in data:
            row['tenant_id'] = tenant.id
        all_data.extend(data)

    return all_data
```

#### 3.4 - ETL V4 - Watermark por Tenant (Dia 3)

```python
# src/multi_tenant/etl_v4/watermark_manager.py

def get_last_watermark(tenant_id=None):
    """
    Retorna último watermark
    - Se tenant_id fornecido: watermark específico do tenant
    - Se None: watermark global (para admin)
    """
    query = """
        SELECT MAX(watermark_end)
        FROM etl_control
        WHERE status = 'success'
    """

    if tenant_id:
        query += " AND tenant_id = %s"
        return execute_query(query, (tenant_id,))

    return execute_query(query)

def create_etl_execution(tenant_id, triggered_by='manual'):
    """Cria registro de execução ETL por tenant"""
    query = """
        INSERT INTO etl_control
        (tenant_id, triggered_by, status, started_at)
        VALUES (%s, %s, 'running', NOW())
        RETURNING id
    """
    return execute_query(query, (tenant_id, triggered_by))
```

#### 3.5 - Pipeline Unificado (Dia 4)

```python
# src/multi_tenant/etl_v4/pipeline.py

def run_etl_multi_tenant(tenant_id=None, force_full=False):
    """
    Executa ETL multi-tenant

    Args:
        tenant_id: Se fornecido, sincroniza apenas esse tenant
                   Se None, sincroniza TODOS os tenants
        force_full: Ignora watermark e faz full load
    """

    if tenant_id:
        # Sincronizar apenas um tenant
        tenants = [get_tenant(tenant_id)]
    else:
        # Sincronizar todos os tenants ativos
        tenants = get_active_tenants()

    for tenant in tenants:
        logger.info(f"Sincronizando tenant: {tenant.name} (ID: {tenant.id})")

        # 1. Obter watermark
        watermark = None if force_full else get_last_watermark(tenant.id)

        # 2. Extract
        data = extract_by_tenant(tenant.id, watermark)

        # 3. Transform
        data_transformed = transform_data(data)

        # 4. Load (UPSERT)
        load_upsert(data_transformed, tenant.id)

        logger.info(f"✅ Tenant {tenant.name}: {len(data)} registros sincronizados")
```

#### 3.6 - Agendamento (Cron) (Dia 4)

```bash
# Executar ETL de todos os tenants a cada hora
0 * * * * cd /home/tester/projetos/allpfit-analytics && /home/tester/projetos/allpfit-analytics/venv/bin/python src/multi_tenant/etl_v4/pipeline.py --all-tenants
```

### Commits (Próxima Etapa)
Aguardando aprovação para commit:
- `feat(etl): implement complete multi-tenant ETL pipeline (v4)`
- `feat(etl): add extractor, transformer, loader, watermark manager`
- `feat(db): migrate user integracao_user to johan_geniai`
- `fix(dashboard): add tenant_info for regular clients`
- `docs: add complete Phase 3 documentation`

### Entregáveis ✅
- ✅ ETL sincroniza múltiplos tenants
- ✅ Watermark independente por tenant
- ✅ Logs estruturados por componente
- ✅ Advisory locks para prevenir concorrência
- ✅ UPSERT com idempotência
- ✅ Documentação completa (FASE3_ETL_MULTI_TENANT.md)
- ✅ 1.093 conversas carregadas no banco
- ✅ Dashboard funcionando com dados reais

---

## 📅 FASE 4: DASHBOARD CLIENTE (2-3 dias)

### Objetivos
- Adaptar dashboard atual para multi-tenant
- Filtrar dados automaticamente pelo tenant logado
- Personalização por cliente (logo, cores, nome)
- Métricas específicas do cliente

### Tarefas

#### 4.1 - Refatoração do Dashboard (Dia 1)

**Arquitetura:**
```
src/multi_tenant/dashboards/
├── __init__.py
├── login.py              # Tela de login
├── client_dashboard.py   # Dashboard do cliente
├── admin_dashboard.py    # Dashboard admin (Fase 5)
└── components/
    ├── header.py         # Header personalizado
    ├── metrics.py        # Cards de métricas
    └── charts.py         # Gráficos
```

**Modificações principais:**
```python
# src/multi_tenant/dashboards/client_dashboard.py
import streamlit as st
from multi_tenant.auth.middleware import require_authentication

# Autenticação obrigatória
session = require_authentication()
tenant_id = session['tenant_id']
tenant_name = session['tenant_name']
user_name = session['user_name']

# Header personalizado
st.title(f"📊 Analytics {tenant_name}")
st.caption(f"Bem-vindo, {user_name}!")

# Carregar dados APENAS do tenant
@st.cache_data(ttl=300)
def load_tenant_data(tenant_id):
    query = """
        SELECT * FROM conversations_analytics
        WHERE tenant_id = %s
        ORDER BY conversation_date DESC
    """
    return execute_query(query, (tenant_id,))

df = load_tenant_data(tenant_id)

# Resto do dashboard igual (KPIs, gráficos, tabelas)
```

#### 4.2 - Personalização por Tenant (Dia 2)

**Tabela de configurações:**
```sql
CREATE TABLE tenant_configs (
    tenant_id INTEGER PRIMARY KEY REFERENCES tenants(id),
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#1E40AF',
    secondary_color VARCHAR(7) DEFAULT '#10B981',
    custom_css TEXT,
    features JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO tenant_configs (tenant_id, logo_url, primary_color) VALUES
(1, 'https://allpfit.com.br/logo.png', '#FF6B35');
```

**Aplicar personalização:**
```python
def apply_tenant_branding(tenant_id):
    """Aplica cores e logo do tenant"""
    config = get_tenant_config(tenant_id)

    st.markdown(f"""
        <style>
        :root {{
            --primary-color: {config.primary_color};
            --secondary-color: {config.secondary_color};
        }}
        </style>
    """, unsafe_allow_html=True)

    if config.logo_url:
        st.image(config.logo_url, width=200)
```

#### 4.3 - Testes de Isolamento (Dia 3)

```python
# tests/multi_tenant/test_dashboard.py

def test_tenant_data_isolation():
    """Verifica que cliente só vê seus dados"""
    # Login como tenant_id = 1
    session = authenticate_user("isaac@allpfit.com.br", "password")

    # Carregar dados
    df = load_tenant_data(session['tenant_id'])

    # Verificar que TODOS os registros são do tenant correto
    assert all(df['tenant_id'] == 1)
    assert 1 not in df['tenant_id'].unique()  # Não deve ter dados de outros tenants
```

### Commits
- `refactor(dashboard): adapt for multi-tenant`
- `feat(dashboard): add tenant branding customization`
- `feat(dashboard): add tenant-specific header`
- `test(dashboard): add data isolation tests`

### Entregáveis
- ✅ Dashboard filtra automaticamente por tenant
- ✅ Personalização visual por cliente
- ✅ Testes de isolamento passando

---

## 📅 FASE 5: DASHBOARD ADMIN (2-3 dias)

### Objetivos
- Dashboard central GeniAI
- Visão consolidada de todos os clientes
- Gerenciamento de tenants e usuários
- Métricas agregadas

### Tarefas

#### 5.1 - Dashboard Admin (Dia 1-2)

**Funcionalidades:**
```python
# src/multi_tenant/dashboards/admin_dashboard.py

def show_admin_dashboard():
    st.title("🎛️ GeniAI - Painel Admin")

    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview Geral",
        "👥 Clientes",
        "📈 Métricas Agregadas",
        "⚙️ Configurações"
    ])

    with tab1:
        show_overview_geral()

    with tab2:
        show_clients_management()

    with tab3:
        show_aggregated_metrics()

    with tab4:
        show_system_settings()
```

**Overview Geral:**
```python
def show_overview_geral():
    """Métricas consolidadas de todos os clientes"""

    # KPIs agregados
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_tenants = count_active_tenants()
        st.metric("Clientes Ativos", total_tenants)

    with col2:
        total_conversations = count_all_conversations()
        st.metric("Conversas Totais", format_number(total_conversations))

    with col3:
        total_leads = count_all_leads()
        st.metric("Leads Totais", format_number(total_leads))

    with col4:
        conversion_rate = calculate_global_conversion_rate()
        st.metric("Taxa Conversão Global", format_percentage(conversion_rate))

    # Tabela de clientes
    st.subheader("📋 Clientes")
    tenants_df = get_tenants_summary()
    st.dataframe(tenants_df)

    # Gráfico: Conversas por Cliente
    st.subheader("📊 Distribuição de Conversas por Cliente")
    chart_data = get_conversations_by_tenant()
    st.bar_chart(chart_data)
```

**Gerenciamento de Clientes:**
```python
def show_clients_management():
    """CRUD de clientes"""

    st.subheader("➕ Adicionar Novo Cliente")

    with st.form("new_tenant_form"):
        name = st.text_input("Nome do Cliente")
        slug = st.text_input("Slug (URL-friendly)")
        inbox_ids = st.text_input("Inbox IDs (separados por vírgula)")
        plan = st.selectbox("Plano", ["basic", "pro", "enterprise"])

        submitted = st.form_submit_button("Criar Cliente")

        if submitted:
            create_tenant(name, slug, inbox_ids.split(','), plan)
            st.success(f"✅ Cliente {name} criado com sucesso!")
            st.rerun()

    # Listar clientes existentes
    st.subheader("📋 Clientes Existentes")
    tenants = get_all_tenants()

    for tenant in tenants:
        with st.expander(f"{tenant.name} (ID: {tenant.id})"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Status:** {tenant.status}")
                st.write(f"**Plano:** {tenant.plan}")
                st.write(f"**Inboxes:** {tenant.inbox_ids}")

            with col2:
                if st.button("🗑️ Deletar", key=f"delete_{tenant.id}"):
                    delete_tenant(tenant.id)
                    st.rerun()

                if st.button("⚙️ Configurar", key=f"config_{tenant.id}"):
                    st.session_state.editing_tenant = tenant.id
```

**Métricas Agregadas:**
```python
def show_aggregated_metrics():
    """Análises cross-tenant"""

    st.subheader("📈 Performance Comparativa")

    # Comparar conversão por cliente
    df = pd.DataFrame([
        {
            'Cliente': t.name,
            'Conversas': count_conversations(t.id),
            'Leads': count_leads(t.id),
            'Taxa Conversão': calculate_conversion_rate(t.id)
        }
        for t in get_active_tenants()
    ])

    st.dataframe(df)

    # Gráfico comparativo
    fig = px.bar(df, x='Cliente', y='Taxa Conversão',
                 title='Taxa de Conversão por Cliente')
    st.plotly_chart(fig)
```

#### 5.2 - Controle de Acesso (Dia 2)

```python
def require_admin():
    """Middleware para páginas admin"""
    session = require_authentication()

    if session['user_role'] not in ['admin', 'super_admin']:
        st.error("🚫 Acesso negado. Área exclusiva para administradores.")
        st.stop()

    return session
```

#### 5.3 - Logs e Auditoria (Dia 3)

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tenant_id INTEGER REFERENCES tenants(id),
    action VARCHAR(100),    -- 'create_tenant', 'delete_user', etc
    entity_type VARCHAR(50), -- 'tenant', 'user', 'config'
    entity_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);
```

```python
def log_admin_action(user_id, action, entity_type, entity_id, new_value):
    """Registra ações de admin"""
    query = """
        INSERT INTO audit_logs
        (user_id, action, entity_type, entity_id, new_value)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (user_id, action, entity_type, entity_id, new_value))
```

### Commits
- `feat(admin): create admin dashboard overview`
- `feat(admin): add client management interface`
- `feat(admin): implement aggregated metrics`
- `feat(admin): add audit logging`
- `feat(admin): add access control middleware`

### Entregáveis
- ✅ Dashboard admin funcional
- ✅ CRUD de clientes
- ✅ Métricas agregadas
- ✅ Sistema de auditoria

---

## 📅 FASE 6: TESTES E DEPLOY (2-3 dias)

### Objetivos
- Testes de integração completos
- Testes de segurança (isolamento)
- Documentação de deploy
- Deploy em staging/produção

### Tarefas

#### 6.1 - Testes de Integração (Dia 1)

```python
# tests/multi_tenant/test_integration.py

def test_full_flow_client():
    """Testa fluxo completo do cliente"""
    # 1. Login
    session = authenticate_user("isaac@allpfit.com.br", "password")
    assert session is not None
    assert session['tenant_id'] == 1

    # 2. Carregar dashboard
    df = load_tenant_data(session['tenant_id'])
    assert not df.empty
    assert all(df['tenant_id'] == 1)

    # 3. Calcular métricas
    metrics = calculate_metrics(df)
    assert 'total_conversations' in metrics

    # 4. Logout
    destroy_session(session['session_id'])
    assert validate_session(session['session_id']) is None

def test_full_flow_admin():
    """Testa fluxo completo do admin"""
    # 1. Login como admin
    session = authenticate_user("admin@geniai.com.br", "admin_password")
    assert session['user_role'] == 'super_admin'

    # 2. Criar novo tenant
    tenant_id = create_tenant("Academia Teste", "academia-teste", [10, 11], "basic")
    assert tenant_id is not None

    # 3. Criar usuário para o tenant
    user_id = create_user(tenant_id, "teste@academia.com", "password123", "Usuário Teste")
    assert user_id is not None

    # 4. Verificar isolamento
    # Login como novo usuário
    new_session = authenticate_user("teste@academia.com", "password123")
    df = load_tenant_data(new_session['tenant_id'])

    # Deve estar vazio (novo tenant sem dados)
    assert df.empty or all(df['tenant_id'] == tenant_id)

    # 5. Deletar tenant de teste
    delete_tenant(tenant_id)
```

#### 6.2 - Testes de Segurança (Dia 1)

```python
# tests/multi_tenant/test_security.py

def test_sql_injection_protection():
    """Verifica proteção contra SQL injection"""
    malicious_email = "'; DROP TABLE users; --"

    user = authenticate_user(malicious_email, "password")
    assert user is None  # Não deve crashar, apenas retornar None

    # Verificar que tabela ainda existe
    result = execute_query("SELECT COUNT(*) FROM users")
    assert result is not None

def test_session_hijacking_protection():
    """Verifica proteção contra session hijacking"""
    session1 = create_session(1, 1)

    # Tentar usar sessão expirada
    time.sleep(2)
    # Forçar expiração
    execute_query("UPDATE sessions SET expires_at = NOW() - INTERVAL '1 hour' WHERE id = %s", (session1,))

    # Deve falhar validação
    assert validate_session(session1) is None

def test_tenant_data_leakage():
    """Verifica que não há vazamento de dados entre tenants"""
    # Login como tenant 1
    session1 = authenticate_user("isaac@allpfit.com.br", "password")
    df1 = load_tenant_data(session1['tenant_id'])

    # Login como tenant 2
    session2 = authenticate_user("cliente2@teste.com", "password")
    df2 = load_tenant_data(session2['tenant_id'])

    # Verificar que não há interseção de dados
    assert set(df1['conversation_id']).isdisjoint(set(df2['conversation_id']))
```

#### 6.3 - Documentação de Deploy (Dia 2)

**Criar guia de deploy:**
```markdown
# docs/multi-tenant/05_DEPLOYMENT.md

## Pré-requisitos
- PostgreSQL 14+
- Python 3.11+
- Servidor Linux (Ubuntu 22.04 recomendado)

## 1. Setup do Banco de Dados

```bash
# Criar banco
sudo -u postgres psql -c "CREATE DATABASE geniai_analytics;"

# Executar migrations
psql -d geniai_analytics -f sql/multi_tenant/01_create_database.sql
psql -d geniai_analytics -f sql/multi_tenant/02_create_schema.sql
psql -d geniai_analytics -f sql/multi_tenant/03_seed_data.sql
psql -d geniai_analytics -f sql/multi_tenant/05_row_level_security.sql
```

## 2. Variáveis de Ambiente

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@localhost/geniai_analytics
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
```

## 3. Systemd Service

```ini
# /etc/systemd/system/geniai-analytics.service
[Unit]
Description=GeniAI Multi-Tenant Analytics Dashboard
After=network.target postgresql.service

[Service]
Type=simple
User=tester
WorkingDirectory=/home/tester/projetos/allpfit-analytics
Environment="PATH=/home/tester/projetos/allpfit-analytics/venv/bin"
ExecStart=/home/tester/projetos/allpfit-analytics/venv/bin/streamlit run src/multi_tenant/dashboards/app.py --server.port=8501

[Install]
WantedBy=multi-user.target
```

## 4. Cron Job ETL

```bash
# crontab -e
0 * * * * cd /home/tester/projetos/allpfit-analytics && /home/tester/projetos/allpfit-analytics/venv/bin/python src/multi_tenant/etl_v4/pipeline.py --all-tenants >> logs/etl_multi_tenant.log 2>&1
```

## 5. Nginx Reverse Proxy (Opcional)

```nginx
server {
    listen 80;
    server_name analytics.geniai.com.br;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```
```

#### 6.4 - Deploy Staging (Dia 2-3)

```bash
# 1. Criar banco staging
sudo -u postgres createdb geniai_analytics_staging

# 2. Rodar migrations
./scripts/deploy_staging.sh

# 3. Seed dados de teste
python scripts/seed_test_data.py

# 4. Iniciar serviço
streamlit run src/multi_tenant/dashboards/app.py --server.port=8502

# 5. Testes manuais
# - Login como cliente
# - Login como admin
# - Verificar isolamento de dados
# - Testar ETL
```

#### 6.5 - Deploy Produção (Dia 3)

```bash
# Checklist de produção
[ ] Backup do banco atual (allpfit)
[ ] Criar banco geniai_analytics
[ ] Executar todas as migrations
[ ] Migrar dados existentes
[ ] Seed usuários e tenants
[ ] Configurar variáveis de ambiente
[ ] Atualizar systemd service
[ ] Atualizar cron job ETL
[ ] Testar autenticação
[ ] Testar isolamento de dados
[ ] Verificar logs
[ ] Monitoring (Grafana/Prometheus)
```

### Commits
- `test: add integration tests`
- `test: add security tests`
- `docs: add deployment guide`
- `chore: add systemd service file`
- `chore: update cron jobs for production`

### Entregáveis
- ✅ Todos os testes passando
- ✅ Documentação de deploy completa
- ✅ Deploy em staging validado
- ✅ Deploy em produção realizado

---

## 🔄 PROCESSO DE DESENVOLVIMENTO

### Workflow Git

```bash
# 1. Criar branch para cada fase
git checkout -b feature/fase-1-database
# ... desenvolver ...
git add .
git commit -m "feat(db): implement multi-tenant schema"
git push origin feature/fase-1-database

# 2. Merge na branch principal do projeto
git checkout feature/multi-tenant-system
git merge feature/fase-1-database
git push origin feature/multi-tenant-system

# 3. Criar branch para próxima fase
git checkout -b feature/fase-2-auth
```

### Commits Semânticos

Seguir padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix bug
refactor(scope): refactor code
test(scope): add tests
docs(scope): update documentation
chore(scope): update build tasks, configs
```

**Exemplos:**
- `feat(auth): implement bcrypt password hashing`
- `feat(db): add row-level security policies`
- `fix(etl): correct tenant_id mapping in extractor`
- `refactor(dashboard): extract metrics to separate module`
- `test(security): add tenant isolation tests`
- `docs(deploy): add production deployment guide`

### Code Review Checklist

Antes de cada commit/merge:
- [ ] Código testado localmente
- [ ] Testes unitários passando
- [ ] Sem credenciais hardcoded
- [ ] Logs adequados
- [ ] Documentação atualizada
- [ ] Sem TODOs pendentes críticos

---

## 📊 MÉTRICAS DE SUCESSO

### Técnicas
- ✅ 100% dos testes passando
- ✅ Isolamento de dados validado (RLS funcionando)
- ✅ ETL sincronizando todos os tenants sem erros
- ✅ Tempo de resposta < 2s para dashboards
- ✅ Zero downtime na migração

### Funcionais
- ✅ Clientes conseguem logar e ver apenas seus dados
- ✅ Admin consegue gerenciar todos os clientes
- ✅ Dados sincronizados em tempo real (1h delay máximo)
- ✅ Personalização visual por cliente funcionando

### Negócio
- ✅ Sistema escalável para +10 clientes
- ✅ Onboarding de novo cliente < 30 minutos
- ✅ Redução de custos operacionais (1 servidor para N clientes)

---

## 🚨 RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Vazamento de dados entre tenants | Média | Alto | RLS + testes de isolamento rigorosos |
| Performance degradada com muitos tenants | Baixa | Médio | Índices otimizados + particionamento futuro |
| Migração de dados falhar | Baixa | Alto | Backup completo + dry-run em staging |
| ETL multi-tenant falhar | Média | Alto | Logs detalhados + rollback automático |
| Autenticação quebrar | Baixa | Alto | Testes de segurança + sessões com TTL |

---

## 📚 PRÓXIMOS PASSOS (Pós-Lançamento)

### Fase 7: Otimizações (Opcional)
- Particionamento de tabelas por tenant
- Cache Redis para queries frequentes
- API REST para integrações
- Webhooks para notificações

### Fase 8: Features Avançadas (Futuro)
- Exportação de relatórios PDF/Excel
- Agendamento de relatórios por email
- Alertas customizados por cliente
- Dashboard mobile (PWA)
- Integração com Google Analytics
- Multi-idioma (i18n)

---

## 📞 SUPORTE

**Dúvidas ou problemas durante desenvolvimento?**
- Revisar documentação em `/docs/multi-tenant/`
- Consultar logs em `/logs/`
- Verificar testes em `/tests/multi_tenant/`

---

**Última atualização:** 2025-11-04
**Versão:** 1.0
**Status:** 🟢 Em Desenvolvimento - Fase 0 Completa