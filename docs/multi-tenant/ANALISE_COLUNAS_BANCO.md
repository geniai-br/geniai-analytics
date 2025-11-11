# ANÁLISE DAS COLUNAS DO BANCO DE DADOS

> **Data:** 2025-11-11
> **Tabela:** `conversations_analytics`
> **Tenant analisado:** AllpFit (tenant_id = 1)
> **Total de conversas:** 1.317

---

## ✅ COLUNAS JÁ EXISTENTES E ÚTEIS

### 📋 Colunas de Identificação (OK)
- `conversation_id` - ID único da conversa ✅
- `contact_name` - Nome do contato ✅
- `contact_phone` - Telefone ✅
- `contact_email` - Email ✅

### 📥 Informações de Inbox (JÁ EXISTE!)
- **`inbox_id`** - ID da inbox ✅ (1.317/1.317 = 100%)
- **`inbox_name`** - Nome da inbox ✅ (1.317/1.317 = 100%)
  - Exemplo: "allpfitjpsulcloud1"
- **`inbox_channel_type`** - Tipo de canal ✅
- **`inbox_timezone`** - Timezone da inbox ✅

**Conclusão:** NÃO precisa adicionar `inbox_id`/`inbox_name` - **JÁ EXISTEM!**

### 📅 Datas Relevantes (JÁ EXISTEM!)
- **`conversation_created_at`** - Data de criação da conversa ✅
- **`mc_first_message_at`** - Data da primeira mensagem ✅ (1.316/1.317 = 99.9%)
- **`mc_last_message_at`** - Data da última mensagem ✅ (1.316/1.317 = 99.9%)

**Conclusão:** NÃO precisa adicionar `primeiro_contato`/`ultimo_contato` - **JÁ EXISTEM!**
- `mc_first_message_at` = primeiro contato
- `mc_last_message_at` = último contato

### 💬 Conversa Compilada (JÁ EXISTE!)
- **`message_compiled`** - JSONB com TODAS as mensagens ✅ (1.316/1.317 = 99.9%)

**Estrutura do JSONB:**
```json
[
  {
    "text": "Ola",
    "sender": "Contact",
    "private": false,
    "sent_at": "2025-09-25T01:52:07.951889",
    "sender_id": 5,
    "message_id": 11065,
    "message_type": 0
  },
  {
    "text": "Como funciona?",
    "sender": "Contact",
    "private": false,
    "sent_at": "2025-09-25T01:57:59.179351",
    "sender_id": 5,
    "message_id": 11071,
    "message_type": 0
  },
  {
    "text": "Oi! Aqui é a Gabi...",
    "sender": "AgentBot",
    "private": false,
    "sent_at": "2025-09-25T01:58:23.159729",
    "sender_id": 1,
    "message_id": 11072,
    "message_type": 1
  }
]
```

**Conclusão:** NÃO precisa adicionar `conversa_compilada` - **JÁ EXISTE!**
- Apenas precisamos exibir no dashboard (primeiras 5-10 mensagens)

### 👤 Nome Mapeado pelo Bot
- **`nome_mapeado_bot`** - Nome extraído pela IA ✅ (556/1.317 = 42%)
  - Coluna existe e tem dados!
  - 556 conversas já têm nome mapeado

**Conclusão:** Coluna **JÁ EXISTE!** Só precisa exibir no dashboard.

### 📊 Status e Métricas (OK)
- `status` - Status numérico ✅
- `status_label_pt` - Status em português ✅
- `is_lead` - Boolean (é lead?) ✅
- `is_resolved` - Conversa resolvida? ✅
- `is_open` - Conversa aberta? ✅
- `t_messages` - Total de mensagens ✅
- `total_messages_public` - Mensagens públicas ✅
- `user_messages_count` - Mensagens do atendente ✅
- `contact_messages_count` - Mensagens do contato ✅

---

## ❌ COLUNAS ESPECÍFICAS ALLPFIT (OCULTAR)

Estas colunas existem e têm dados, mas devem ser **OCULTADAS** do dashboard:

- **`condicao_fisica`** - (29 com dados) - Específico AllpFit ❌
- **`objetivo`** - (40 com dados) - Específico AllpFit ❌
- **`analise_ia`** - (742 com dados) - Específica AllpFit ❌
- **`sugestao_disparo`** - (dados?) - Específica AllpFit ❌
- **`probabilidade_conversao`** - (dados?) - Específica AllpFit ❌

