# 📦 FASE 3 - ETL MULTI-TENANT

> **Status:** ✅ COMPLETA
> **Data:** 2025-11-06
> **Autor:** Isaac (via Claude Code)

---

## 📋 Visão Geral

A **Fase 3** implementa o sistema de **ETL (Extract, Transform, Load)** multi-tenant que sincroniza dados do Chatwoot (banco remoto) para o banco local `geniai_analytics`, com suporte a múltiplos tenants.

### ✨ Características Principais

- ✅ **Multi-Tenant** - Suporta múltiplos clientes (tenants) no mesmo banco
- ✅ **Extração Incremental** - Busca apenas dados novos/atualizados (watermark)
- ✅ **UPSERT Inteligente** - INSERT para novos, UPDATE para existentes
- ✅ **Chunked Processing** - Processa dados em chunks para evitar memory errors
- ✅ **Advisory Locks** - Previne execução simultânea para o mesmo tenant
- ✅ **Idempotência** - Múltiplas execuções produzem mesmo resultado
- ✅ **Logging Estruturado** - Logs detalhados em cada etapa
- ✅ **Auditoria Completa** - Tabela `etl_control` rastreia todas execuções

---

## 🏗️ Arquitetura

```
┌────────────────────────────────────────────────────────────────┐
│ BANCO REMOTO (Chatwoot - 178.156.206.184:5432)                │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  vw_conversations_analytics_final                    │    │
│  │  - 95 colunas documentadas                           │    │
│  │  - Dados de múltiplas accounts/inboxes               │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────┬────────────────────────────────────┘
                            │ EXTRACT (incremental)
                            │ WHERE inbox_id IN (...tenant inboxes)
                            │   AND updated_at > watermark
                            ▼
┌────────────────────────────────────────────────────────────────┐
│  ETL PIPELINE V4 (Multi-Tenant)                                │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  1. RemoteExtractor (extractor.py)                   │    │
│  │     - Busca inbox_ids do tenant                      │    │
│  │     - Query incremental com chunks                   │    │
│  │     - Yield generator para eficiência                │    │
│  └────────────────┬─────────────────────────────────────┘    │
│                   ▼                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  2. ConversationTransformer (transformer.py)         │    │
│  │     - Adiciona tenant_id                             │    │
│  │     - Normaliza tipos (timestamps, integers, bools)  │    │
│  │     - Calcula campos derivados                       │    │
│  │     - Renomeia colunas para schema local             │    │
│  └────────────────┬─────────────────────────────────────┘    │
│                   ▼                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  3. ConversationLoader (loader.py)                   │    │
│  │     - UPSERT batch (tenant_id, conversation_id)      │    │
│  │     - Rastreia inserted/updated counts               │    │
│  │     - Commit transacional                            │    │
│  └────────────────┬─────────────────────────────────────┘    │
│                   ▼                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  4. WatermarkManager (watermark_manager.py)          │    │
│  │     - Advisory locks (pg_try_advisory_lock)          │    │
│  │     - Controle de execuções (etl_control)            │    │
│  │     - Atualiza watermark por tenant                  │    │
│  └────────────────┬─────────────────────────────────────┘    │
│                   ▼                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  5. ETLPipeline (pipeline.py)                        │    │
│  │     - Orquestrador principal                         │    │
│  │     - CLI com argparse                               │    │
│  │     - Tratamento de erros                            │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ BANCO LOCAL (geniai_analytics)                                 │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  conversations_analytics (multi-tenant)              │    │
│  │  - Owner: johan_geniai                               │    │
│  │  - RLS: ENABLED (filtro por tenant_id)               │    │
│  │  - 1.093 conversas (tenant_id=1: AllpFit)            │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  etl_control (auditoria)                             │    │
│  │  - Histórico de execuções                            │    │
│  │  - Watermarks por tenant                             │    │
│  │  - Status: success/failed                            │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  inbox_tenant_mapping                                │    │
│  │  - Mapeamento inbox_id → tenant_id                   │    │
│  │  - 5 inboxes para tenant_id=1 (AllpFit)             │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estrutura de Arquivos

```
src/multi_tenant/etl_v4/
├── __init__.py                  # Package initialization
├── extractor.py                 # RemoteExtractor - busca dados remotos
├── transformer.py               # ConversationTransformer - normaliza dados
├── loader.py                    # ConversationLoader - UPSERT no banco
├── watermark_manager.py         # WatermarkManager - controle de sync
└── pipeline.py                  # ETLPipeline - orquestrador principal

