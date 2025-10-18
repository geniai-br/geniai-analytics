# 🚀 Estratégia de Performance - Views do Chatwoot

## ❌ PROBLEMA: View Monolítica (Gigante)

### **Desvantagens da abordagem atual (1 view gigante):**

1. **Performance Ruim**
   - 80+ colunas sendo calculadas SEMPRE
   - Múltiplos JOINs (7+ tabelas)
   - Agregações pesadas (jsonb_agg, contadores)
   - Subconsultas correlacionadas
   - **Resultado**: Query lenta mesmo quando você só quer 3 campos

2. **Uso Ineficiente de Recursos**
   - Banco processa TUDO mesmo se você só precisa de status
   - Cache ineficiente (muitos dados diferentes juntos)
   - Índices não otimizados

3. **Difícil Manutenção**
   - Query gigante = difícil debugar
   - Mudança em 1 campo = recriar tudo
   - Difícil identificar gargalos

4. **Problemas de Escalabilidade**
   - Com 10k, 50k, 100k conversas = query fica MUITO lenta
   - Scan completo da tabela messages
   - Memória do banco explodir

---

## ✅ SOLUÇÃO: Arquitetura de Views Modulares

### **Abordagem Recomendada: CAMADAS DE VIEWS**

```
┌─────────────────────────────────────────────────────┐
│  CAMADA 1: Views Base (Simples, Rápidas)           │
│  - Dados diretos das tabelas                        │
│  - Mínimo de JOINs                                  │
│  - Indexadas                                        │
└─────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  CAMADA 2: Views Intermediárias (Agregações)       │
│  - Usam views da Camada 1                          │
│  - Agregações específicas                          │
│  - Métricas calculadas                             │
└─────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  CAMADA 3: Views Analíticas (Dashboard)            │
│  - Juntam Camadas 1 e 2                            │
│  - Apenas para relatórios                          │
│  - Podem ser MATERIALIZED                          │
└─────────────────────────────────────────────────────┘
```

---

## 📐 ARQUITETURA PROPOSTA

### **CAMADA 1: Views Base (Simples e Rápidas)**

#### **1.1. vw_conversations_base**
```sql
-- Apenas dados diretos da tabela conversations + JOINs simples
-- SEM agregações pesadas
SELECT
    c.id,
    c.display_id,
    c.account_id,
    c.inbox_id,
    c.status,
    c.contact_id,
    c.assignee_id,
    c.team_id,
    c.created_at,
    c.updated_at,
    c.priority,
    -- Informações do contato (1 JOIN)
    cont.name as contact_name,
    cont.email as contact_email,
    cont.phone_number as contact_phone,
    -- Informações do inbox (1 JOIN)
    i.name as inbox_name,
    i.channel_type as inbox_type,
    -- Informações do agente (1 JOIN)
    u.name as assignee_name
FROM conversations c
LEFT JOIN contacts cont ON cont.id = c.contact_id
LEFT JOIN inboxes i ON i.id = c.inbox_id
LEFT JOIN users u ON u.id = c.assignee_id;
```
**Performance**: ⚡⚡⚡ MUITO RÁPIDA (apenas JOINs simples, sem agregação)

---

#### **1.2. vw_messages_compiled**
```sql
-- A view ORIGINAL que já funciona bem!
-- Apenas o JSON de mensagens
SELECT
    conversation_id,
    jsonb_agg(...) AS message_compiled,
    client_sender_id,
    inbox_id,
    client_phone,
    count(*) AS t_messages
FROM messages m
GROUP BY conversation_id;
```
**Performance**: ⚡⚡ RÁPIDA (já existe e funciona)

---

#### **1.3. vw_csat_base**
```sql
-- Apenas respostas CSAT
SELECT
    conversation_id,
    rating,
    feedback_message,
    created_at as rated_at
FROM csat_survey_responses;
```
**Performance**: ⚡⚡⚡ MUITO RÁPIDA (simples, sem JOIN)

---

### **CAMADA 2: Views de Métricas (Agregações Específicas)**

