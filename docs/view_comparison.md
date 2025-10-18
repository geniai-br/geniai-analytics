# 📊 Comparação: View Antiga vs Nova View

## 🔴 VIEW ATUAL: `vw_conversas_por_lead`

### **Colunas (6 apenas):**
```sql
1. conversation_id          - ID da conversa
2. message_compiled         - JSON com mensagens
3. client_sender_id         - ID do cliente
4. inbox_id                 - ID do canal
5. client_phone             - Telefone
6. t_messages               - Total de mensagens
```

### **Limitações:**
- ❌ Sem informações de status da conversa
- ❌ Sem dados do agente/atendente
- ❌ Sem informações de tempo/duração
- ❌ Sem CSAT/satisfação
- ❌ Sem nome do canal
- ❌ Sem informações completas do contato
- ❌ Sem métricas calculadas
- ❌ 53% dos registros sem client_sender_id

---

## 🟢 NOVA VIEW: `vw_conversas_analytics_completa`

### **Colunas (80+ campos!):**

#### **📌 Mantidos da view original (compatibilidade):**
```sql
✅ conversation_id
✅ message_compiled (MELHORADO - mais campos)
✅ client_sender_id
✅ inbox_id
✅ client_phone
✅ t_messages
```

#### **🆕 INFORMAÇÕES DA CONVERSA (20 campos):**
```sql
+ conversation_id_full      - ID completo
+ display_id                - ID de exibição amigável
+ conversation_uuid         - UUID único
+ account_id                - Conta/empresa
+ contact_id                - ID do contato
+ status                    - open, pending, resolved, closed
+ priority                  - 0-4 (none, low, medium, high, urgent)
+ snoozed_until             - Adiada até quando
+ assignee_id               - Agente responsável
+ team_id                   - Time responsável
+ campaign_id               - Campanha de origem
+ conversation_created_at   - Data de criação
+ conversation_updated_at   - Última atualização
+ last_activity_at          - Última atividade
+ first_reply_created_at    - Primeira resposta
+ waiting_since             - Aguardando desde
+ contact_last_seen_at      - Última vez que contato viu
+ agent_last_seen_at        - Última vez que agente viu
+ cached_label_list         - Lista de labels
+ conversation_attributes   - Atributos adicionais
```

#### **👤 INFORMAÇÕES DO CONTATO (11 campos):**
```sql
+ contact_name              - Nome do cliente
+ contact_email             - Email
+ contact_identifier        - Identificador externo
+ contact_type              - Tipo de contato
+ contact_location          - Localização
+ contact_country           - Código do país
+ contact_created_at        - Cliente desde quando
+ contact_last_activity_at  - Última atividade do cliente
+ contact_blocked           - Está bloqueado?
```

#### **📱 INFORMAÇÕES DO CANAL (6 campos):**
```sql
+ inbox_name                - Nome do canal (ex: "WhatsApp Business")
+ inbox_channel_type        - Tipo (whatsapp, telegram, email, etc)
+ inbox_business_name       - Nome do negócio
+ inbox_timezone            - Fuso horário
+ inbox_auto_assign         - Auto-atribuição ativa?
+ inbox_csat_enabled        - CSAT ativo neste canal?
```

#### **🧑‍💼 INFORMAÇÕES DO AGENTE (4 campos):**
```sql
+ assignee_name             - Nome do agente
+ assignee_display_name     - Nome de exibição
+ assignee_email            - Email do agente
+ assignee_availability     - Disponibilidade (online, offline, busy)
```

#### **👥 INFORMAÇÕES DO TIME (2 campos):**
```sql
+ team_name                 - Nome do time
+ team_description          - Descrição do time
```

#### **⭐ SATISFAÇÃO DO CLIENTE (3 campos):**
```sql
+ csat_rating               - Rating (1-5)
+ csat_feedback             - Comentário do cliente
+ csat_created_at           - Quando foi avaliado
```

#### **💬 CONTADORES DETALHADOS (4 campos):**
```sql
+ user_messages_count       - Mensagens do agente
+ contact_messages_count    - Mensagens do cliente
+ private_notes_count       - Notas internas
+ system_messages_count     - Mensagens do sistema
```

#### **📝 PRIMEIRA E ÚLTIMA MENSAGEM (6 campos):**
```sql
+ first_message_text        - Texto da primeira mensagem
+ last_message_text         - Texto da última mensagem
+ first_message_at          - Data da primeira mensagem
+ last_message_at           - Data da última mensagem
+ first_message_sender_type - Quem enviou a primeira
+ last_message_sender_type  - Quem enviou a última
```

#### **⏱️ MÉTRICAS DE TEMPO CALCULADAS (3 campos):**
```sql
+ first_response_time_seconds        - Tempo até primeira resposta
+ conversation_duration_seconds      - Duração total da conversa
+ avg_time_between_messages_seconds  - Tempo médio entre mensagens
```

#### **🚦 FLAGS BOOLEANOS (10 campos):**
```sql
+ is_assigned               - Foi atribuída?
+ has_team                  - Tem time?
+ is_resolved               - Está resolvida?
+ is_open                   - Está aberta?
+ is_snoozed                - Está adiada?
+ has_csat                  - Tem avaliação?
+ has_human_intervention    - Teve atendimento humano?
+ is_bot_resolved           - Foi resolvida só por bot?
+ has_contact_reply         - Cliente respondeu?
+ has_contact               - Tem contato identificado?
```