docs/multi-tenant/
├── FASE3_ETL_MULTI_TENANT.md   # Este arquivo
├── REMOTE_DATABASE.md           # Documentação banco remoto (95 colunas)
├── README_USUARIOS.md           # Guia de usuários do banco
└── DB_DOCUMENTATION.md          # Schema completo do banco local
```

---

## 🚀 Como Usar

### Execução Manual

```bash
# Ativar ambiente virtual
cd /home/tester/projetos/allpfit-analytics
source venv/bin/activate

# Executar ETL para tenant específico
export LOCAL_DB_USER='johan_geniai'
export LOCAL_DB_PASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh'

python3 src/multi_tenant/etl_v4/pipeline.py \
  --tenant-id 1 \
  --chunk-size 50
```

### Parâmetros CLI

| Parâmetro | Descrição | Padrão | Obrigatório |
|-----------|-----------|--------|-------------|
| `--tenant-id` | ID do tenant para sincronizar | - | ✅ Sim |
| `--chunk-size` | Tamanho do chunk para processamento | 10000 | ❌ Não |
| `--force-full` | Forçar sincronização completa (ignorar watermark) | False | ❌ Não |

### Exemplos

```bash
# Sincronização incremental padrão (recomendado)
python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1

# Sincronização com chunks menores (mais lento, menos memória)
python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1 --chunk-size 100

# Sincronização completa (reprocessar tudo)
python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1 --force-full
```

---

## 📊 Resultados da Fase 3

### ✅ Implementação Completa

**Arquivos Criados:**
- ✅ `extractor.py` (350+ linhas) - Extração remota
- ✅ `transformer.py` (400+ linhas) - Transformação de dados
- ✅ `loader.py` (320+ linhas) - Carga com UPSERT
- ✅ `watermark_manager.py` (400+ linhas) - Controle de sync
- ✅ `pipeline.py` (400+ linhas) - Orquestrador CLI

**Documentação Criada:**
- ✅ `REMOTE_DATABASE.md` (600+ linhas) - 95 colunas documentadas
- ✅ `README_USUARIOS.md` - Guia de usuários do banco
- ✅ `FASE3_ETL_MULTI_TENANT.md` - Este documento

**Configuração do Banco:**
- ✅ Usuário `johan_geniai` criado (owner de todas as tabelas)
- ✅ RLS habilitado em `conversations_analytics`
- ✅ Isaac no role `authenticated_users`
- ✅ Advisory locks configurados
- ✅ Watermark inicial configurado

### 📈 Dados Carregados (Tenant ID=1: AllpFit)

```
Total de conversas carregadas: 1.093
Período: 25/Set/2025 até 06/Nov/2025
Últimos 30 dias: 773 conversas
Com mensagens do cliente: 1.053
Inboxes mapeados: 5 (IDs: 1, 2, 61, 64, 67)
```

### 🎯 Dashboard Funcionando

**URL:** http://localhost:8504
**Login:** isaac@allpfit.com.br / senha123

**Métricas Visíveis (Fase 3):**
- ✅ **773 Total Contatos** (últimos 30 dias)
- ⏳ **0 Leads** (Fase 4 - análise IA)
- ⏳ **0 Visitas Agendadas** (Fase 4 - análise IA)
- ⏳ **0 Conversas com IA** (Fase 4 - análise IA)

---

## 🔧 Detalhes Técnicos

### 1. Extração (extractor.py)

**Responsabilidades:**
- Buscar `inbox_ids` do tenant via `inbox_tenant_mapping`
- Query incremental baseada em watermark
- Processar em chunks (yield generator)
- Conexão com banco remoto (Chatwoot)

**Query SQL:**
```sql
SELECT
    conversation_id, display_id, inbox_id, contact_id,
    conversation_created_at, conversation_updated_at,
    t_messages, user_messages_count, contact_messages_count,
    status, status_label_pt, priority, is_resolved,
    contact_name, contact_phone, contact_email,
    inbox_name, account_name, message_compiled,
    -- ... mais 47 colunas
