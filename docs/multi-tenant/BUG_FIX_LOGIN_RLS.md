# 🐛 BUG FIX: Login não redireciona para dashboard

## 📋 RESUMO DO PROBLEMA

**Sintoma:** Após fazer login com credenciais corretas, o usuário vê a mensagem de sucesso e os balões, mas permanece na tela de login ao invés de ser redirecionado para o dashboard.

**Causa Raiz Identificada:** Row-Level Security (RLS) do PostgreSQL está bloqueando o acesso do usuário `isaac` à tabela `sessions`. O usuário consegue INSERIR sessões (por causa da policy `sessions_authentication_insert` para `public`), mas NÃO consegue LER as sessões (pois não possui as roles necessárias: `admin_users` ou `authenticated_users`).

---

## 🔍 ANÁLISE TÉCNICA DETALHADA

### Fluxo do Bug

1. **Login bem-sucedido:** `authenticate_user()` valida email/senha ✅
2. **INSERT de sessão:** Session é inserida no banco com sucesso ✅
3. **COMMIT:** Transaction é committed corretamente ✅
4. **Validação de sessão:** `validate_session()` tenta ler a sessão recém-criada ❌
5. **SELECT bloqueado por RLS:** O usuário `isaac` não tem permissão para ler a tabela `sessions` devido às políticas RLS ❌
6. **Resultado:** `validate_session()` retorna `None`, fazendo o app pensar que o usuário não está autenticado ❌

### Evidências

```sql
-- Teste realizado:
INSERT INTO sessions (id, user_id, tenant_id, expires_at)
VALUES ('11111111-1111-1111-1111-111111111111', 1, 0, NOW() + INTERVAL '24 hours');
-- Resultado: INSERT 0 1 (PostgreSQL aceita o INSERT)

SELECT COUNT(*) FROM sessions;
-- Resultado: 0 (mas não conseguimos LER devido ao RLS!)
```

### Políticas RLS Atuais

**Para INSERT:**
- `sessions_authentication_insert` - Role: `{public}` - WITH CHECK: `true` ✅ (permite INSERT)

**Para SELECT:**
- `user_own_sessions` - Role: `{authenticated_users}` - USING: `(user_id = get_current_user_id())` ❌
- `admin_all_sessions` - Role: `{admin_users}` - USING: `true` ❌

**Problema:** O usuário `isaac` não possui NENHUMA dessas roles, então não consegue executar SELECT!

### Verificação das Permissões do Usuário `isaac`

```sql
-- Permissões atuais:
SELECT rolname, rolbypassrls, rolsuper FROM pg_roles WHERE rolname = 'isaac';
-- Resultado: isaac | f | f
-- (sem BYPASSRLS e sem SUPERUSER)

-- Roles atribuídas:
SELECT r.rolname FROM pg_roles r
JOIN pg_auth_members m ON r.oid = m.roleid
WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = 'isaac');
-- Resultado: 0 rows (nenhuma role atribuída)
```

---

## ✅ SOLUÇÃO

O usuário `isaac` (usuário da aplicação) precisa ter permissão para BYPASSAR as políticas RLS, pois ele é responsável por gerenciar autenticação e precisa criar/ler sessões sem restrições.

### Opção A: BYPASSRLS (RECOMENDADO)

Esta é a solução mais segura e recomendada para o usuário da aplicação:

```sql
-- Conectar como superuser postgres
psql -U postgres -d geniai_analytics

-- Conceder BYPASSRLS ao isaac
ALTER ROLE isaac BYPASSRLS;

-- Verificar
SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'isaac';
-- Deve mostrar: isaac | t
```

### Opção B: Adicionar Roles (Alternativa)

Caso não seja possível usar BYPASSRLS:

```sql
-- Conectar como superuser postgres
psql -U postgres -d geniai_analytics

-- Adicionar roles necessárias
GRANT admin_users TO isaac;
GRANT authenticated_users TO isaac;
```

---

## 🚀 COMO APLICAR O FIX

### Método 1: Via Script Automático

```bash
cd /home/tester/projetos/allpfit-analytics

# Executar o script de fix (requer acesso sudo ou postgres superuser)
sudo -u postgres psql -d geniai_analytics -c "ALTER ROLE isaac BYPASSRLS;"

# Verificar se funcionou
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics \
  -c "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'isaac';"
```

### Método 2: Via psql Manual

```bash
# 1. Conectar como postgres superuser
sudo -u postgres psql -d geniai_analytics

# 2. Executar o comando
ALTER ROLE isaac BYPASSRLS;

# 3. Verificar
SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'isaac';
-- Deve mostrar: isaac | t (true)

# 4. Sair
\q
```

### Método 3: Script Bash Fornecido

```bash
cd /home/tester/projetos/allpfit-analytics

# O script mostra os comandos SQL e tenta executá-los
./fix_rls_permissions.sh
```

---

## 🧪 TESTE APÓS O FIX

```bash
cd /home/tester/projetos/allpfit-analytics
source venv/bin/activate

# Executar teste de fluxo de login
python src/multi_tenant/test_login_flow.py
```

**Resultado esperado:**
```
✅ Autenticado!
✅ Sessão validada!
✅ Sessão existe no banco!
✅ TODOS OS TESTES PASSARAM!
```

Após isso, reinicie o Streamlit e teste o login via interface web:

```bash
./restart_multi_tenant.sh
# Acessar http://localhost:8503 e fazer login
```

---

## 📚 REFERÊNCIAS

- [PostgreSQL Row-Level Security Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Documentação do banco: `/home/tester/projetos/allpfit-analytics/docs/multi-tenant/DB_DOCUMENTATION.md`
- Seção "Row-Level Security (RLS)" no DB_DOCUMENTATION.md explica a arquitetura RLS do sistema

---

## ⚠️ IMPORTANTE

**POR QUE BYPASSRLS É SEGURO NESTE CASO?**

1. O usuário `isaac` é o usuário da **aplicação**, não um usuário final
2. A aplicação implementa sua própria camada de segurança via `st.session_state` e validação de sessões
3. O RLS é mantido para proteger queries de usuários finais (através das roles `authenticated_users` e `admin_users`)
4. BYPASSRLS permite que a aplicação gerencie autenticação sem ser bloqueada pelas próprias políticas RLS

**ALTERNATIVA FUTURA (Arquitetura):**

Se quiser manter RLS rigoroso, a solução correta seria:
1. Criar um usuário separado apenas para autenticação (ex: `auth_service`) com BYPASSRLS
2. Manter `isaac` sem BYPASSRLS para operações normais
3. Usar `auth_service` apenas nas funções de `authenticate_user()` e `validate_session()`

---

## 🎯 STATUS

- [x] Problema identificado (RLS bloqueando SELECT em sessions)
- [x] Causa raiz confirmada (falta de BYPASSRLS ou roles no usuário isaac)
- [x] Solução documentada
- [x] Script de fix criado
- [ ] **AGUARDANDO: Aplicação do fix com privilégios de postgres superuser**
- [ ] Teste completo após fix
- [ ] Limpeza de logs debug

---

**Data:** 2025-11-05
**Desenvolvedor:** Claude (Anthropic)
**Ticket:** Login redirect bug - FASE 2 Multi-Tenant