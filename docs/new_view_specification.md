# 🎯 Nova View: vw_conversas_analytics_completa

## 📊 Análise das Tabelas Disponíveis

### **1. CONVERSATIONS (26 colunas) - TABELA PRINCIPAL** ⭐

**Colunas essenciais que vamos usar:**
```
✅ id                        - ID da conversa
✅ account_id                - Conta/empresa
✅ inbox_id                  - Canal de atendimento
✅ status                    - Status da conversa
✅ assignee_id               - Agente responsável
✅ team_id                   - Time responsável
✅ contact_id                - ID do contato
✅ display_id                - ID de exibição
✅ created_at                - Data de criação
✅ updated_at                - Última atualização
✅ last_activity_at          - Última atividade
✅ contact_last_seen_at      - Última vez que contato viu
✅ agent_last_seen_at        - Última vez que agente viu
✅ contact_inbox_id          - Relacionamento contato-inbox
✅ priority                  - Prioridade (0-4)
✅ snoozed_until             - Adiada até quando
✅ campaign_id               - ID da campanha
✅ first_reply_created_at    - Primeira resposta
✅ waiting_since             - Aguardando desde
✅ assignee_last_seen_at     - Última visualização do assignee
✅ cached_label_list         - Lista de labels em cache
✅ uuid                      - UUID único
✅ identifier                - Identificador externo
✅ additional_attributes     - Atributos adicionais (JSON)
✅ custom_attributes         - Atributos customizados (JSON)
✅ sla_policy_id             - Política de SLA
```

---

### **2. CONTACTS (17 colunas) - INFORMAÇÕES DO CLIENTE** ⭐

**Colunas essenciais:**
```
✅ id                        - ID do contato
✅ name                      - Nome
✅ email                     - Email
✅ phone_number              - Telefone
✅ account_id                - Conta
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
✅ identifier                - Identificador externo
✅ last_activity_at          - Última atividade
✅ contact_type              - Tipo de contato
✅ middle_name               - Nome do meio
✅ last_name                 - Sobrenome
✅ location                  - Localização
✅ country_code              - Código do país
✅ blocked                   - Bloqueado?
✅ additional_attributes     - Atributos adicionais (JSON)
✅ custom_attributes         - Atributos customizados (JSON)
```

---

### **3. INBOXES (28 colunas) - CANAIS DE ATENDIMENTO** ⭐

**Colunas essenciais:**
```
✅ id                        - ID do inbox
✅ channel_id                - ID do canal
✅ account_id                - Conta
✅ name                      - Nome do canal
✅ channel_type              - Tipo (whatsapp, telegram, etc)
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
✅ enable_auto_assignment    - Auto-atribuição ativada?
✅ greeting_enabled          - Saudação ativada?
✅ greeting_message          - Mensagem de saudação
✅ email_address             - Email do canal
✅ working_hours_enabled     - Horário comercial ativo?
✅ out_of_office_message     - Mensagem fora do horário
✅ timezone                  - Fuso horário
✅ csat_survey_enabled       - Pesquisa CSAT ativada?
✅ allow_messages_after_resolved - Permitir msgs após resolver?
✅ portal_id                 - ID do portal
✅ sender_name_type          - Tipo do nome do remetente
✅ business_name             - Nome do negócio
```

---

### **4. MESSAGES (19 colunas) - MENSAGENS INDIVIDUAIS** ⭐

**Colunas essenciais:**
```
✅ id                        - ID da mensagem
✅ content                   - Conteúdo da mensagem
✅ account_id                - Conta
✅ inbox_id                  - Canal
✅ conversation_id           - ID da conversa
✅ message_type              - Tipo (incoming, outgoing, activity, etc)
✅ created_at                - Criada em
✅ updated_at                - Atualizada em
✅ private                   - Mensagem privada/nota interna?
✅ status                    - Status da mensagem
✅ source_id                 - ID da origem externa
✅ content_type              - Tipo de conteúdo (text, image, etc)
✅ content_attributes        - Atributos do conteúdo (JSON)
✅ sender_type               - Tipo do remetente (User, Contact, etc)
✅ sender_id                 - ID do remetente
✅ external_source_ids       - IDs de fonte externa (JSON)
✅ additional_attributes     - Atributos adicionais (JSON)
✅ processed_message_content - Conteúdo processado
✅ sentiment                 - Análise de sentimento
```

---

### **5. USERS (28 colunas) - AGENTES/ATENDENTES** ⭐

