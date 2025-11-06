# 🚀 RECOMENDAÇÕES PARA A FASE 3 - ETL MULTI-TENANT

> **Criado em:** 2025-11-06
> **Baseado em:** Lições aprendidas da Fase 2
> **Objetivo:** Guiar implementação da Fase 3 com base em experiências anteriores

---

## 📋 VISÃO GERAL

A Fase 3 é a mais complexa até agora, pois envolve:
- Integração com banco remoto (Chatwoot)
- Lógica de ETL multi-tenant
- Watermark por tenant
- Criação/atualização de views remotas

**Complexidade:** 🔴 Alta

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

### 1. Acesso ao Banco Remoto
- [ ] Confirmar credenciais do banco Chatwoot
- [ ] Testar conexão remota (`psql -h <host> -U <user> -d chatwoot_production`)
- [ ] Verificar permissões (SELECT na view)
- [ ] Documentar latência da conexão (importante para ETL)

### 2. View Remota
- [ ] Verificar se `vw_conversations_analytics_final` existe
- [ ] Listar todas as colunas disponíveis (`\d+ vw_conversations_analytics_final`)
- [ ] Verificar se possui colunas necessárias:
  - `is_lead` (BOOLEAN)
  - `visit_scheduled` (BOOLEAN)
  - `crm_converted` (BOOLEAN)
  - `ai_probability_label` (VARCHAR)
  - `ai_probability_score` (NUMERIC)
- [ ] Se não existir, criar/atualizar a view

### 3. Dados de Teste
- [ ] Identificar inbox_ids do AllpFit (tenant_id = 1)
- [ ] Verificar quantidade de conversas por inbox
- [ ] Calcular volume de dados para estimar tempo de sync

---

## 🎯 RECOMENDAÇÕES BASEADAS NA FASE 2

### 1. **Logging Desde o Início** ⭐

**Lição da Fase 2:** Tivemos que refatorar 40+ `print()` para `logger`.

**Recomendação:**
```python
# ETL multi_tenant/etl_v4/extractor.py
import logging
logger = logging.getLogger(__name__)

# Usar logo de cara:
logger.info(f"Iniciando ETL para tenant {tenant_id}")
logger.warning(f"Watermark não encontrado para tenant {tenant_id}, fazendo full sync")
logger.error(f"Erro ao extrair dados: {str(e)}")
```

**Benefícios:**
- ✅ Fácil debug em produção
- ✅ Logs estruturados desde o início
- ✅ Não precisa refatorar depois

---

### 2. **Não Assumir Estrutura do Banco** ⭐

**Lição da Fase 2:** Queries esperavam `is_lead`, mas coluna não existia.

**Recomendação:**
```python
# SEMPRE verificar antes de usar:
def check_remote_columns():
    """Verifica colunas disponíveis na view remota"""
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'vw_conversations_analytics_final'
    """
    # ...listar e documentar
```

**Ação:**
1. Criar script `verify_remote_schema.py`
2. Listar todas as colunas disponíveis
3. Documentar diferenças vs. schema esperado
4. Criar view/função se necessário

---

### 3. **Watermark Seguro (Evitar Duplicatas)** ⭐

**Problema Potencial:** ETL executar 2x ao mesmo tempo → duplicatas

**Recomendação:**
```python
# src/multi_tenant/etl_v4/watermark_manager.py

def acquire_etl_lock(tenant_id):
    """
    Trava ETL para evitar execução simultânea
    
    Usa advisory lock do PostgreSQL
    """
    query = text("""
        SELECT pg_try_advisory_lock(:lock_id)
    """)
    
    lock_id = hash(f"etl_{tenant_id}") % 2147483647  # INT máximo
    
    with engine.connect() as conn:
        result = conn.execute(query, {'lock_id': lock_id}).scalar()
        
        if not result:
            raise Exception(f"ETL já está rodando para tenant {tenant_id}")
    
    return lock_id

def release_etl_lock(lock_id):
    """Libera trava"""
    query = text("SELECT pg_advisory_unlock(:lock_id)")
    # ...
```

**Uso:**
```python
try:
    lock = acquire_etl_lock(tenant_id)
    # ... executar ETL ...
finally:
    release_etl_lock(lock)
```

---

### 4. **RLS - Lembrar de Desabilitar em Tabelas de Controle**

**Lição da Fase 2:** RLS bloqueou `sessions`, perdemos 2h debugando.