**Ação:**
- Não deletar colunas do banco (preservar dados AllpFit)
- Apenas não exibir no dashboard multi-tenant
- Comentar código relacionado

---

## 🔍 COLUNAS QUE NÃO EXISTEM

### Tipo de Atendimento (Bot vs Humano)
**Solicitado:** Diferenciar inboxes atendidas por IA vs humanos

**Status:** NÃO EXISTE coluna específica, mas pode ser inferida:
- `has_human_intervention` - Boolean (teve intervenção humana?) ✅
- `is_bot_resolved` - Boolean (resolvido por bot?) ✅
- `assignee_id` - ID do atendente (se NULL = bot, se preenchido = humano?) ✅

**Opções:**
1. Usar colunas existentes para inferir tipo
2. Criar nova coluna `atendimento_tipo` ENUM ('bot', 'humano', 'misto')

### Nome do Bot/IA
**Solicitado:** Coluna com nome da IA que atendeu

**Status:** NÃO EXISTE

**Opções:**
1. Adicionar coluna `bot_name` VARCHAR
2. Inferir do `inbox_name` ou configuração do tenant
3. Deixar como "Bot Padrão" por enquanto

---

## 📋 RESUMO DE AÇÕES

### ✅ NÃO PRECISA ADICIONAR (JÁ EXISTE):
- [x] `inbox_id` / `inbox_name` - JÁ EXISTEM
- [x] `primeiro_contato` - usar `mc_first_message_at`
- [x] `ultimo_contato` - usar `mc_last_message_at`
- [x] `conversa_compilada` - usar `message_compiled`
- [x] `nome_mapeado_bot` - JÁ EXISTE (556 registros)

### ❌ OCULTAR DO DASHBOARD:
- [ ] `condicao_fisica`
- [ ] `objetivo`
- [ ] `analise_ia`
- [ ] `sugestao_disparo`
- [ ] `probabilidade_conversao`

### ➕ CONSIDERAR ADICIONAR (OPCIONAL):
- [ ] `atendimento_tipo` ENUM('bot', 'humano', 'misto')
- [ ] `bot_name` VARCHAR - nome da IA que atendeu
- [ ] Tags (verificar se já existe em outra tabela)

### 🎨 IMPLEMENTAR NO DASHBOARD:
- [ ] Exibir `nome_mapeado_bot` na tabela
- [ ] Exibir `inbox_name` na tabela
- [ ] Exibir primeiras 5-10 mensagens de `message_compiled`
- [ ] Usar `mc_first_message_at` como "Primeiro Contato"
- [ ] Usar `mc_last_message_at` como "Último Contato"
- [ ] Filtros para todas essas colunas

---

## 🔢 ESTATÍSTICAS ATUAIS (AllpFit)

| Coluna | Registros com Dados | % |
|--------|---------------------|---|
| Total conversas | 1.317 | 100% |
| `inbox_name` | 1.317 | 100% |
| `message_compiled` | 1.316 | 99.9% |
| `mc_first_message_at` | 1.316 | 99.9% |
| `mc_last_message_at` | 1.316 | 99.9% |
| `nome_mapeado_bot` | 556 | 42% |
| `condicao_fisica` | 29 | 2.2% |
| `objetivo` | 40 | 3% |
| `analise_ia` | 742 | 56% |

---

## 💡 RECOMENDAÇÕES

### 1. Usar Colunas Existentes
**Ganho:** Zero mudanças no banco, apenas no dashboard
**Esforço:** Baixo (apenas frontend)

### 2. Renomear na Visualização
Mapear nomes mais amigáveis no dashboard:
- `mc_first_message_at` → "Primeiro Contato"
- `mc_last_message_at` → "Último Contato"
- `message_compiled` → "Conversa" (exibir primeiras mensagens)
- `nome_mapeado_bot` → "Nome Mapeado"

### 3. Implementar Filtros
Todas as colunas listadas acima são filtráveis:
- Datas: range picker
- Texto: busca parcial
- Boolean: checkbox
- Inbox: multi-select dropdown

### 4. Análise de Tipo de Atendimento
Usar lógica:
```python
def get_atendimento_tipo(row):
    if row['is_bot_resolved'] and not row['has_human_intervention']:
        return 'Bot'
    elif row['has_human_intervention']:
        return 'Humano' if row['assignee_id'] else 'Misto'
    else:
        return 'Bot'
```

---

**Última atualização:** 2025-11-11
**Responsável:** Claude
**Próximo passo:** Analisar dashboard single-tenant para referência de UI
