# 🚀 Guia de Deploy - Views no Banco de Produção

## 📋 Pré-requisitos

Você vai precisar de:
- ✅ Acesso ao servidor de banco de dados (178.156.206.184)
- ✅ Usuário com permissão de **CREATE VIEW** (não é o `hetzner_dev_isaac_read`)
- ✅ Acesso SSH ou cliente PostgreSQL (psql, DBeaver, pgAdmin, etc.)

---

## 🔐 IMPORTANTE: Usuário Correto

**⚠️ O usuário `hetzner_dev_isaac_read` NÃO tem permissão para criar views!**

Você precisa usar um usuário com permissões de **DDL** (Data Definition Language).

Opções:
- `postgres` (superusuário)
- `admin` ou usuário específico com permissão CREATE

---

## 📁 Preparação dos Arquivos

### **Opção 1: Clonar o repositório no servidor**

```bash
# SSH no servidor
ssh seu_usuario@servidor

# Clonar o repositório
git clone git@github.com:geniai-br/allpfit-analytics.git
cd allpfit-analytics

# Checkout na branch
git checkout feature/views-modulares-analytics

# Ir para pasta das views
cd sql/modular_views/
```

---

### **Opção 2: Copiar arquivos manualmente**

Se não tiver Git no servidor:

```bash
# No seu computador local
cd /home/isaac/projects/allpfit-analytics/sql/modular_views/

# Copiar para o servidor via SCP
scp *.sql seu_usuario@servidor:/tmp/views/
```

---

## 🎯 Deploy das Views

### **Método 1: Script Automatizado (RECOMENDADO)** ✅

```bash
# Conectar ao banco com usuário ADMIN
psql -h 178.156.206.184 -p 5432 -U usuario_admin -d chatwoot

# Navegar para pasta das views
\cd /caminho/para/sql/modular_views/

# Executar script master
\i 00_deploy_all_views.sql
```

O script irá:
1. ✅ Criar as 7 views em ordem
2. ✅ Mostrar progresso
3. ✅ Verificar se foram criadas
4. ✅ Testar com uma query
5. ✅ Mostrar resumo

---

### **Método 2: Executar via DBeaver/pgAdmin**

Se preferir usar interface gráfica:

1. **Abrir DBeaver/pgAdmin**
2. **Conectar ao banco:**
   - Host: 178.156.206.184
   - Port: 5432
   - Database: chatwoot
   - User: usuario_admin (com permissão CREATE)

3. **Executar scripts na ordem:**
   ```
   01_vw_conversations_base_complete.sql
   02_vw_messages_compiled_complete.sql
   03_vw_csat_base.sql
   04_vw_conversation_metrics_complete.sql
   05_vw_message_stats_complete.sql
   06_vw_temporal_metrics.sql
   07_vw_conversations_analytics_final.sql
   ```

4. **Verificar:**
   ```sql
   SELECT * FROM pg_views
   WHERE viewname LIKE 'vw_%'
   AND schemaname = 'public'
   ORDER BY viewname;
   ```

---

### **Método 3: Uma linha (se tiver os arquivos locais)**

```bash
psql -h 178.156.206.184 -p 5432 -U usuario_admin -d chatwoot \
  -f 01_vw_conversations_base_complete.sql \
  -f 02_vw_messages_compiled_complete.sql \
  -f 03_vw_csat_base.sql \
  -f 04_vw_conversation_metrics_complete.sql \
  -f 05_vw_message_stats_complete.sql \
  -f 06_vw_temporal_metrics.sql \
  -f 07_vw_conversations_analytics_final.sql
```

---

## ✅ Verificação Pós-Deploy

### **1. Conferir se as views foram criadas:**

```sql
SELECT
    schemaname,
    viewname,
    viewowner
FROM pg_views
WHERE viewname IN (
    'vw_conversations_base_complete',
    'vw_messages_compiled_complete',
    'vw_csat_base',
    'vw_conversation_metrics_complete',
    'vw_message_stats_complete',
    'vw_temporal_metrics',
    'vw_conversations_analytics_final'
)
ORDER BY viewname;
```

**Resultado esperado:** 7 views listadas

---

### **2. Testar contagem de registros:**

```sql
-- Deve retornar o número de conversas (ex: 4073)
SELECT COUNT(*) as total FROM vw_conversations_analytics_final;
```

---

### **3. Testar uma query completa:**

```sql
-- Buscar 1 registro com todos os campos
SELECT *
FROM vw_conversations_analytics_final
LIMIT 1;
```

**Resultado esperado:** 1 linha com ~150 colunas

---

### **4. Testar performance:**

```sql
-- Query com filtro (deve ser rápida)
SELECT
    conversation_id,
    display_id,
    status,
    contact_name,
    inbox_name,
    csat_rating,
    first_response_time_minutes
FROM vw_conversations_analytics_final
WHERE conversation_date >= CURRENT_DATE - 7
LIMIT 100;
```

**Tempo esperado:** < 2 segundos

---

### **5. Verificar permissões do usuário read-only:**

```sql
-- Conectar com o usuário READ ONLY
\c - hetzner_dev_isaac_read

-- Testar SELECT (deve funcionar)
SELECT COUNT(*) FROM vw_conversations_analytics_final;

-- Testar DROP (deve dar erro de permissão - isso é BOM!)
DROP VIEW vw_conversations_analytics_final;
-- Erro esperado: ERROR: must be owner of view
```

---

## 🔄 Se precisar atualizar/recriar as views

```sql
-- Conectar como admin
\c - usuario_admin

-- Recriar todas (o CREATE OR REPLACE já substitui)
\i 00_deploy_all_views.sql

-- Ou recriar apenas uma específica:
\i 04_vw_conversation_metrics_complete.sql
```

---

## ❌ Troubleshooting

### **Erro: "permission denied for table X"**
**Causa:** Usuário não tem permissão nas tabelas base
**Solução:**
```sql
-- Garantir permissões (como superusuário)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO usuario_admin;
```

---

### **Erro: "view already exists"**
**Causa:** View já existe e não está usando CREATE OR REPLACE
**Solução:**
```sql
-- Remover a view antiga
DROP VIEW IF EXISTS nome_da_view CASCADE;

-- Recriar
\i arquivo_da_view.sql
```

---

### **Erro: "column does not exist"**
**Causa:** Nome de coluna diferente no seu banco
**Solução:** Verificar estrutura das tabelas:
```sql
\d conversations
\d messages
\d contacts
-- etc...
```

---

## 📊 Validação Final - Checklist

Antes de considerar o deploy concluído, verifique:

- [ ] 7 views criadas com sucesso
- [ ] Contagem de registros bate (ex: 4073)
- [ ] Query de teste retorna dados
- [ ] Permissões do usuário read-only funcionando
- [ ] Performance aceitável (queries < 5s)
- [ ] Nenhum erro no log do PostgreSQL

---

## 🎯 Próximo Passo: Atualizar o ETL

Após confirmar que as views estão funcionando no banco de produção:

1. ✅ Voltar ao projeto local
2. ✅ Atualizar o ETL para usar `vw_conversations_analytics_final`
3. ✅ Testar extração
4. ✅ Configurar banco local
5. ✅ Desenvolver dashboard

**Documentação:** Ver arquivo `docs/update_etl.md` (próximo passo)

---

## 📞 Suporte

Se encontrar algum problema:

1. Verificar logs do PostgreSQL
2. Testar views individuais (1 a 6) antes da final (7)
3. Conferir permissões do usuário
4. Validar estrutura das tabelas base

---

**Criado em:** 2025-10-17
**Versão:** 1.0
**Status:** Pronto para uso