**Recomendação:**
```sql
-- Tabelas de controle ETL NÃO devem ter RLS
ALTER TABLE etl_control DISABLE ROW LEVEL SECURITY;
ALTER TABLE inbox_tenant_mapping DISABLE ROW LEVEL SECURITY;
```

**Motivo:** ETL precisa acessar dados de TODOS os tenants sem filtro.

---

### 5. **Cache de Metadados (Performance)**

**Problema Potencial:** Queries de mapeamento (inbox → tenant) a cada execução

**Recomendação:**
```python
@st.cache_resource(ttl=3600)  # Cache de 1h
def get_inbox_tenant_mapping():
    """Carrega mapeamento inbox → tenant (cachado)"""
    query = text("""
        SELECT inbox_id, tenant_id, inbox_name
        FROM inbox_tenant_mapping
        WHERE is_active = TRUE
    """)
    # ...retornar dict
    return {row.inbox_id: row.tenant_id for row in result}
```

**Benefícios:**
- ✅ Reduz queries desnecessárias
- ✅ ETL mais rápido
- ✅ Menos carga no banco

---

### 6. **Testes Incrementais (Não Esperar Tudo Funcionar de Uma Vez)**

**Lição da Fase 2:** Implementamos tudo e só depois testamos.

**Recomendação:**

**Passo 1:** Testar conexão remota
```python
# tests/test_remote_connection.py
def test_remote_connection():
    """Testa se consegue conectar ao banco remoto"""
    # ...
```

**Passo 2:** Testar extração de 1 inbox
```python
def test_extract_single_inbox():
    """Extrai dados de apenas 1 inbox (AllpFit)"""
    data = extract_by_inbox(inbox_id=14, limit=10)
    assert len(data) > 0
```

**Passo 3:** Testar transformação
```python
def test_transform_data():
    """Testa se transforma dados corretamente"""
    # Mock data
    # ...assert campos corretos
```

**Passo 4:** Testar load (UPSERT)
```python
def test_upsert_data():
    """Testa inserção/atualização de dados"""
    # ...
```

**Passo 5:** Testar pipeline completo
```python
def test_full_pipeline():
    """Testa ETL end-to-end"""
    # ...
```

---

### 7. **Monitoramento de Erros (Slack/Email)**

**Recomendação:**
```python
# src/multi_tenant/etl_v4/notifications.py

def notify_etl_failure(tenant_id, error_message):
    """
    Notifica falha do ETL via Slack ou Email
    
    Só em produção!
    """
    if os.getenv('ENVIRONMENT') != 'production':
        return
    
    # Slack webhook
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if webhook_url:
        payload = {
            'text': f"🚨 ETL FALHOU - Tenant {tenant_id}\n```{error_message}```"
        }
        requests.post(webhook_url, json=payload)
```

**Uso:**
```python
try:
    run_etl_multi_tenant(tenant_id)
except Exception as e:
    logger.error(f"ETL falhou: {e}")
    notify_etl_failure(tenant_id, str(e))
```

---

### 8. **Documentar TUDO (Para o Próximo Agente)**

**Lição da Fase 2:** BUG_FIX_LOGIN_RLS.md salvou horas de re-debugging.

**Recomendação:**

Criar documentos:
1. `FASE3_IMPLEMENTACAO.md` - Como foi implementado
2. `FASE3_BUGS.md` - Bugs encontrados e resolvidos
3. `ETL_MONITORING.md` - Como monitorar ETL em produção
4. `REMOTE_DATABASE.md` - Credenciais e schema do Chatwoot

---

## 🚨 ALERTAS E ARMADILHAS

### 1. **Timezone (UTC vs SP)**

**Problema:** Chatwoot usa UTC, Brasil usa UTC-3

**Solução:**
```python
from datetime import datetime, timedelta

# Converter UTC → SP
def utc_to_sp(utc_time):
    return utc_time - timedelta(hours=3)

# Converter SP → UTC
def sp_to_utc(sp_time):
    return sp_time + timedelta(hours=3)
```

**Uso:**
```python
# Watermark em UTC (para consultar banco remoto)
watermark_utc = sp_to_utc(last_sync_sp)

# Exibir para usuário em SP
last_sync_display = utc_to_sp(watermark_utc)
```

---

### 2. **Limite de Conexões (Pool Exhaustion)**

**Problema:** ETL abre muitas conexões simultâneas

**Solução:**
```python
# Configurar pool de conexões
engine_remote = create_engine(
    remote_url,
    pool_size=3,        # Máximo 3 conexões simultâneas
    max_overflow=2,     # +2 em picos
    pool_timeout=30,    # Timeout de 30s
    pool_pre_ping=True  # Verificar antes de usar
)
```

