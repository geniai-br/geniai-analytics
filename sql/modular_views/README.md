# 📊 Views Modulares - AllpFit Analytics

## 🎯 Objetivo

Este diretório contém as **7 views modulares otimizadas** para análise completa de conversas do Chatwoot.

Estratégia: **Views pequenas e rápidas** que se combinam para formar uma view analítica completa.

---

## 📐 Arquitetura

```
CAMADA 1: Views Base (Rápidas)
├── 01_vw_conversations_base_complete.sql      ⚡⚡⚡ Dados base + JOINs
├── 02_vw_messages_compiled_complete.sql       ⚡⚡  Mensagens em JSON
└── 03_vw_csat_base.sql                        ⚡⚡⚡ Satisfação

CAMADA 2: Views de Métricas (Calculadas)
├── 04_vw_conversation_metrics_complete.sql    ⚡⚡⚡ Tempos e flags
├── 05_vw_message_stats_complete.sql           ⚡⚡  Estatísticas de msgs
└── 06_vw_temporal_metrics.sql                 ⚡⚡⚡ Análise temporal

CAMADA 3: View Final (Tudo junto)
└── 07_vw_conversations_analytics_final.sql    ⚡⚡  150+ campos

DEPLOY:
└── 00_deploy_all_views.sql                    Script master
```

---

## 📋 Descrição das Views

### **1. vw_conversations_base_complete**
**Campos:** 60+
**Inclui:**
- Todos os campos de `conversations`
- Dados de `contacts` (nome, email, telefone, etc)
- Dados de `inboxes` (canal, tipo, configurações)
- Dados de `users` (agente responsável)
- Dados de `teams` (time)
- Dados de `accounts` (conta/empresa)
- Dados de `contact_inboxes` (source_id, etc)

**Performance:** ⚡⚡⚡ MUITO RÁPIDA (apenas JOINs, sem agregação)

---

### **2. vw_messages_compiled_complete**
**Campos:** 7
**Inclui:**
- `message_compiled` (JSONB com todas as mensagens)
- `client_sender_id`
- `client_phone`
- `t_messages`
- Timestamps de primeira/última mensagem

**Performance:** ⚡⚡ MÉDIA (agregação JSONB)
**Compatibilidade:** Mantém os mesmos campos da view original `vw_conversas_por_lead`

---

### **3. vw_csat_base**
**Campos:** 10
**Inclui:**
- Rating (1-5)
- Feedback do cliente
- Categorias NPS (Promotor, Neutro, Detrator)
- Classificação de sentiment
- Flags (tem feedback escrito, detalhado)

**Performance:** ⚡⚡⚡ MUITO RÁPIDA (simples, sem JOINs)

---

### **4. vw_conversation_metrics_complete**
**Campos:** 30+
**Inclui:**
- Tempo de primeira resposta (segundos e minutos)
- Tempo de resolução
- Tempo de espera
- 20+ flags booleanos:
  - is_assigned, is_resolved, is_open
  - is_fast_response, is_slow_response
  - is_high_priority, has_contact
  - E muito mais...
- Labels (status em PT, prioridade em texto)

**Performance:** ⚡⚡⚡ RÁPIDA (cálculos simples)

---

### **5. vw_message_stats_complete**
**Campos:** 25+
**Inclui:**
- Contadores: user_messages, contact_messages, system, private
- Primeira/última mensagem (texto e tipo)
- Duração da conversa
- Tempo médio entre mensagens
- Sentiment score médio
- Tamanho médio/máximo de mensagens
- Flags: has_user_messages, is_short_conversation, etc
- Ratios: proporção de mensagens agente vs cliente

**Performance:** ⚡⚡ MÉDIA (agregações múltiplas)

---

### **6. vw_temporal_metrics**
**Campos:** 40+
**Inclui:**
- Componentes: ano, mês, dia, hora, minuto, semana, trimestre
- Labels: nome do dia, nome do mês (PT e abreviado)
- Períodos: manhã, tarde, noite, madrugada
- Flags temporais:
  - is_weekday, is_weekend
  - is_business_hours, is_night_time
  - is_today, is_this_week, is_this_month
  - E muito mais...
- Formatações úteis para charts

**Performance:** ⚡⚡⚡ MUITO RÁPIDA (cálculos sobre timestamps)

---

### **7. vw_conversations_analytics_final** ⭐
**Campos:** 150+
**Descrição:** Junta TODAS as 6 views anteriores

