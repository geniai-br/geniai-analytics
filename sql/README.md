# 🗄️ Scripts SQL Multi-Tenant

Scripts para criar e configurar o banco de dados multi-tenant `geniai_analytics`.

---

## 📋 Ordem de Execução

Execute os scripts **nesta ordem exata**:

```bash
# 1. Criar banco de dados
psql -U postgres -f 01_create_database.sql

# 2. Criar schema (tabelas, índices, triggers)
psql -U postgres -d geniai_analytics -f 02_create_schema.sql

# 3. Popular dados iniciais (tenants, users)
psql -U postgres -d geniai_analytics -f 03_seed_data.sql

# 4. (Opcional) Migrar dados do banco allpfit
psql -U postgres -d geniai_analytics -f 04_migrate_allpfit_data.sql

# 5. Implementar Row-Level Security
psql -U postgres -d geniai_analytics -f 05_row_level_security.sql

# 6. (Opcional) Testar isolamento
psql -U postgres -d geniai_analytics -f 06_test_isolation.sql
```

---

## 📄 Descrição dos Scripts

### 01_create_database.sql
**Objetivo:** Criar banco `geniai_analytics` e configurações iniciais

**O que faz:**
- Cria database `geniai_analytics`
- Instala extensões (uuid-ossp, pgcrypto, dblink)
- Cria roles (authenticated_users, admin_users, etl_service)
- Configura timezone e locale

**Saída esperada:**
```
CREATE DATABASE
CREATE EXTENSION
CREATE ROLE
```

---

### 02_create_schema.sql
**Objetivo:** Criar todas as tabelas do sistema multi-tenant

**Tabelas criadas:**
1. `tenants` - Clientes da GeniAI
2. `users` - Usuários por tenant + admins
3. `sessions` - Controle de sessões de login
4. `inbox_tenant_mapping` - Mapear inbox_id → tenant_id
5. `tenant_configs` - Personalizações (logo, cores, features)
6. `audit_logs` - Log de auditoria de ações

**Modificações em tabelas existentes:**
- `conversations_analytics` + `tenant_id` + `inbox_id`
- `conversas_analytics_ai` + `tenant_id`
- `etl_control` + `tenant_id` + `inbox_ids`

**Saída esperada:**
```
CREATE TABLE (9 tabelas)
CREATE INDEX (25+ índices)
CREATE TRIGGER (5 triggers)
```

---

### 03_seed_data.sql
**Objetivo:** Popular dados iniciais

**Dados inseridos:**
1. **Tenants:**
   - ID 0: GeniAI Admin (interno)
   - ID 1: AllpFit CrossFit (primeiro cliente)

2. **Usuários:**
   - `admin@geniai.com.br` (super_admin)
   - `suporte@geniai.com.br` (admin)
   - `isaac@allpfit.com.br` (admin AllpFit)
   - `visualizador@allpfit.com.br` (client AllpFit)

3. **Inbox Mapping:**
   - Inbox 1, 2 → Tenant 1 (AllpFit)

4. **Configurações:**
   - Branding e features habilitadas

**Senha padrão (DEV):** `senha123`
⚠️ **ALTERAR EM PRODUÇÃO!**

**Saída esperada:**
```
INSERT 0 2  (tenants)
INSERT 0 4  (users)
INSERT 0 2  (inbox_mapping)
INSERT 0 2  (tenant_configs)
```

---

### 04_migrate_allpfit_data.sql
**Objetivo:** Migrar dados do banco `allpfit` → `geniai_analytics`

**Pré-requisitos:**
- Banco `allpfit` deve existir e estar acessível
- Extensão `dblink` instalada
- **BACKUP do banco allpfit feito!**

**O que faz:**
- Conecta no banco `allpfit` via dblink
- Copia `conversas_analytics` → `conversations_analytics` + `tenant_id=1`
- Copia `conversas_analytics_ai` → `conversas_analytics_ai` + `tenant_id=1`
- Copia `etl_control` → `etl_control` + `tenant_id=1`
- Atualiza `tenants.inbox_ids` com IDs reais
- Valida contagens

**⚠️ IMPORTANTE:**
Os blocos `INSERT` estão **comentados por segurança**.
Descomentar após revisão e backup!

**Saída esperada:**
```
INSERT 0 N  (N = número de conversas migradas)
```

---

### 05_row_level_security.sql
**Objetivo:** Implementar isolamento de dados via RLS (Row-Level Security)

**O que faz:**
- Habilita RLS em todas as tabelas de dados
- Cria funções auxiliares (`get_current_tenant_id()`, `is_admin_user()`)
- Cria políticas (policies) para clientes e admins
- Configura grants (permissões)

