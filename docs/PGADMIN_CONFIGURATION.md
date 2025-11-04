# 🎯 Guia Definitivo: Configuração pgAdmin para AllpFit Analytics

## ✅ CREDENCIAIS CORRETAS (Fornecidas por Isaac)

```
Usuário: hetzner_hyago_read
Senha: c1d46b41391f
View: vw_conversations_analytics_final
Banco: chatwoot
Schema: public
Host: 178.156.206.184
Porta: 5432
```

**Status**: ✅ **TESTADO E FUNCIONANDO!**

---

## 🗄️ Configuração dos Servidores no pgAdmin

### **SERVIDOR 1: Middleware GeniAI Server (Local)**
**Você já tem configurado**

```yaml
Nome: Middleware GeniAI Server
Tipo: PostgreSQL 15
Host: localhost (ou 5.161.245.128)
Porta: 5432

Databases:
  - integracao_chatwoot
    User: integracao_user
    Pass: vlVMVM6UNz2yYSBlzodPjQvZh

  - allpfit (Analytics Local)
    User: isaac
    Pass: AllpFit2024@Analytics
    Tabelas:
      • conversas_analytics (dados locais sincronizados)
      • conversas_analytics_ai (análises GPT-4)
      • etl_control (auditoria ETL)
```

**Conexão**:
- Se local: `localhost`
- Se remoto: SSH Tunnel (tester@5.161.245.128)

---

### **SERVIDOR 2: GeniAI Analytics - Chatwoot (Remoto)**
**⭐ NOVO - A CONFIGURAR**

#### **Passo a Passo no pgAdmin:**

1. **Clique com botão direito em "Servers" → "Register" → "Server"**

2. **Aba "General":**
   - **Name**: `GeniAI Analytics - Chatwoot`
   - **Server Group**: Servers
   - **Comments**: `Banco Chatwoot - Fonte de dados multi-tenant`

3. **Aba "Connection":**
   - **Host name/address**: `178.156.206.184`
   - **Port**: `5432`
   - **Maintenance database**: `chatwoot`
   - **Username**: `hetzner_hyago_read`
   - **Password**: `c1d46b41391f`
   - **Save password**: ✅ (marque se quiser salvar)
   - **Role**: (deixe vazio)
   - **Service**: (deixe vazio)

4. **Aba "SSH Tunnel" (IMPORTANTE!):**

   **Opção A: Se você tem SSH direto ao 178.156.206.184**
   - **Use SSH tunneling**: ✅ (marque)
   - **Tunnel host**: `178.156.206.184`
   - **Tunnel port**: `22`
   - **Username**: `[seu_usuario_ssh]` (perguntar Isaac)
   - **Authentication**: Identity file
   - **Identity file**: `~/.ssh/id_ed25519` (ou sua chave SSH)

   **Opção B: Se NÃO tem SSH direto (mais comum)**
   - **Use SSH tunneling**: ❌ (desmarque)
   - Conecte direto pela porta 5432
   - **NOTA**: O servidor deve permitir conexões externas na porta 5432

5. **Aba "Advanced":**
   - **DB restriction**: `chatwoot` (opcional, para mostrar só esse banco)
   - **Connection timeout**: 10

6. **Clique em "Save"**

---

## 🧪 Testando a Conexão (Via Terminal)

```bash
# Teste básico
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -U hetzner_hyago_read -d chatwoot -c "SELECT version();"

# Ver databases disponíveis
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -U hetzner_hyago_read -l

# Contar conversas AllpFit
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -U hetzner_hyago_read -d chatwoot -c "
SELECT inbox_name, COUNT(*)
FROM vw_conversations_analytics_final
WHERE inbox_name = 'allpfitjpsulcloud1'
GROUP BY inbox_name;
"

# Ver todas as contas disponíveis (multi-tenant)
PGPASSWORD='c1d46b41391f' psql -h 178.156.206.184 -U hetzner_hyago_read -d chatwoot -c "
SELECT inbox_name, COUNT(*) as total_conversas
FROM vw_conversations_analytics_final
GROUP BY inbox_name
ORDER BY total_conversas DESC;
"
```

