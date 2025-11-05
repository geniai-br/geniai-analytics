# 🚀 SISTEMA MULTI-TENANT GENIAI

> **Status:** 🟢 Fase 1 Completa | 🚀 Fase 2 Pronta para Implementar
> **Última Atualização:** 2025-11-05

Transformação do AllpFit Analytics em plataforma SaaS multi-tenant para clientes da GeniAI.

---

## 🆕 INÍCIO RÁPIDO (NOVO CHAT)

**Para iniciar um novo chat e continuar o desenvolvimento:**

### 📋 Copie este Prompt:
```
Preciso implementar FASE 2 (autenticação multi-tenant) do projeto GeniAI Analytics.

Leia estes arquivos (nesta ordem):
1. docs/multi-tenant/DB_DOCUMENTATION.md
2. docs/multi-tenant/00_CRONOGRAMA_MASTER.md (seção FASE 2)
3. docs/multi-tenant/02_UX_FLOW.md

Depois, me ajude a implementar os 6 arquivos da Fase 2.

Banco: geniai_analytics | User: isaac | Pass: AllpFit2024@Analytics
```

**Ou veja o prompt completo:** [PROMPT_NOVO_CHAT.md](./PROMPT_NOVO_CHAT.md)

---

## 📚 Documentação

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| [00_CRONOGRAMA_MASTER.md](00_CRONOGRAMA_MASTER.md) | Cronograma completo do projeto (6 fases) | ✅ Completo |
| [01_ARQUITETURA_DB.md](01_ARQUITETURA_DB.md) | Arquitetura de banco de dados multi-tenant | ✅ Completo |
| 02_AUTENTICACAO.md | Sistema de autenticação e sessões | 🔜 Próximo |
| 03_ETL_DESIGN.md | Pipeline ETL multi-tenant | 📋 Planejado |
| 04_DASHBOARD_SPECS.md | Especificações UI/UX dos dashboards | 📋 Planejado |
| 05_DEPLOYMENT.md | Guia de deploy e configuração | 📋 Planejado |

---

## 🎯 Objetivo do Projeto

### Situação Atual
- Dashboard single-tenant para AllpFit
- Dados armazenados em banco único sem segregação
- Sem sistema de autenticação
- Sem isolamento de dados entre clientes

### Objetivo Final
- **Sistema Multi-Tenant SaaS**
- Dashboard personalizado por cliente
- Autenticação e controle de acesso
- Isolamento de dados (Row-Level Security)
- Painel admin para GeniAI gerenciar todos os clientes

---

## 🏗️ Arquitetura Escolhida

### Single Database + Row-Level Security (RLS)

```
┌─────────────────────────────────────────────────────────┐
│ Database: geniai_analytics                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Tenant 1    │  │  Tenant 2    │  │  Tenant N    │ │
│  │  AllpFit     │  │  Academia XYZ│  │  ...         │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                 │                  │         │
│         └─────────────────┼──────────────────┘         │
│                           │                            │
│                  ┌────────▼────────┐                   │
│                  │ conversations   │                   │
│                  │ + tenant_id     │                   │
│                  │ (RLS enabled)   │                   │
│                  └─────────────────┘                   │
│                                                         │
│  RLS Policy: WHERE tenant_id = current_tenant_id       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Por quê?**
- ✅ Simplicidade operacional (1 schema, 1 backup, 1 ETL)
- ✅ Custos reduzidos
- ✅ Queries cross-tenant para admin
- ✅ RLS garante isolamento mesmo com bugs no código

---

## 📁 Estrutura do Projeto

```
projetos/allpfit-analytics/
├── docs/multi-tenant/              # 📚 Documentação
│   ├── README.md                   # Este arquivo
│   ├── 00_CRONOGRAMA_MASTER.md    # Cronograma 6 fases
│   └── 01_ARQUITETURA_DB.md       # Database design
│
├── sql/multi_tenant/               # 💾 Scripts SQL
│   ├── 01_create_database.sql     # CREATE DATABASE geniai_analytics
│   ├── 02_create_schema.sql       # Tabelas (tenants, users, sessions, etc)
│   ├── 03_seed_data.sql           # Dados iniciais
│   ├── 04_migrate_allpfit.sql     # Migração dados AllpFit
│   └── 05_row_level_security.sql  # Políticas RLS
│
├── src/multi_tenant/               # 🐍 Código Python
│   ├── auth/                      # Autenticação
│   │   ├── password.py            # Hashing bcrypt
│   │   ├── session.py             # Gerenciamento sessões
│   │   ├── login.py               # Lógica de login
│   │   └── middleware.py          # Proteção de rotas
│   ├── models/                    # SQLAlchemy models
│   ├── etl_v4/                    # ETL multi-tenant
│   │   ├── extractor.py           # Extract por tenant
│   │   ├── transformer.py         # Transform
│   │   ├── loader.py              # Load com tenant_id
│   │   └── pipeline.py            # Orquestração
│   └── dashboards/                # Dashboards Streamlit
│       ├── login.py               # Tela de login
│       ├── client_dashboard.py    # Dashboard cliente
│       └── admin_dashboard.py     # Dashboard admin
│
└── tests/multi_tenant/            # 🧪 Testes
    ├── test_database.py           # Testes schema
    ├── test_rls.py                # Testes isolamento
    ├── test_auth.py               # Testes autenticação
    └── test_integration.py        # Testes end-to-end