#### **📈 ANÁLISE DE SENTIMENT (1 campo):**
```sql
+ avg_sentiment_score       - Média de sentiment das mensagens
```

#### **🏢 INFORMAÇÕES DA CONTA (2 campos):**
```sql
+ account_name              - Nome da empresa
+ account_locale            - Localização/idioma
```

#### **📅 METADADOS TEMPORAIS (10 campos):**
```sql
+ conversation_date         - Data (apenas dia)
+ conversation_year         - Ano
+ conversation_month        - Mês (1-12)
+ conversation_day          - Dia (1-31)
+ conversation_day_of_week  - Dia da semana (0-6)
+ conversation_hour         - Hora (0-23)
+ conversation_day_name     - Nome do dia (Segunda, Terça, etc)
+ conversation_period       - Período (Manhã, Tarde, Noite, Madrugada)
+ is_weekday                - É dia útil?
+ is_business_hours         - É horário comercial?
```

---

## 📊 RESUMO DA EVOLUÇÃO

| Aspecto | View Antiga | Nova View |
|---------|-------------|-----------|
| **Total de Colunas** | 6 | 80+ |
| **Informações do Contato** | Apenas ID e telefone | Nome, email, tipo, localização, etc |
| **Informações do Canal** | Apenas ID | Nome, tipo, configurações |
| **Status da Conversa** | ❌ Não tem | ✅ Completo |
| **Agente/Atendente** | ❌ Não tem | ✅ Nome, email, disponibilidade |
| **Time** | ❌ Não tem | ✅ Nome e descrição |
| **CSAT** | ❌ Não tem | ✅ Rating e feedback |
| **Métricas de Tempo** | ❌ Não tem | ✅ 3 métricas calculadas |
| **Contadores Detalhados** | 1 (total) | 5 (total, user, contact, system, notes) |
| **Flags Booleanos** | ❌ Não tem | ✅ 10 indicadores |
| **Análise Temporal** | ❌ Não tem | ✅ 10 campos (ano, mês, dia, hora, período) |
| **message_compiled** | Básico (5 campos) | Enriquecido (9 campos) |

---

## 🎯 BENEFÍCIOS DA NOVA VIEW

### **1. Análise Completa de Performance**
- ✅ Tempo de primeira resposta
- ✅ Duração das conversas
- ✅ Identificação de bot vs humano
- ✅ Taxa de resolução

### **2. Segmentação Avançada**
- ✅ Por canal (nome e tipo)
- ✅ Por agente/time
- ✅ Por período (manhã, tarde, noite)
- ✅ Por dia da semana
- ✅ Por horário comercial

### **3. Análise de Satisfação**
- ✅ CSAT rating
- ✅ Feedback do cliente
- ✅ Sentiment analysis

### **4. Identificação de Problemas**
- ✅ Conversas muito longas
- ✅ Sem atendimento humano
- ✅ Sem resposta
- ✅ Aguardando há muito tempo

### **5. Métricas de Negócio**
- ✅ Volume por canal
- ✅ Performance por agente
- ✅ Campanhas de origem
- ✅ Clientes recorrentes

---

## 🚀 COMO USAR

### **Aplicar a Nova View:**

```sql
-- Conectar ao banco como usuário com permissão de criação
psql -h 178.156.206.184 -p 5432 -U usuario_admin -d chatwoot

-- Executar o script
\i /caminho/para/create_view_v2_enhanced.sql
```

### **Testar a Nova View:**

```sql
-- Ver estrutura
SELECT * FROM vw_conversas_analytics_completa LIMIT 1;

-- Contar registros
SELECT COUNT(*) FROM vw_conversas_analytics_completa;

-- Comparar com view antiga
SELECT
    COUNT(*) as total_antiga
FROM vw_conversas_por_lead;

SELECT
    COUNT(*) as total_nova
FROM vw_conversas_analytics_completa;
```

---

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Performance**: A nova view faz vários JOINs e agregações.
   - Pode ser mais lenta que a atual
   - Considere criar índices nas tabelas base
   - Para dashboards, faça cache dos dados no banco local

2. **Compatibilidade**: Mantém os mesmos 6 campos originais
   - Códigos existentes continuarão funcionando
   - Novos campos são adicionais

3. **Permissões**: O script já inclui:
   ```sql
   GRANT SELECT ON vw_conversas_analytics_completa TO hetzner_dev_isaac_read;
   ```

4. **Nomenclatura**:
   - View antiga: `vw_conversas_por_lead`
   - View nova: `vw_conversas_analytics_completa`
   - Podem coexistir no mesmo banco

---

## 📋 PRÓXIMOS PASSOS

1. ✅ Revisar e aprovar a query SQL
2. ⏳ Aplicar no banco de dados (DBA)
3. ⏳ Testar performance
4. ⏳ Atualizar ETL pipeline para usar nova view
5. ⏳ Desenvolver dashboard com novos campos

---

**Criado em**: 2025-10-17
**Versão**: 2.0
**Status**: Aguardando aprovação para deploy