---

## 📊 Contas Disponíveis (Multi-Tenant)

Encontrei **17 contas** no Chatwoot:

| Inbox Name | Total Conversas | Empresa/Uso |
|------------|----------------|-------------|
| **cdtmossorocloud1** | 525 | CDT Mossoró (maior) |
| **allpfitjpsulrecepcao** | 344 | AllpFit Recepção |
| **cdtviamaocloud2** | 186 | CDT Via Mão |
| **cdtjpsulcloud2illumi** | 141 | CDT JP Sul Illuminovo |
| **cdtjpsulcloud1** | 88 | CDT JP Sul |
| **allpfitjpsulcloud1** | 88 | AllpFit JP Sul ⭐ |
| **geniaicloud1** | 11 | GeniAI (testes?) |
| **cdtviamaoclouddialog1** | 8 | CDT Via Mão Dialog |
| **geniaiteste** | 7 | GeniAI Testes |
| **cdtjpsul_posvenda** | 7 | CDT Pós-venda |
| **allpfitjpsulcloud2** | - | AllpFit Cloud 2 |
| **cdtmossorocloud2** | - | CDT Mossoró 2 |
| **cdtmossorocloud2dialog** | - | CDT Mossoró Dialog |
| **cdtjpsulcloud2illuminovo** | - | CDT Illuminovo |
| **cdtjpsulcloud2illuminovoo** | - | CDT Illuminovoo |
| **geniai_** | - | GeniAI |
| **geniaicloud2** | - | GeniAI Cloud 2 |

**Total geral**: ~1.400 conversas

---

## 🏗️ Estrutura da View

A view `vw_conversations_analytics_final` contém **118 campos**:

### **Principais Campos:**

**Identificação:**
- `conversation_id` (PK)
- `display_id`
- `conversation_uuid`
- `account_id`

**Status:**
- `status` (0=open, 1=resolved, 2=pending, 3=snoozed, 4=closed)
- `priority` (0-4)

**Contato:**
- `contact_id`
- `contact_name`
- `contact_email`
- `contact_phone`

**Inbox (Tenant):**
- `inbox_id`
- `inbox_name` ⭐ (usado para filtrar por conta)
- `inbox_channel_type`
- `inbox_timezone`

**Timestamps:**
- `conversation_created_at`
- `conversation_updated_at`
- `last_activity_at`

**Atribuição:**
- `assignee_id`
- `assignee_name`
- `team_id`

**Mensagens:**
- `message_compiled` (JSONB)
- `message_count`
- `bot_message_count`
- `human_message_count`

---

## 🎯 Query Exemplo: Filtrar por Conta

```sql
-- Ver conversas da AllpFit
SELECT
    conversation_id,
    display_id,
    contact_name,
    contact_phone,
    inbox_name,
    status,
    conversation_created_at,
    message_count
FROM vw_conversations_analytics_final
WHERE inbox_name = 'allpfitjpsulcloud1'
ORDER BY conversation_updated_at DESC
LIMIT 10;

-- Ver conversas de TODAS as contas CDT
SELECT
    inbox_name,
    COUNT(*) as total,
    COUNT(DISTINCT contact_phone) as leads_unicos,
    MAX(conversation_updated_at) as ultima_atualizacao
FROM vw_conversations_analytics_final
WHERE inbox_name LIKE 'cdt%'
GROUP BY inbox_name
ORDER BY total DESC;

-- Análise multi-tenant: top contas por volume
SELECT
    inbox_name,
    COUNT(*) as total_conversas,
    COUNT(DISTINCT DATE(conversation_created_at)) as dias_ativos,
    MIN(conversation_created_at) as primeira_conversa,
    MAX(conversation_updated_at) as ultima_conversa
FROM vw_conversations_analytics_final
GROUP BY inbox_name
ORDER BY total_conversas DESC;
```

---

## 🔐 Segurança e Permissões

### **Usuário: hetzner_hyago_read**

✅ **Tem permissão para:**
- CONNECT no database `chatwoot`
- SELECT na view `vw_conversations_analytics_final`
- SELECT em outras views públicas

