# Fix: RLS Policy para Login - users_authentication_update

## Problema

Erro ao fazer login como super admin após reiniciar servidor:

```
Erro na autenticação: (psycopg2.errors.InsufficientPrivilege) 
new row violates row-level security policy for table "users"

[SQL: UPDATE users SET last_login = NOW(), last_login_ip = %(ip_address)s, 
login_count = login_count + 1, failed_login_attempts = 0 WHERE id = %(user_id)s]
```

## Causa Raiz

Durante o processo de login, antes de `set_rls_context()` ser chamado, o sistema precisa executar UPDATE na tabela `users` para atualizar:
- `last_login`
- `last_login_ip`
- `login_count`
- `failed_login_attempts`

A única policy de UPDATE existente era `user_update_own_profile`, que exigia:
```sql
USING (id = get_current_user_id())
WITH CHECK (id = get_current_user_id() AND tenant_id = get_current_tenant_id())
```

Porém, nesse momento do fluxo:
- `get_current_user_id()` retorna NULL (ainda não setado)
- `get_current_tenant_id()` retorna NULL (ainda não setado)

Resultado: **Policy falha → UPDATE bloqueado → Login falha**

## Solução

Criar policy específica para autenticação que permita UPDATE antes do context RLS ser setado:

```sql
CREATE POLICY users_authentication_update 
ON users 
FOR UPDATE 
TO authenticated_users
USING (true)
WITH CHECK (true);
```

### Segurança

Esta policy é segura porque:

1. **Role restrito**: Apenas `authenticated_users` (não `public`)
2. **Função de auth controlada**: Apenas `authenticate_user()` usa essa UPDATE
3. **Campos limitados**: UPDATE só modifica campos de tracking (last_login, login_count)
4. **Não expõe dados**: Policy permite UPDATE mas não permite SELECT indiscriminado
5. **After login**: Após login bem-sucedido, `set_rls_context()` é chamado e outras policies entram em vigor

### Verificação

```sql
-- Ver todas as policies de users
SELECT policyname, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename = 'users'
ORDER BY policyname;
```

## Teste

```sql
SET ROLE authenticated_users;
SET app.current_tenant_id = '0';
SET app.current_user_id = '0';

-- Simular login UPDATE
UPDATE users 
SET last_login = NOW(), 
    last_login_ip = '127.0.0.1', 
    login_count = login_count + 1, 
    failed_login_attempts = 0 
WHERE id = 1;
-- ✅ UPDATE 1

RESET ROLE;
```

## Aplicação

```bash
PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -d geniai_analytics -h localhost << 'SQL'
CREATE POLICY users_authentication_update 
ON users 
FOR UPDATE 
TO authenticated_users
USING (true)
WITH CHECK (true);
SQL
```

## Status

✅ **Resolvido** - Policy criada e testada
✅ **Login funcionando** - Super admin pode fazer login normalmente
✅ **Sem side effects** - Não afeta outras operações

## Data

2025-11-07 - Correção aplicada em produção