**Políticas criadas:**
- **Clientes:** Veem apenas dados do próprio tenant
- **Admins:** Veem dados de todos os tenants
- **ETL:** Bypass RLS para inserir dados

**Como funciona:**
```sql
-- Aplicação configura sessão:
SET app.current_tenant_id = 1;
SET ROLE authenticated_users;

-- Query sem WHERE é automaticamente filtrada:
SELECT * FROM conversations_analytics;
-- Retorna APENAS tenant_id = 1 ✅
```

**Saída esperada:**
```
ALTER TABLE ... ENABLE ROW LEVEL SECURITY (9 tabelas)
CREATE POLICY (30+ policies)
GRANT (múltiplos grants)
```

---

### 06_test_isolation.sql
**Objetivo:** Testar isolamento entre tenants (validar RLS)

**Testes executados:**
1. ✅ Cliente vê apenas próprios dados
2. ✅ Cliente NÃO vê dados de outros tenants
3. ✅ Admin vê dados de todos os tenants
4. ✅ Tenant inexistente retorna vazio
5. ✅ Sem session variables = sem acesso
6. ✅ RLS funciona em todas as tabelas

**Como executar:**
```bash
psql -d geniai_analytics -f 06_test_isolation.sql
```

**Saída esperada:**
Todos os testes devem mostrar `✅ OK`

**Se houver `❌ FALHOU`:**
- Revisar 05_row_level_security.sql
- Verificar se RLS está habilitado
- Verificar session variables

---

## 🔧 Troubleshooting

### Erro: "database geniai_analytics already exists"
```bash
# Dropar banco (⚠️ CUIDADO - perda de dados!)
psql -U postgres -c "DROP DATABASE geniai_analytics;"

# Ou ignorar erro:
psql -U postgres -c "CREATE DATABASE geniai_analytics;" || true
```

### Erro: "role authenticated_users already exists"
```bash
# Roles já existem - OK para ignorar
# Script usa IF NOT EXISTS
```

### Erro: "could not connect to database allpfit"
```bash
# Banco allpfit não existe ou não está acessível
# Se não tem dados para migrar: pular script 04
```

### Erro: "permission denied for table conversations_analytics"
```bash
# Verificar grants:
psql -d geniai_analytics -c "\dp conversations_analytics"

# Rodar novamente 05_row_level_security.sql (seção GRANTS)
```

---

## 📊 Verificações Úteis

### Listar tabelas criadas
```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Verificar RLS habilitado
```sql
SELECT tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public';
```

### Listar policies criadas
```sql
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Contar registros por tenant
```sql
SELECT
    tenant_id,
    COUNT(*) AS conversations
FROM conversations_analytics
GROUP BY tenant_id;
```

### Ver usuários criados
```sql
SELECT
    u.email,
    u.role,
    t.name AS tenant_name
FROM users u
JOIN tenants t ON t.id = u.tenant_id
WHERE u.deleted_at IS NULL;
```

---

## 🔐 Segurança

### Alterar senhas em produção
```sql
-- Usuários
UPDATE users
SET password_hash = '$2b$12$NEW_HASH_HERE'
WHERE email = 'admin@geniai.com.br';

-- Role ETL
ALTER ROLE etl_service WITH PASSWORD 'senha_forte_aqui';
```

### Restringir acesso por IP (pg_hba.conf)
```
# Apenas localhost pode conectar
host geniai_analytics all 127.0.0.1/32 md5

# Ou IP específico
host geniai_analytics etl_service 192.168.1.100/32 md5
```

### Habilitar SSL
```
# postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

---

## 📚 Próximos Passos

Após executar todos os scripts:

1. ✅ **Validar isolamento:** Executar `06_test_isolation.sql`
2. ✅ **Implementar autenticação:** Criar módulo `src/multi_tenant/auth/`
3. ✅ **Adaptar ETL:** Criar `src/multi_tenant/etl_v4/`
4. ✅ **Modificar dashboard:** Adicionar filtro por tenant
5. ✅ **Deploy:** Atualizar aplicação para usar novo banco

---

## 📞 Suporte

**Documentação pública:** `docs/public/`
**Visão Geral:** `docs/public/VISAO_GERAL_PROJETO.md`
**Arquitetura DB:** `docs/public/ARQUITETURA_DB.md`
**Documentação privada:** `docs/private/` (credenciais, checkpoints)

---

**Última atualização:** 2025-11-04
**Versão:** 1.0.0