**Esta é a view que você deve usar no ETL e consultas!**

**Performance:** ⚡⚡ MÉDIA
**Recomendação:** Use com filtros (WHERE, LIMIT) e extraia para banco local

---

## 🚀 Como Usar

### **Opção 1: Deploy Completo (Recomendado)**

```bash
# Conectar ao banco como usuário com permissão de criação
psql -h 178.156.206.184 -p 5432 -U usuario_admin -d chatwoot

# Navegar até a pasta
\cd /caminho/para/sql/modular_views/

# Executar script master
\i 00_deploy_all_views.sql
```

O script irá:
1. Criar as 7 views em ordem
2. Verificar se foram criadas
3. Testar a view final
4. Mostrar resumo

---

### **Opção 2: Deploy Individual**

```bash
# Criar views na ordem:
\i 01_vw_conversations_base_complete.sql
\i 02_vw_messages_compiled_complete.sql
\i 03_vw_csat_base.sql
\i 04_vw_conversation_metrics_complete.sql
\i 05_vw_message_stats_complete.sql
\i 06_vw_temporal_metrics.sql
\i 07_vw_conversations_analytics_final.sql
```

---

## 🔍 Exemplos de Uso

### **Consultar view final completa:**
```sql
SELECT *
FROM vw_conversations_analytics_final
WHERE conversation_date >= CURRENT_DATE - 7  -- Últimos 7 dias
LIMIT 100;
```

### **Apenas campos essenciais:**
```sql
SELECT
    conversation_id,
    display_id,
    status,
    contact_name,
    inbox_name,
    assignee_name,
    csat_rating,
    first_response_time_minutes,
    is_bot_resolved
FROM vw_conversations_analytics_final
WHERE is_this_month = true;
```

### **Análise de performance:**
```sql
SELECT
    inbox_name,
    COUNT(*) as total,
    AVG(first_response_time_minutes) as avg_response,
    AVG(csat_rating) as avg_csat,
    SUM(CASE WHEN is_bot_resolved THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as bot_resolution_rate
FROM vw_conversations_analytics_final
WHERE conversation_date >= CURRENT_DATE - 30
GROUP BY inbox_name
ORDER BY total DESC;
```

### **Heatmap de volume:**
```sql
SELECT
    conversation_day_name,
    conversation_hour,
    COUNT(*) as volume
FROM vw_conversations_analytics_final
WHERE is_this_month = true
GROUP BY conversation_day_name, conversation_day_of_week, conversation_hour
ORDER BY conversation_day_of_week, conversation_hour;
```

---

## 📊 Resumo de Campos por View

| View | Total Campos | Performance | Uso |
|------|--------------|-------------|-----|
| vw_conversations_base_complete | ~60 | ⚡⚡⚡ | Dados base |
| vw_messages_compiled_complete | 7 | ⚡⚡ | Mensagens JSON |
| vw_csat_base | 10 | ⚡⚡⚡ | Satisfação |
| vw_conversation_metrics_complete | ~30 | ⚡⚡⚡ | Métricas |
| vw_message_stats_complete | ~25 | ⚡⚡ | Estatísticas |
| vw_temporal_metrics | ~40 | ⚡⚡⚡ | Análise temporal |
| **vw_conversations_analytics_final** | **~150** | **⚡⚡** | **Use esta!** |

---

## ⚠️ Observações Importantes

1. **Performance:**
   - Views individuais são rápidas
   - View final é mais lenta devido aos JOINs
   - **SEMPRE use filtros** (WHERE) ao consultar a view final

2. **Extração para Banco Local:**
   - Recomendado: ETL extrai de `vw_conversations_analytics_final`
   - Salva em banco local (PostgreSQL local)
   - Dashboard consulta banco local (instantâneo!)

3. **Compatibilidade:**
   - `vw_messages_compiled_complete` mantém os mesmos campos da view original
   - Códigos antigos continuam funcionando

4. **Permissões:**
   - Todas as views têm GRANT para `hetzner_dev_isaac_read`
   - Script funciona com usuário read-only

---

## 📈 Próximos Passos

1. ✅ Views criadas
2. ⏳ Atualizar ETL para usar `vw_conversations_analytics_final`
3. ⏳ Desenvolver dashboard Streamlit
4. ⏳ Implementar cache em banco local
5. ⏳ Adicionar refresh automático (cron)

---

**Criado em:** 2025-10-17
**Versão:** 1.0
**Status:** Pronto para deploy
