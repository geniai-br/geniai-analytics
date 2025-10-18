# 📋 Especificação da Nova View - vw_conversas_por_lead

## 🔍 Análise da View Atual

### **Colunas Existentes:**
```
1. conversation_id       INTEGER       - ID único da conversa ✅
2. message_compiled      JSONB         - Array de mensagens em JSON ✅
3. client_sender_id      BIGINT        - ID do cliente (53% nulos ⚠️)
4. inbox_id              INTEGER       - ID do canal ✅
5. client_phone          VARCHAR       - Telefone (53% nulos ⚠️)
6. t_messages            BIGINT        - Total de mensagens ✅
```

### **Estrutura do message_compiled (JSON):**
Cada mensagem no array contém:
```json
{
  "text": "Conteúdo da mensagem",
  "sender": "Contact|User|None",
  "sent_at": "2025-09-25T03:17:59.295105",
  "sender_id": 123,
  "message_id": 11150
}
```

### **Estatísticas Atuais:**
- Total: **4.075 conversas**
- Clientes únicos: **1.867**
- Inboxes: **11 canais**
- Média msgs/conversa: **9.41**
- Range: **1 - 1.115 mensagens**
- **53% das conversas NÃO têm client_sender_id/phone** ⚠️

### **Tipos de Sender Encontrados:**
- `Contact` - Cliente/Lead
- `User` - Atendente humano
- `None` - Eventos do sistema (auto-assign, etc.)

---

## 🎯 Colunas Necessárias na Nova View

### **🔴 PRIORIDADE CRÍTICA (Fase 1)**

#### **A) Identificadores e Relacionamentos**
```sql
-- JÁ TEMOS ✅
conversation_id          INTEGER
client_sender_id         BIGINT
inbox_id                 INTEGER

-- PRECISAMOS ADICIONAR:
account_id               INTEGER      -- Conta/empresa (multi-tenant)
contact_id               BIGINT       -- ID do contato (relacionamento)
assignee_id              INTEGER      -- Agente responsável
team_id                  INTEGER      -- Time responsável
campaign_id              INTEGER      -- Campanha de origem (se houver)
```

#### **B) Datas e Tempos**
```sql
-- PRECISAMOS ADICIONAR:
created_at               TIMESTAMP    -- Início da conversa
updated_at               TIMESTAMP    -- Última atualização
last_activity_at         TIMESTAMP    -- Última mensagem
resolved_at              TIMESTAMP    -- Quando foi resolvida
first_reply_created_at   TIMESTAMP    -- Primeira resposta

-- CALCULADOS (podem ser extraídos do message_compiled):
first_response_time      INTEGER      -- Segundos até primeira resposta
avg_response_time        DECIMAL      -- Tempo médio de resposta
conversation_duration    INTEGER      -- Duração total (segundos)
```

#### **C) Status e Classificação**
```sql
-- PRECISAMOS ADICIONAR:
status                   VARCHAR      -- open, pending, resolved, closed, snoozed
display_id               INTEGER      -- ID de exibição amigável
conversation_type        VARCHAR      -- incoming, outgoing
priority                 INTEGER      -- 0=none, 1=low, 2=medium, 3=high, 4=urgent
snoozed_until            TIMESTAMP    -- Até quando está adiada
```

#### **D) Informações do Cliente/Contato**
```sql
-- JÁ TEMOS (parcial) ✅
client_phone             VARCHAR

-- PRECISAMOS ADICIONAR:
contact_name             VARCHAR      -- Nome do contato
contact_email            VARCHAR      -- Email do contato
contact_identifier       VARCHAR      -- Identificador externo
contact_created_at       TIMESTAMP    -- Quando o contato foi criado
contact_last_seen_at     TIMESTAMP    -- Última visualização
```

#### **E) Informações do Canal (Inbox)**
```sql
-- JÁ TEMOS ✅
inbox_id                 INTEGER

-- PRECISAMOS ADICIONAR:
inbox_name               VARCHAR      -- Nome do canal
inbox_channel_type       VARCHAR      -- whatsapp, telegram, email, web, etc.
inbox_identifier         VARCHAR      -- Identificador do canal
```

#### **F) Mensagens e Conteúdo**
```sql
-- JÁ TEMOS ✅
message_compiled         JSONB        -- Array de mensagens
t_messages               BIGINT       -- Total de mensagens

-- PRECISAMOS ADICIONAR:
messages_count           INTEGER      -- Total de mensagens (validação)
user_messages_count      INTEGER      -- Mensagens do atendente
contact_messages_count   INTEGER      -- Mensagens do cliente
system_messages_count    INTEGER      -- Mensagens do sistema
first_message_text       TEXT         -- Primeira mensagem (para preview)
last_message_text        TEXT         -- Última mensagem
```

---

### **🟡 PRIORIDADE ALTA (Fase 2)**