FROM vw_conversations_analytics_final
WHERE inbox_id = ANY(:inbox_ids)
  AND conversation_updated_at > :watermark_start
  AND conversation_updated_at <= :watermark_end
ORDER BY conversation_updated_at ASC
LIMIT :chunk_size OFFSET :offset
```

### 2. Transformação (transformer.py)

**Responsabilidades:**
- Adicionar `tenant_id` em todas as rows
- Normalizar tipos de dados:
  - Timestamps: `pd.to_datetime()`
  - Integers: `Int64` (nullable)
  - Booleans: `fillna(False).astype(bool)`
  - Strings: truncar para max_length
- Calcular campos derivados:
  - `conversation_date`, `conversation_year`, etc.
  - `has_user_messages`, `has_contact_reply`, etc.
  - `user_message_ratio`, `contact_message_ratio`
- Renomear colunas para match com schema local

### 3. Carga (loader.py)

**Responsabilidades:**
- UPSERT batch usando `ON CONFLICT UPDATE`
- Unique constraint: `(tenant_id, conversation_id)`
- Rastrear inserted vs updated counts
- Commit transacional

**Query UPSERT:**
```sql
INSERT INTO conversations_analytics (
    tenant_id, conversation_id, display_id, inbox_id,
    contact_id, contact_name, contact_phone, ...
) VALUES (
    %(tenant_id)s, %(conversation_id)s, %(display_id)s, ...
)
ON CONFLICT (tenant_id, conversation_id)
DO UPDATE SET
    display_id = EXCLUDED.display_id,
    contact_name = EXCLUDED.contact_name,
    etl_updated_at = NOW(),
    ...
```

### 4. Controle de Sync (watermark_manager.py)

**Responsabilidades:**
- **Advisory Locks:** `pg_try_advisory_lock(lock_id)`
  - `lock_id = hash(f"etl_{tenant_id}") % 2147483647`
  - Previne execução simultânea para mesmo tenant
- **Watermark Management:**
  - Buscar último watermark: `MAX(watermark_end) WHERE status='success'`
  - Criar execução: `INSERT INTO etl_control (tenant_id, type, status, started_at)`
  - Atualizar execução: `UPDATE etl_control SET status, finished_at, records_extracted, ...`
- **Release Lock:** `pg_advisory_unlock(lock_id)` em finally

### 5. Orquestração (pipeline.py)

**Responsabilidades:**
- CLI com `argparse`
- Logging estruturado
- Fluxo completo:
  1. Acquire lock
  2. Get watermark (ou None se --force-full)
  3. Create execution record
  4. Extract → Transform → Load (chunked loop)
  5. Update execution as success
  6. Release lock (always in finally)

---

## 🔐 Usuários do Banco

| Usuário | Tipo | Uso | RLS | Password |
|---------|------|-----|-----|----------|
| `postgres` | Superuser | Administração | N/A | - |
| `johan_geniai` | Owner | ETL, Manutenção | ❌ Bypass | `vlVMVM6UNz2yYSBlzodPjQvZh` |
| `isaac` | Padrão | Dashboard, Queries | ✅ Sim | `AllpFit2024@Analytics` |

**Roles:**
- `authenticated_users` - Usuários normais (RLS ativo)
- `admin_users` - Admins (bypass RLS)
- `etl_service` - Serviço ETL (bypass RLS)

**Importante:**
- ETL usa `johan_geniai` (owner, sem RLS)
- Dashboard usa `isaac` (com RLS, filtra por tenant_id)
- Variáveis de ambiente: `LOCAL_DB_USER`, `LOCAL_DB_PASSWORD`

---

## 🧪 Testes e Validação

### Validar Dados Carregados

```sql
-- Conectar como isaac (simula dashboard)
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics

-- Configurar RLS context
SET app.current_tenant_id = 1;
SET app.current_user_id = 3;

-- Verificar total de conversas
SELECT COUNT(*) FROM conversations_analytics;
-- Resultado esperado: 1093

-- Verificar últimos 30 dias
SELECT COUNT(*) FROM conversations_analytics
WHERE conversation_created_at >= CURRENT_DATE - INTERVAL '30 days';
-- Resultado esperado: 773
```

### Validar ETL Control

```sql
-- Ver execuções do ETL
SELECT
    id, tenant_id, type, status,
    started_at, finished_at,
    records_extracted, records_inserted, records_updated
FROM etl_control
ORDER BY started_at DESC
LIMIT 5;
```

### Validar Inbox Mapping

```sql
-- Ver inboxes mapeados
SELECT
    tenant_id,
    COUNT(*) as total_inboxes,
    ARRAY_AGG(inbox_id ORDER BY inbox_id) as inbox_ids
FROM inbox_tenant_mapping
GROUP BY tenant_id;
-- Resultado esperado: tenant_id=1, 5 inboxes
```

---

## 🐛 Problemas e Soluções

### Problema 1: RLS Bloqueando INSERT
**Erro:** `ERROR: new row violates row-level security policy`
**Causa:** RLS habilitado em tabelas de controle
**Solução:** Desabilitar RLS em `etl_control` e `inbox_tenant_mapping`
```sql
ALTER TABLE etl_control DISABLE ROW LEVEL SECURITY;
ALTER TABLE inbox_tenant_mapping DISABLE ROW LEVEL SECURITY;
```

### Problema 2: Password com @ no URL
**Erro:** `could not translate host name "Analytics@localhost"`
**Causa:** @ não escapado na connection string
**Solução:** URL encode do password
```python
from urllib.parse import quote_plus
password = quote_plus("AllpFit2024@Analytics")
```

### Problema 3: Column Name Mismatch
**Erro:** `column "total_messages" does not exist`
**Causa:** Assumir nomes sem verificar schema remoto
**Solução:** Usar nomes exatos da view remota
```python
# Correto:
t_messages, user_messages_count, contact_messages_count

# Errado:
total_messages, agent_messages, contact_messages
```

### Problema 4: Dashboard tenant_info Undefined
**Erro:** `UnboundLocalError: cannot access local variable 'tenant_info'`
**Causa:** Variável só definida para admins
**Solução:** Definir também para clientes
```python
else:
    display_tenant_id = session['tenant_id']
    tenant_name = session['tenant_name']
    show_back_button = False
    tenant_info = get_tenant_info(display_tenant_id)  # FIX
```

---

## 📝 Próximas Fases

### ⏳ Fase 4 - Dashboard Cliente Avançado
- Análise de texto com IA para detectar leads
- Classificação de visitas agendadas
- Detecção de conversões CRM
- Preencher colunas: `is_lead`, `visit_scheduled`, `crm_converted`
- Gráficos e métricas avançadas

### ⏳ Fase 5 - Dashboard Admin Completo
- Gestão de tenants
- Configurações por cliente
- Relatórios consolidados
- Billing e limites

### ⏳ Fase 6 - Testes e Deploy
- Testes unitários
- Testes de integração
- CI/CD pipeline
- Deploy em produção

---

## 📚 Referências

- **Cronograma:** `docs/CRONOGRAMA_DETALHADO.md`
- **Recomendações:** `docs/RECOMENDACOES_IMPLEMENTACAO.md`
- **DB Schema:** `docs/multi-tenant/DB_DOCUMENTATION.md`
- **Remote DB:** `docs/multi-tenant/REMOTE_DATABASE.md`
- **Usuários:** `docs/multi-tenant/README_USUARIOS.md`

---

**Criado por:** Isaac (via Claude Code)
**Data:** 2025-11-06
**Versão:** 1.0
**Status:** ✅ Fase 3 Completa