---

### 3. **Dados Grandes (Memory Error)**

**Problema:** Carregar 100k+ linhas em memória

**Solução:**
```python
# Usar chunks
def extract_in_chunks(query, chunk_size=10000):
    """Extrai dados em chunks para evitar memory error"""
    offset = 0
    
    while True:
        chunk_query = f"{query} LIMIT {chunk_size} OFFSET {offset}"
        df = pd.read_sql(chunk_query, conn)
        
        if df.empty:
            break
        
        yield df
        offset += chunk_size

# Uso:
for chunk in extract_in_chunks(query):
    load_data(chunk)
```

---

### 4. **Foreign Keys (Órfãos)**

**Problema:** Inserir conversa sem criar contato antes

**Solução:**
```python
# SEMPRE inserir na ordem correta:
# 1. Tenants (já existe)
# 2. Inboxes (mapping)
# 3. Contacts (se não existir)
# 4. Conversations (referencia contact)

# Verificar foreign keys:
def ensure_contact_exists(contact_id, contact_data):
    """Cria contato se não existir"""
    query = text("""
        INSERT INTO contacts (id, name, phone, email)
        VALUES (:id, :name, :phone, :email)
        ON CONFLICT (id) DO NOTHING
    """)
    # ...
```

---

## 📊 ESTIMATIVAS REVISADAS

| Tarefa | Estimativa Original | Estimativa Ajustada | Motivo |
|--------|-------------------|---------------------|--------|
| Análise View Remota | 4h | 2h | ✅ Scripts de verificação |
| Criar Inbox Mapping | 2h | 1h | ✅ Simples |
| Extractor Multi-Tenant | 8h | 6h | ✅ Código base ETL V3 |
| Watermark por Tenant | 4h | 3h | ✅ Lógica conhecida |
| Pipeline Unificado | 6h | 6h | ⚠️ Complexidade mantida |
| Testes | 4h | 6h | ⚠️ Aumentado (mais crítico) |
| **Total** | 28h | 24h | ✅ Otimizado |

**Estimativa Final:** 3 dias (24h) - ✅ Mantida

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Dia 1: Setup e Análise
- [ ] Testar conexão com banco remoto
- [ ] Verificar schema da view remota
- [ ] Criar script `verify_remote_schema.py`
- [ ] Documentar colunas disponíveis
- [ ] Criar `inbox_tenant_mapping` (seed data)
- [ ] Escrever queries de extração (draft)

### Dia 2: Implementação Core
- [ ] Implementar `extractor.py` (buscar dados remotos)
- [ ] Implementar `transformer.py` (normalizar dados)
- [ ] Implementar `loader.py` (UPSERT local)
- [ ] Implementar `watermark_manager.py` (controle de sync)
- [ ] Testes unitários de cada módulo

### Dia 3: Pipeline e Testes
- [ ] Implementar `pipeline.py` (orquestrador)
- [ ] Implementar locks (evitar execução simultânea)
- [ ] Testes de integração (end-to-end)
- [ ] Executar ETL para AllpFit (tenant_id=1)
- [ ] Validar dados no dashboard (Fase 2)
- [ ] Documentar processo em `FASE3_IMPLEMENTACAO.md`

---

## 🎯 CRITÉRIOS DE SUCESSO

A Fase 3 estará completa quando:

1. ✅ ETL sincroniza dados do AllpFit (tenant_id=1)
2. ✅ Watermark funciona (apenas dados novos na 2ª execução)
3. ✅ Dashboard mostra dados reais (não mais vazio)
4. ✅ Queries não retornam zero (is_lead, visit_scheduled)
5. ✅ Logs estruturados funcionando
6. ✅ Testes passando (unit + integration)
7. ✅ Documentação completa

---

## 📚 REFERÊNCIAS

- ETL V3 Atual: `/home/tester/projetos/allpfit-analytics/src/etl_v3/`
- Fase 2 Completa: `/home/tester/projetos/allpfit-analytics/src/multi_tenant/`
- Lições Aprendidas: `FASE2_MELHORIAS.md`
- Bug RLS: `BUG_FIX_LOGIN_RLS.md`
- Cronograma: `00_CRONOGRAMA_MASTER.md`

---

**Criado em:** 2025-11-06
**Baseado em:** Fase 2 (lições aprendidas)
**Status:** 📋 Guia de Implementação - Pronto para Fase 3