#### **2.1. vw_conversation_metrics**
```sql
-- Métricas calculadas por conversa
SELECT
    c.id as conversation_id,

    -- Tempo de resposta
    EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at))
        as first_response_seconds,

    -- Flags booleanos
    (c.status IN ('resolved', 'closed')) as is_resolved,
    (c.assignee_id IS NOT NULL) as is_assigned,

    -- Metadados temporais
    c.created_at::date as conversation_date,
    EXTRACT(HOUR FROM c.created_at) as conversation_hour,
    EXTRACT(DOW FROM c.created_at) as day_of_week

FROM conversations c;
```
**Performance**: ⚡⚡⚡ RÁPIDA (cálculos simples, sem JOIN)

---

#### **2.2. vw_message_stats**
```sql
-- Estatísticas de mensagens por conversa
SELECT
    m.conversation_id,

    -- Contadores
    COUNT(*) FILTER (WHERE sender_type = 'User') as user_msg_count,
    COUNT(*) FILTER (WHERE sender_type = 'Contact') as contact_msg_count,

    -- Primeira e última mensagem
    MIN(m.created_at) as first_message_at,
    MAX(m.created_at) as last_message_at,

    -- Duração
    EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) as duration_seconds

FROM messages m
WHERE m.private = false
GROUP BY m.conversation_id;
```
**Performance**: ⚡⚡ MÉDIA (agregação, mas sem JOIN)

---

### **CAMADA 3: Views Analíticas (Para Dashboard)**

#### **3.1. vw_conversations_analytics (Completa mas Modular)**
```sql
-- Junta TODAS as camadas anteriores
SELECT
    cb.*,                    -- Dados base
    mc.message_compiled,     -- Mensagens
    mc.t_messages,
    csat.rating,            -- CSAT
    csat.feedback_message,
    cm.first_response_seconds,  -- Métricas
    cm.is_resolved,
    ms.user_msg_count,      -- Stats de mensagens
    ms.contact_msg_count,
    ms.duration_seconds
FROM vw_conversations_base cb
LEFT JOIN vw_messages_compiled mc ON mc.conversation_id = cb.id
LEFT JOIN vw_csat_base csat ON csat.conversation_id = cb.id
LEFT JOIN vw_conversation_metrics cm ON cm.conversation_id = cb.id
LEFT JOIN vw_message_stats ms ON ms.conversation_id = cb.id;
```
**Performance**: ⚡⚡ MÉDIA (JOINs de views, mas cada view já está otimizada)

---

### **CAMADA 4: Materialized Views (Para Dashboards)**

#### **4.1. mvw_daily_summary (MATERIALIZADA)**
```sql
-- View MATERIALIZADA que é RECALCULADA periodicamente
CREATE MATERIALIZED VIEW mvw_daily_summary AS
SELECT
    conversation_date,
    inbox_name,
    status,
    COUNT(*) as total_conversations,
    AVG(first_response_seconds) as avg_response_time,
    COUNT(*) FILTER (WHERE csat.rating IS NOT NULL) as total_rated,
    AVG(csat.rating) as avg_rating
FROM vw_conversations_analytics
GROUP BY conversation_date, inbox_name, status;

-- Refresh periódico (via cron ou manualmente)
REFRESH MATERIALIZED VIEW mvw_daily_summary;
```
**Performance**: ⚡⚡⚡ **INSTANTÂNEA!** (dados pré-calculados)

---

## 📊 COMPARAÇÃO DE ABORDAGENS

| Abordagem | Performance | Manutenção | Escalabilidade | Flexibilidade |
|-----------|-------------|------------|----------------|---------------|
| **1 View Gigante** | ❌ Lenta | ❌ Difícil | ❌ Ruim | ⚠️ Média |
| **Views Modulares** | ✅ Rápida | ✅ Fácil | ✅ Excelente | ✅ Alta |
| **Materialized Views** | ✅✅ Muito Rápida | ⚠️ Média | ✅ Ótima | ❌ Baixa |
| **Tabela Cache Local** | ✅✅✅ Instantânea | ✅ Fácil | ✅✅ Perfeita | ✅ Alta |