```

---

## 📋 Fases do Projeto

### ✅ FASE 0: Setup e Planejamento (COMPLETO)
- [x] Análise arquitetura atual
- [x] Criação de branch `feature/multi-tenant-system`
- [x] Estrutura de pastas
- [x] Documentação inicial

### 🔜 FASE 1: Arquitetura de Dados (2-3 dias)
- [ ] Criar banco `geniai_analytics`
- [ ] Modelar schema multi-tenant
- [ ] Implementar Row-Level Security
- [ ] Migrar dados AllpFit

### 📋 FASE 2: Sistema de Autenticação (2-3 dias)
- [ ] Módulo de password hashing
- [ ] Gerenciamento de sessões
- [ ] Tela de login
- [ ] Middleware de proteção

### 📋 FASE 3: ETL Multi-Tenant (3-4 dias)
- [ ] Adaptar extractor para múltiplos inboxes
- [ ] Watermark por tenant
- [ ] Pipeline unificado
- [ ] Atualizar cron job

### 📋 FASE 4: Dashboard Cliente (2-3 dias)
- [ ] Refatorar dashboard atual
- [ ] Filtro automático por tenant
- [ ] Personalização (logo, cores)
- [ ] Testes de isolamento

### 📋 FASE 5: Dashboard Admin (2-3 dias)
- [ ] Overview geral
- [ ] Gerenciamento de clientes
- [ ] Métricas agregadas
- [ ] Sistema de auditoria

### 📋 FASE 6: Testes e Deploy (2-3 dias)
- [ ] Testes de integração
- [ ] Testes de segurança
- [ ] Deploy staging
- [ ] Deploy produção

**Total estimado:** 14-20 dias úteis

---

## 🚀 Como Começar

### 1. Ler Documentação
```bash
# Ler cronograma completo
cat docs/multi-tenant/00_CRONOGRAMA_MASTER.md

# Ler arquitetura de banco
cat docs/multi-tenant/01_ARQUITETURA_DB.md
```

### 2. Setup Ambiente
```bash
# Já estamos na branch correta
git branch  # Deve mostrar: feature/multi-tenant-system

# Instalar dependências (futuro)
pip install bcrypt psycopg2-binary streamlit-authenticator
```

### 3. Iniciar Fase 1
```bash
# Criar banco de dados
sudo -u postgres createdb geniai_analytics

# Executar scripts SQL (quando prontos)
psql -d geniai_analytics -f sql/multi_tenant/01_create_database.sql
```

---

## 🔑 Conceitos-Chave

### Row-Level Security (RLS)
Mecanismo do PostgreSQL que **filtra automaticamente** linhas de tabelas baseado em políticas.

**Exemplo:**
```sql
-- Política: usuários só veem dados do próprio tenant
CREATE POLICY tenant_isolation ON conversations_analytics
FOR ALL TO authenticated_users
USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- Mesmo que desenvolvedor esqueça WHERE, RLS protege!
SELECT * FROM conversations_analytics;
-- Retorna APENAS linhas do tenant_id da sessão
```

### Multi-Tenancy
Arquitetura onde **múltiplos clientes (tenants)** compartilham a mesma aplicação e infraestrutura, mas seus dados são **logicamente isolados**.

**Benefícios:**
- 💰 Redução de custos (1 servidor para N clientes)
- 🔧 Manutenção simplificada (1 codebase)
- 📊 Análises cross-tenant possíveis (admin)

### Tenant
Cliente da GeniAI que possui um ou mais **inboxes** no Chatwoot.

**Exemplo:**
- Tenant: "AllpFit CrossFit" (tenant_id=1)
  - Inbox 1: WhatsApp Principal
  - Inbox 2: Telegram

---

## 📊 Modelo de Dados Resumido

```
tenants (clientes)
├── id
├── name ("AllpFit CrossFit")
├── slug ("allpfit")
├── inbox_ids ([1, 2])
└── status (active, suspended, cancelled)

