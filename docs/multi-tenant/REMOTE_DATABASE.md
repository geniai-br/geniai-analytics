# 🌐 DOCUMENTAÇÃO DO BANCO REMOTO - Chatwoot

> **Banco:** `chatwoot`
> **Host:** 178.156.206.184:5432
> **User:** hetzner_hyago_read
> **Tipo:** PostgreSQL (Read-Only)
> **Última Verificação:** 2025-11-06 (Fase 3 - ETL Multi-Tenant)

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Credenciais de Acesso](#credenciais-de-acesso)
3. [View Principal](#view-principal-vw_conversations_analytics_final)
4. [Inboxes do AllpFit](#inboxes-do-allpfit)
5. [Mapeamento de Colunas](#mapeamento-de-colunas)
6. [Colunas Ausentes](#colunas-ausentes)
7. [Queries de Teste](#queries-de-teste)

---

## 🎯 VISÃO GERAL

### Propósito
Banco de dados do Chatwoot hospedado em servidor remoto Hetzner, contendo:
- Conversas de todos os clientes
- Múltiplos inboxes (WhatsApp, Telegram, Instagram, etc)
- Dados agregados e calculados em views

### Arquitetura
```
┌────────────────────────────────────────┐
│  SERVIDOR REMOTO: 178.156.206.184     │
├────────────────────────────────────────┤
│  DATABASE: chatwoot                    │
│                                        │
│  VIEW: vw_conversations_analytics_final│
│  • 95 colunas calculadas               │
│  • Métricas pré-agregadas              │
│  • CSAT e NPS                          │
│  • Análise temporal                    │
│                                        │
│  🔒 Read-Only Access                   │
│     (hetzner_hyago_read)               │
└────────────────────────────────────────┘
```

---

## 🔐 CREDENCIAIS DE ACESSO

### Conexão PostgreSQL (Read-Only)
```bash
Host: 178.156.206.184
Port: 5432
Database: chatwoot
User: hetzner_hyago_read
Password: c1d46b41391f
```

### String de Conexão
```python
# SQLAlchemy
REMOTE_DATABASE_URL = "postgresql://hetzner_hyago_read:c1d46b41391f@178.156.206.184:5432/chatwoot"

# psql CLI
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -p 5432 -U hetzner_hyago_read -d chatwoot
```

### Variável de Ambiente (.env)
```bash
REMOTE_DB_HOST=178.156.206.184
REMOTE_DB_PORT=5432
REMOTE_DB_NAME=chatwoot
REMOTE_DB_USER=hetzner_hyago_read
REMOTE_DB_PASSWORD=c1d46b41391f
```

---

## 📊 VIEW PRINCIPAL: vw_conversations_analytics_final

### Informações Gerais
- **Nome:** `public.vw_conversations_analytics_final`
- **Total de Colunas:** 95
- **Tipo:** View (Materialized ou Regular)
- **Atualização:** Contínua (dados em tempo real)

### Estrutura Completa (95 colunas)

#### 1. Identificadores (12 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| conversation_id | integer | 🔑 ID único da conversa |
| display_id | integer | ID de exibição (sequencial) |
| conversation_uuid | uuid | UUID único |
| account_id | integer | ID da conta no Chatwoot |
| inbox_id | integer | 🔑 ID do inbox (para filtrar por tenant) |
| contact_id | bigint | ID do contato |
| assignee_id | integer | ID do atendente |
| team_id | bigint | ID do time |
| campaign_id | bigint | ID da campanha |
| client_sender_id | bigint | ID do sender do cliente |
| csat_response_id | bigint | ID da resposta CSAT |

#### 2. Timestamps (11 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| conversation_created_at | timestamp | Data de criação da conversa |
| conversation_updated_at | timestamp | Última atualização |
| last_activity_at | timestamp | Última atividade |
| first_reply_created_at | timestamp | Primeira resposta |
| waiting_since | timestamp | Aguardando desde |
| contact_last_seen_at | timestamp | Último acesso do contato |
| agent_last_seen_at | timestamp | Último acesso do agente |
| mc_first_message_at | timestamp | Primeira mensagem |
| mc_last_message_at | timestamp | Última mensagem |
| csat_created_at | timestamp | CSAT criado em |
| snoozed_until | timestamp | Adiado até |

#### 3. Informações de Contato (5 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| contact_name | varchar | Nome do contato |
| contact_email | varchar | Email do contato |
| contact_phone | varchar | 📞 Telefone do contato |
| contact_identifier | varchar | Identificador único |
| client_phone | varchar | Telefone do cliente |

#### 4. Informações do Inbox (4 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| inbox_name | varchar | Nome do inbox |
| inbox_channel_type | varchar | Tipo (WhatsApp, Telegram, etc) |
| inbox_timezone | varchar | Timezone do inbox |
| account_name | varchar | Nome da conta |

#### 5. Informações de Atendimento (6 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| assignee_name | varchar | Nome do atendente |
| assignee_email | varchar | Email do atendente |
| team_name | varchar | Nome do time |
| status | integer | Status (0=open, 1=resolved, 2=pending) |
| priority | integer | Prioridade (0-3) |
| priority_label | text | Label da prioridade |

#### 6. Métricas de Mensagens (11 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| t_messages | bigint | Total de mensagens |
| total_messages_public | bigint | Mensagens públicas |
| total_messages_private | bigint | Mensagens privadas (notas) |
| user_messages_count | bigint | Mensagens do atendente |
| contact_messages_count | bigint | Mensagens do contato |
| private_notes_count | bigint | Notas privadas |
| first_message_text | text | Texto da primeira mensagem |
| last_message_text | text | Texto da última mensagem |
| first_message_sender_type | varchar | Tipo do sender (contact/user) |
| last_message_sender_type | varchar | Tipo do último sender |
| message_compiled | jsonb | 📋 Mensagens compiladas (JSON) |

#### 7. Métricas Temporais (7 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| first_response_time_seconds | integer | TMA (Tempo Médio de Atendimento) |
| first_response_time_minutes | numeric | TMA em minutos |
| resolution_time_seconds | integer | Tempo de resolução |
| waiting_time_seconds | integer | Tempo de espera |
| conversation_duration_seconds | integer | Duração total da conversa |
| avg_time_between_messages_seconds | numeric | Tempo médio entre mensagens |
| avg_message_length | integer | Tamanho médio de mensagem |

#### 8. CSAT e Satisfação (5 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| csat_rating | integer | Nota CSAT (1-5) |
| csat_feedback | text | Feedback textual |
| csat_nps_category | text | Categoria NPS (promotor/neutro/detrator) |
| csat_sentiment_category | text | Sentimento (positivo/negativo) |
| has_csat | boolean | Possui avaliação? |

#### 9. Flags Booleanas (32 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| is_assigned | boolean | Possui atendente? |
| has_team | boolean | Possui time? |
| is_resolved | boolean | ✅ Resolvida? |
| is_open | boolean | Aberta? |
| is_pending | boolean | Pendente? |
| is_snoozed | boolean | Adiada? |
| has_contact | boolean | Possui contato? |
| is_waiting | boolean | Aguardando? |
| has_priority | boolean | Possui prioridade? |
| is_high_priority | boolean | Alta prioridade? |
| is_from_campaign | boolean | De campanha? |
| is_fast_response | boolean | Resposta rápida? |
| is_slow_response | boolean | Resposta lenta? |
| is_fast_resolution | boolean | Resolução rápida? |
| is_waiting_long | boolean | Esperando há muito tempo? |
| contact_has_seen | boolean | Contato visualizou? |
| agent_has_seen | boolean | Agente visualizou? |
| has_written_feedback | boolean | Possui feedback escrito? |
| has_detailed_feedback | boolean | Possui feedback detalhado? |
| has_user_messages | boolean | Possui mensagens do atendente? |
| has_contact_messages | boolean | Possui mensagens do contato? |
| has_private_notes | boolean | Possui notas privadas? |
| has_contact_reply | boolean | Contato respondeu? |
| is_short_conversation | boolean | Conversa curta? |
| is_long_conversation | boolean | Conversa longa? |
| has_human_intervention | boolean | 🤖 Teve intervenção humana? |
| is_bot_resolved | boolean | 🤖 Resolvida por bot? |

#### 10. Campos Temporais Calculados (8 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| conversation_date | date | Data da conversa (DATE) |
| conversation_year | integer | Ano |
| conversation_month | integer | Mês (1-12) |
| conversation_day | integer | Dia (1-31) |
| conversation_day_of_week | integer | Dia da semana (0=dom, 6=sáb) |
| conversation_hour | integer | Hora (0-23) |
| conversation_minute | integer | Minuto (0-59) |
| conversation_week_of_year | integer | Semana do ano (1-53) |

#### 11. Outros (5 colunas)
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| priority_score | integer | Score de prioridade |
| status_label_pt | text | Status em português |
| user_message_ratio | numeric | Proporção de mensagens do atendente |
| contact_message_ratio | numeric | Proporção de mensagens do contato |
| max_message_length | integer | Tamanho máximo de mensagem |

---

## 📦 INBOXES DO ALLPFIT

### Identificados no Banco Remoto

| Inbox ID | Nome | Account | Total Conversas | Período |
|----------|------|---------|-----------------|---------|
| 61 | allpfitjpsulcloud1 | Allp Fit JP Sul | 139 | 2025-10-27 a 2025-11-06 |
| 64 | allpfitjpsulrecepcao | Allp Fit JP Sul | 429 | 2025-10-27 a 2025-11-06 |
| 67 | allpfitjpsulcloud2 | Allp Fit JP Sul | 1 | 2025-10-28 |

**Total:** 569 conversas do AllpFit

### Query de Identificação
```sql
SELECT DISTINCT inbox_id, inbox_name, account_name
FROM vw_conversations_analytics_final
WHERE inbox_name ILIKE '%allp%' OR account_name ILIKE '%allp%'
ORDER BY inbox_id;
```

---

## 🗺️ MAPEAMENTO DE COLUNAS

### De Remoto → Local (conversations_analytics)

| Coluna Local | Coluna Remota | Transformação |
|--------------|---------------|---------------|
| conversation_id | conversation_id | Direto |
| conversation_display_id | display_id | Direto |
| inbox_id | inbox_id | Direto |
| inbox_name | inbox_name | Direto |
| contact_id | contact_id | Direto |
| contact_name | contact_name | Direto |
| contact_phone | contact_phone OU client_phone | Coalesce |
| contact_email | contact_email | Direto |
| conversation_created_at | conversation_created_at | Direto |
| conversation_updated_at | conversation_updated_at | Direto |
| conversation_date | conversation_date | Direto |
| first_message_at | mc_first_message_at | Direto |
| last_message_at | mc_last_message_at | Direto |
| total_messages | t_messages | Direto |
| contact_messages | contact_messages_count | Direto |
| agent_messages | user_messages_count | Direto |
| bot_messages | (calculado) | Se has_human_intervention=false |
| human_messages | (calculado) | Se has_human_intervention=true |
| conversation_status | status_label_pt | Direto |
| conversation_label | (NULL) | ⚠️ Não disponível |
| is_lead | (NULL) | ⚠️ **PROBLEMA: Não existe!** |
| visit_scheduled | (NULL) | ⚠️ **PROBLEMA: Não existe!** |
| crm_converted | (NULL) | ⚠️ **PROBLEMA: Não existe!** |
| ai_analysis_status | (NULL) | ⚠️ Não disponível |
| ai_probability_label | (NULL) | ⚠️ Não disponível |
| ai_probability_score | (NULL) | ⚠️ Não disponível |

---

## ⚠️ COLUNAS AUSENTES (Críticas para Dashboard)

### Problema Identificado
As seguintes colunas **NÃO EXISTEM** na view remota, mas são **ESSENCIAIS** para o dashboard:

1. **`is_lead`** (BOOLEAN) - Identifica se é um lead qualificado
2. **`visit_scheduled`** (BOOLEAN) - Identifica se agendou visita
3. **`crm_converted`** (BOOLEAN) - Identifica se converteu no CRM
4. **`ai_probability_label`** (VARCHAR) - Classificação por IA
5. **`ai_probability_score`** (NUMERIC) - Score de probabilidade

### Soluções Propostas

#### Opção 1: Usar Proxies Temporários ⭐ (Recomendado para Fase 3)
```python
# transformer.py
def transform_data(row):
    return {
        # ... outros campos ...

        # Proxies temporários (até criar lógica real)
        'is_lead': row.get('is_resolved', False),  # Proxy: resolvida = lead
        'visit_scheduled': False,  # Sempre False por enquanto
        'crm_converted': False,  # Sempre False por enquanto
        'ai_analysis_status': None,
        'ai_probability_label': None,
        'ai_probability_score': None
    }
```

#### Opção 2: Criar Análise Pós-ETL (Futuro)
- Analisar `message_compiled` (JSONB) para identificar padrões
- Buscar palavras-chave ("agendar", "visita", "quando posso ir")
- Classificar com IA/ML após sync

#### Opção 3: Atualizar View Remota (Requer Acesso Write)
```sql
-- ⚠️ Requer permissão de escrita no banco remoto
ALTER VIEW vw_conversations_analytics_final ADD COLUMN is_lead BOOLEAN;
```

---

## 🧪 QUERIES DE TESTE

### 1. Testar Conexão
```bash
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -p 5432 -U hetzner_hyago_read -d chatwoot -c "SELECT version();"
```

### 2. Listar Inboxes Disponíveis
```sql
SELECT DISTINCT
    inbox_id,
    inbox_name,
    account_name,
    COUNT(*) as total_conversations
FROM vw_conversations_analytics_final
GROUP BY inbox_id, inbox_name, account_name
ORDER BY total_conversations DESC;
```

### 3. Testar Extração de 10 Conversas
```sql
SELECT
    conversation_id,
    inbox_id,
    inbox_name,
    contact_name,
    contact_phone,
    conversation_created_at,
    t_messages,
    is_resolved
FROM vw_conversations_analytics_final
WHERE inbox_id IN (61, 64, 67)
ORDER BY conversation_created_at DESC
LIMIT 10;
```

### 4. Verificar Período de Dados
```sql
SELECT
    inbox_id,
    inbox_name,
    MIN(conversation_created_at) as primeira_conversa,
    MAX(conversation_created_at) as ultima_conversa,
    COUNT(*) as total
FROM vw_conversations_analytics_final
WHERE inbox_id IN (61, 64, 67)
GROUP BY inbox_id, inbox_name;
```

### 5. Estatísticas de Mensagens
```sql
SELECT
    inbox_id,
    AVG(t_messages) as avg_messages,
    MAX(t_messages) as max_messages,
    AVG(user_messages_count) as avg_agent_messages,
    AVG(contact_messages_count) as avg_contact_messages,
    COUNT(CASE WHEN has_human_intervention THEN 1 END) as com_humano,
    COUNT(CASE WHEN is_bot_resolved THEN 1 END) as resolvida_bot
FROM vw_conversations_analytics_final
WHERE inbox_id IN (61, 64, 67)
GROUP BY inbox_id;
```

---

## 🚀 PRÓXIMOS PASSOS

### Para Fase 3 - ETL Multi-Tenant
1. ✅ Popular `inbox_tenant_mapping` com (61, 64, 67 → tenant_id=1)
2. ✅ Implementar extractor que busca esses 3 inboxes
3. ✅ Usar proxies temporários para `is_lead`, `visit_scheduled`, `crm_converted`
4. ✅ Documentar limitação das colunas ausentes

### Para Fase 4 - Dashboard (Futuro)
1. ⚠️ Implementar análise de texto em `message_compiled` (JSONB)
2. ⚠️ Classificar leads com base em padrões
3. ⚠️ Criar modelo de ML para `ai_probability_score`

---

## 📊 PERFORMANCE

### Latência da Conexão
- **Ping:** ~10-50ms (mesmo datacenter)
- **Query simples:** ~100-300ms
- **Query complexa:** ~1-3s

### Recomendações
- ✅ Usar LIMIT em queries de teste
- ✅ Processar dados em chunks (10k linhas por vez)
- ✅ Evitar JOINs desnecessários (view já tem tudo)
- ✅ Cachear mapeamento de inboxes

---

## 📞 REFERÊNCIAS RÁPIDAS

### Comandos PostgreSQL Úteis
```bash
# Conectar
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -p 5432 -U hetzner_hyago_read -d chatwoot

# Listar views
\dv

# Descrever view
\d+ vw_conversations_analytics_final

# Sair
\q
```

### Arquivos Relacionados
- [00_CRONOGRAMA_MASTER.md](./00_CRONOGRAMA_MASTER.md) - Plano completo
- [DB_DOCUMENTATION.md](./DB_DOCUMENTATION.md) - Banco local
- [RECOMENDACOES_FASE3.md](./RECOMENDACOES_FASE3.md) - Guia Fase 3

---

**Última atualização:** 2025-11-06
**Criado por:** Isaac (via Claude Code)
**Status:** ✅ Banco Remoto Verificado - Pronto para ETL