---

## 🎯 RECOMENDAÇÃO FINAL

### **Estratégia Híbrida (Melhor dos 2 Mundos):**

```
┌─────────────────────────────────────────────────────┐
│  BANCO REMOTO (Chatwoot - Source)                  │
│  ┌───────────────────────────────────────────────┐ │
│  │ CAMADA 1: Views Base (Simples)                │ │
│  │ - vw_conversations_base                       │ │
│  │ - vw_messages_compiled                        │ │
│  │ - vw_csat_base                                │ │
│  └───────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │ CAMADA 2: Views de Métricas                   │ │
│  │ - vw_conversation_metrics                     │ │
│  │ - vw_message_stats                            │ │
│  └───────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │ CAMADA 3: View Analítica (Junção)             │ │
│  │ - vw_conversations_analytics                  │ │
│  │   (Junta todas as anteriores)                 │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                       ▼ ETL extrai 1x por dia/hora
┌─────────────────────────────────────────────────────┐
│  BANCO LOCAL (PostgreSQL Local)                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ TABELA: conversas_analytics                   │ │
│  │ - Dados PRÉ-CALCULADOS                        │ │
│  │ - Indexada para dashboard                     │ │
│  │ - Refresh periódico via ETL                   │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  Dashboard Streamlit consulta DAQUI ⚡⚡⚡          │
└─────────────────────────────────────────────────────┘
```

---

## 🔥 VANTAGENS DA ESTRATÉGIA HÍBRIDA

1. **No Banco Remoto:**
   - ✅ Views modulares = fácil manutenção
   - ✅ Cada view otimizada para seu propósito
   - ✅ Pode consultar individualmente (rápido)
   - ✅ Fácil debugar e testar

2. **No Banco Local:**
   - ✅✅✅ Dashboard INSTANTÂNEO (sem lag)
   - ✅ Não sobrecarrega banco remoto
   - ✅ Pode adicionar índices customizados
   - ✅ Pode ter agregações extras
   - ✅ Dados sempre disponíveis mesmo se remoto cair

3. **ETL Pipeline:**
   - ✅ Extrai 1x por hora ou 1x por dia
   - ✅ Processa incremental (só dados novos)
   - ✅ Pode aplicar transformações
   - ✅ Fácil de monitorar

---

## 💡 RECOMENDAÇÃO PRÁTICA

### **FASE 1: Começar Simples**
```sql
-- Criar apenas 2 views:
1. vw_conversations_base     (dados simples, rápida)
2. vw_messages_compiled      (já existe, manter)

-- ETL extrai e junta no banco local
-- Dashboard consulta banco local
```

### **FASE 2: Adicionar Métricas**
```sql
-- Criar views de métricas:
3. vw_conversation_metrics
4. vw_message_stats

-- ETL atualizado para usar todas
```

### **FASE 3: View Completa (se necessário)**
```sql
-- Criar view analítica que junta tudo:
5. vw_conversations_analytics

-- ETL pode usar esta ou as individuais
```

---

## 🎯 MINHA RECOMENDAÇÃO FINAL

**NÃO crie a view gigante no banco remoto!**

**FAÇA:**
1. ✅ Crie 4-5 views modulares simples no banco remoto
2. ✅ ETL extrai dessas views e junta no banco local
3. ✅ Dashboard consulta banco local
4. ✅ Refresh periódico (1x por hora ou tempo real se necessário)

**POR QUÊ?**
- ⚡ Performance: Dashboard instantâneo
- 🛡️ Proteção: Não sobrecarrega banco de produção
- 🔧 Flexibilidade: Fácil adicionar campos
- 📈 Escalabilidade: Suporta milhões de registros

---

## 📝 PRÓXIMO PASSO

Quer que eu crie:
1. **As 4-5 views modulares otimizadas**? ✅ RECOMENDADO
2. **Script SQL para criar todas de uma vez**?
3. **Atualizar o ETL para usar a estratégia modular**?