users (usuários de cada tenant)
├── id
├── tenant_id → tenants.id
├── email
├── password_hash
├── role (client, admin, super_admin)
└── is_active

conversations_analytics (dados)
├── conversation_id
├── tenant_id → tenants.id  ← NOVO!
├── inbox_id
├── ... (121 colunas existentes)
└── RLS: WHERE tenant_id = current_tenant_id
```

---

## 🔒 Segurança

### Níveis de Proteção

1. **RLS (Row-Level Security)** ← Principal
   - PostgreSQL filtra automaticamente
   - Não depende de código da aplicação
   - Mesmo com SQL injection, dados isolados

2. **Middleware de Autenticação**
   - Verifica sessão antes de qualquer query
   - Configura `current_tenant_id` no PostgreSQL
   - Logs de auditoria

3. **Bcrypt Password Hashing**
   - Senhas nunca armazenadas em plain text
   - Salt aleatório por senha
   - Computacionalmente caro (dificulta brute force)

4. **Session Management**
   - UUID aleatórios (impossível adivinhar)
   - Expiração automática (24h)
   - IP tracking para detecção de hijacking

---

## 🧪 Testes

### Estratégia de Testes

```python
# 1. Testes de Isolamento
def test_tenant_isolation():
    """Garante que Tenant A não vê dados de Tenant B"""
    # Login como Tenant A
    # Verificar COUNT(*) == dados apenas de A

# 2. Testes de Autenticação
def test_login_with_valid_credentials():
    """Login com credenciais válidas deve criar sessão"""

# 3. Testes de ETL
def test_etl_multi_tenant():
    """ETL deve sincronizar todos os tenants"""

# 4. Testes de Performance
def test_dashboard_load_time():
    """Dashboard deve carregar em < 2s"""
```

---

## 📈 Métricas de Sucesso

### Técnicas
- [x] Documentação completa (Fase 0)
- [ ] 100% dos testes passando
- [ ] Isolamento de dados validado (RLS)
- [ ] Tempo de resposta < 2s

### Funcionais
- [ ] Clientes conseguem logar
- [ ] Cada cliente vê apenas seus dados
- [ ] Admin consegue gerenciar todos os clientes
- [ ] ETL sincroniza múltiplos tenants

### Negócio
- [ ] Onboarding novo cliente < 30min
- [ ] Sistema escalável para 10+ clientes
- [ ] Redução de custos operacionais

---

## 🤝 Workflow de Desenvolvimento

### Git Flow

```bash
# Sempre trabalhar na branch feature
git checkout feature/multi-tenant-system

# Commits frequentes e descritivos
git add <files>
git commit -m "feat(auth): implement bcrypt password hashing"

# Push apenas quando estável
git push origin feature/multi-tenant-system

# Quando finalizar projeto: merge para main
git checkout main
git merge feature/multi-tenant-system
```

### Conventional Commits

```
feat(scope):     Nova funcionalidade
fix(scope):      Correção de bug
refactor(scope): Refatoração
test(scope):     Testes
docs(scope):     Documentação
chore(scope):    Config, build, etc
```

---

## 🆘 Troubleshooting

### Problema: RLS não está filtrando dados
```sql
-- Verificar se RLS está habilitado
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';

-- Verificar policies
\d+ conversations_analytics

-- Verificar role e tenant_id da sessão
SHOW ROLE;
SELECT current_setting('app.current_tenant_id');
```

### Problema: Migração de dados falhou
```bash
# Verificar se tabelas existem
psql -d geniai_analytics -c "\dt"

# Comparar contagens
psql -d allpfit -c "SELECT COUNT(*) FROM conversas_analytics;"
psql -d geniai_analytics -c "SELECT COUNT(*) FROM conversations_analytics;"

# Restaurar backup
psql -d geniai_analytics < backup.sql
```

---

## 📞 Contato e Suporte

**Desenvolvedor:** Isaac (via Claude Code)
**Documentação:** `/docs/multi-tenant/`
**Branch:** `feature/multi-tenant-system`
**Status:** 🟢 Fase 0 Completa - Iniciando Fase 1

---

**Última atualização:** 2025-11-04
**Versão:** 1.0.0
**Status do Projeto:** 🚀 Em Desenvolvimento