**Colunas essenciais:**
```
✅ id                        - ID do usuário
✅ name                      - Nome
✅ display_name              - Nome de exibição
✅ email                     - Email
✅ account_id                - Conta (via relacionamento)
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
✅ availability              - Disponibilidade (online, offline, busy)
✅ type                      - Tipo de usuário
✅ custom_attributes         - Atributos customizados (JSON)
```

---

### **6. TEAMS (7 colunas) - TIMES**

**Colunas:**
```
✅ id                        - ID do time
✅ name                      - Nome do time
✅ description               - Descrição
✅ allow_auto_assign         - Permite auto-atribuição?
✅ account_id                - Conta
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

### **7. CSAT_SURVEY_RESPONSES (10 colunas) - SATISFAÇÃO** ⭐

**Colunas:**
```
✅ id                        - ID da resposta
✅ account_id                - Conta
✅ conversation_id           - Conversa avaliada
✅ message_id                - Mensagem do survey
✅ rating                    - Rating (1-5)
✅ feedback_message          - Comentário do cliente
✅ contact_id                - Quem avaliou
✅ assigned_agent_id         - Agente avaliado
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

### **8. CONTACT_INBOXES (8 colunas) - RELACIONAMENTO CONTATO-CANAL**

**Colunas:**
```
✅ id                        - ID
✅ contact_id                - ID do contato
✅ inbox_id                  - ID do inbox
✅ source_id                 - ID externo (ex: WhatsApp ID)
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
✅ hmac_verified             - Verificado?
✅ pubsub_token              - Token
```

---

### **9. CONVERSATION_PARTICIPANTS (6 colunas) - PARTICIPANTES**

**Colunas:**
```
✅ id                        - ID
✅ account_id                - Conta
✅ user_id                   - Usuário participante
✅ conversation_id           - Conversa
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

### **10. INBOX_MEMBERS (5 colunas) - MEMBROS DO CANAL**

**Colunas:**
```
✅ id                        - ID
✅ user_id                   - Usuário/agente
✅ inbox_id                  - Canal
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

### **11. TEAM_MEMBERS (5 colunas) - MEMBROS DO TIME**

**Colunas:**
```
✅ id                        - ID
✅ team_id                   - Time
✅ user_id                   - Usuário
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

### **12. ACCOUNTS (14 colunas) - CONTAS/EMPRESAS**

**Colunas:**
```
✅ id                        - ID da conta
✅ name                      - Nome da empresa
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
✅ locale                    - Localização/idioma
✅ domain                    - Domínio
✅ support_email             - Email de suporte
✅ status                    - Status da conta
```

---

### **13. AGENT_BOTS (9 colunas) - BOTS/IA**

**Colunas:**
```
✅ id                        - ID do bot
✅ name                      - Nome do bot
✅ description               - Descrição
✅ outgoing_url              - URL de webhook
✅ account_id                - Conta
✅ bot_type                  - Tipo do bot
✅ bot_config                - Configuração (JSON)
✅ created_at                - Criado em
✅ updated_at                - Atualizado em
```

---

## 🔗 RELACIONAMENTOS IDENTIFICADOS

```
conversations
├── contact_id         → contacts.id
├── inbox_id           → inboxes.id
├── assignee_id        → users.id
├── team_id            → teams.id
├── account_id         → accounts.id
└── contact_inbox_id   → contact_inboxes.id

messages
├── conversation_id    → conversations.id
├── sender_id          → users.id OU contacts.id (dependendo de sender_type)
├── inbox_id           → inboxes.id
└── account_id         → accounts.id

contact_inboxes
├── contact_id         → contacts.id
└── inbox_id           → inboxes.id

csat_survey_responses
├── conversation_id    → conversations.id
├── contact_id         → contacts.id
├── assigned_agent_id  → users.id
└── account_id         → accounts.id

conversation_participants
├── conversation_id    → conversations.id
└── user_id            → users.id

inbox_members
├── inbox_id           → inboxes.id
└── user_id            → users.id

team_members
├── team_id            → teams.id
└── user_id            → users.id
```

---

## 📋 PRÓXIMO PASSO

Agora vou criar a **query SQL completa** para a nova view enriquecida! 🚀

Quer que eu:
1. Crie a query SQL completa da nova view?
2. Inclua campos calculados (tempo de resposta, contadores, etc)?
3. Documente cada campo adicionado?