❌ **NÃO tem permissão para:**
- INSERT, UPDATE, DELETE (somente leitura)
- CREATE, DROP (não pode criar/deletar objetos)
- Acessar tabelas fora do schema `public`

**Isso é PERFEITO para analytics!** Read-only protege os dados.

---

## 🚀 Próximos Passos para Multi-Tenant

### **1. Criar Tabela de Contas no Banco Local**

```sql
-- No banco allpfit (local)
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    inbox_name VARCHAR(255) UNIQUE NOT NULL,  -- Nome do inbox no Chatwoot
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#007AFF',
    created_at TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT true
);

-- Inserir contas existentes
INSERT INTO accounts (name, inbox_name) VALUES
('AllpFit JP Sul', 'allpfitjpsulcloud1'),
('AllpFit Recepção', 'allpfitjpsulrecepcao'),
('CDT Mossoró', 'cdtmossorocloud1'),
('CDT Via Mão', 'cdtviamaocloud2'),
('CDT JP Sul', 'cdtjpsulcloud1');

-- Adicionar account_id nas tabelas existentes
ALTER TABLE conversas_analytics
ADD COLUMN account_id INTEGER REFERENCES accounts(id);

-- Popular com dados existentes (AllpFit = ID 1)
UPDATE conversas_analytics
SET account_id = 1
WHERE inbox_name = 'allpfitjpsulcloud1';
```

### **2. Modificar ETL para Multi-Tenant**

Adicionar no ETL:
- Loop por todas as contas ativas
- Filtro `WHERE inbox_name = account.inbox_name`
- Salvar `account_id` em cada registro

### **3. Criar Página de Login**

```python
# pages/00_Login.py
import streamlit as st
from utils.db_connector import get_all_accounts

st.title("🏢 Seleção de Conta")

accounts = get_all_accounts()
selected = st.selectbox("Escolha sua conta:", accounts)

if st.button("Acessar Dashboard"):
    st.session_state.account_id = selected['id']
    st.session_state.account_name = selected['name']
    st.switch_page("pages/01_Dashboard.py")
```

### **4. Filtrar Dashboard por Conta**

```python
# No dashboard.py
if 'account_id' not in st.session_state:
    st.switch_page("pages/00_Login.py")

account_id = st.session_state.account_id

# Todas as queries devem filtrar:
query = f"""
    SELECT * FROM conversas_analytics
    WHERE account_id = {account_id}
    ...
"""
```

---

## 📝 Checklist de Configuração

### **pgAdmin**
- [ ] Criar servidor "GeniAI Analytics - Chatwoot"
- [ ] Testar conexão com credenciais corretas
- [ ] Navegar até database `chatwoot`
- [ ] Abrir view `vw_conversations_analytics_final`
- [ ] Rodar query de exemplo

### **Multi-Tenant**
- [ ] Criar tabela `accounts` no banco local
- [ ] Inserir contas existentes
- [ ] Adicionar `account_id` em `conversas_analytics`
- [ ] Modificar ETL para suportar múltiplas contas
- [ ] Criar página de login
- [ ] Filtrar dashboard por conta

### **Teste**
- [ ] Conectar via psql com credenciais corretas
- [ ] Contar conversas de cada inbox
- [ ] Verificar campos disponíveis na view
- [ ] Testar query multi-tenant

---

## 🎉 RESUMO

✅ **Credenciais Corretas:**
- User: `hetzner_hyago_read`
- Pass: `c1d46b41391f`

✅ **Conexão Testada:**
- Host: 178.156.206.184
- Database: chatwoot
- View: vw_conversations_analytics_final

✅ **17 Contas Disponíveis:**
- AllpFit (2 inboxes)
- CDT (várias unidades)
- GeniAI (testes)

✅ **Pronto para:**
- Configurar pgAdmin
- Visualizar dados
- Implementar multi-tenant

---

**Data**: 2025-11-04
**Status**: ✅ Funcionando
**Próximo Passo**: Configurar pgAdmin + Multi-tenant