#### **G) Métricas de Atendimento**
```sql
waiting_since            TIMESTAMP    -- Aguardando resposta desde
agent_last_seen_at       TIMESTAMP    -- Última vez que agente viu
contact_last_seen_at     TIMESTAMP    -- Última vez que contato viu
unread_count             INTEGER      -- Mensagens não lidas

-- CALCULADOS:
is_bot_handled           BOOLEAN      -- Foi resolvido apenas por bot?
has_human_intervention   BOOLEAN      -- Teve intervenção humana?
escalation_count         INTEGER      -- Quantas vezes foi escalado
```

#### **H) Satisfação e Feedback**
```sql
rating                   INTEGER      -- Rating dado pelo cliente (1-5)
feedback_message         TEXT         -- Comentário do feedback
rated_at                 TIMESTAMP    -- Quando foi avaliado
csat_survey_response_id  INTEGER      -- ID da resposta CSAT
```

#### **I) Labels e Categorização**
```sql
labels                   JSONB        -- Array de labels/tags
custom_attributes        JSONB        -- Atributos customizados
conversation_labels      VARCHAR[]    -- Array de nomes das labels
```

#### **J) Automação e Bot**
```sql
automated                BOOLEAN      -- Foi automatizada?
automation_rule_id       INTEGER      -- Regra de automação aplicada
bot_conversation         BOOLEAN      -- É conversa com bot?
bot_handoff              BOOLEAN      -- Houve handoff de bot→humano?
```

---

### **🟢 PRIORIDADE MÉDIA (Fase 3 - Opcional)**

#### **K) Análise Avançada**
```sql
-- Campos que podem ser calculados via NLP/ML posteriormente:
sentiment_score          DECIMAL      -- Score de sentimento (-1 a 1)
sentiment_label          VARCHAR      -- positive, neutral, negative
intent_category          VARCHAR      -- Categoria da intenção
language_detected        VARCHAR      -- Idioma detectado
keywords                 VARCHAR[]    -- Palavras-chave extraídas
```

#### **L) Business Metrics**
```sql
conversion_value         DECIMAL      -- Valor gerado
is_converted             BOOLEAN      -- Houve conversão?
product_interest         VARCHAR      -- Produto de interesse
funnel_stage             VARCHAR      -- Estágio no funel
```

#### **M) Contexto Histórico**
```sql
is_first_conversation    BOOLEAN      -- Primeira conversa do contato?
previous_conversation_id INTEGER      -- Conversa anterior
contact_conversations_count INTEGER   -- Total de conversas do contato
days_since_last_contact  INTEGER      -- Dias desde último contato
```

---

## 📊 Resumo: Mapeamento de Necessidades

### **O que já temos e está OK:**
✅ `conversation_id`
✅ `message_compiled` (com timestamps!)
✅ `inbox_id`
✅ `t_messages`

### **O que temos mas está incompleto:**
⚠️ `client_sender_id` (53% nulos - precisa melhorar)
⚠️ `client_phone` (53% nulos - precisa melhorar)

### **O que precisamos URGENTE (Fase 1):**
🔴 `created_at`, `updated_at`, `last_activity_at`
🔴 `status`, `display_id`
🔴 `contact_name`, `contact_email`
🔴 `inbox_name`, `inbox_channel_type`
🔴 `assignee_id`, `assignee_name`
🔴 `messages_count`, `user_messages_count`, `contact_messages_count`

### **O que precisamos em breve (Fase 2):**
🟡 `rating`, `feedback_message`
🟡 `is_bot_handled`, `has_human_intervention`
🟡 `labels`, `custom_attributes`
🟡 `first_message_text`, `last_message_text`

### **O que podemos adicionar depois (Fase 3):**
🟢 Campos de NLP/Sentiment
🟢 Business metrics
🟢 Análise histórica avançada

---

## 🎯 Próximos Passos

1. **Enviar lista de tabelas disponíveis** no banco Chatwoot
2. **Identificar relacionamentos** entre tabelas
3. **Criar nova query da view** com JOINs necessários
4. **Validar campos calculados** que precisam de lógica SQL
5. **Testar performance** da nova view

---

## 📝 Observações Importantes

### **Sobre os 53% de nulos:**
- Metade das conversas não têm `client_sender_id` nem `client_phone`
- Isso pode indicar:
  - Conversas iniciadas pelo sistema
  - Testes/conversas internas
  - Canais que não capturam essas informações
- **Ação**: Investigar se há outro campo para identificar o cliente

### **Sobre o message_compiled:**
- ✅ Excelente: Tem timestamps (`sent_at`)
- ✅ Tem identificação de tipo (`sender`)
- ✅ Tem sender_id dentro de cada mensagem
- ⚠️ Precisa processar para extrair métricas de tempo
- ⚠️ Precisa identificar bot vs humano

### **Campos Calculáveis:**
Alguns campos podem ser calculados a partir dos dados existentes:
- `first_response_time` → Calcular do message_compiled
- `conversation_duration` → Calcular do message_compiled
- `user_messages_count` → Contar do message_compiled
- `is_bot_handled` → Analisar senders do message_compiled

---

**Aguardando**: Lista de tabelas do banco Chatwoot para mapear os JOINs necessários! 🚀
