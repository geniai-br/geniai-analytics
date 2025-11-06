# 👥 GUIA DE USUÁRIOS DO BANCO DE DADOS

> **Atualizado:** 2025-11-06
> **Status Atual:** johan_geniai (migração concluída)

---

## 📊 USUÁRIOS ATUAIS

### 1. `isaac`
```
Tipo: Usuário padrão
Senha: AllpFit2024@Analytics
Uso:
  - Conexões gerais
  - Compatibilidade com sistemas legados
  - Acesso ao banco remoto Chatwoot
Status: ✅ Mantido (sem alterações)
```

### 2. `johan_geniai`
```
Tipo: Owner de todas as tabelas multi-tenant
Senha: vlVMVM6UNz2yYSBlzodPjQvZh
Uso:
  - ETL Multi-Tenant
  - Operações de manutenção
  - Criação/alteração de tabelas
Status: ✅ Ativo (migrado de integracao_user)
```

---

## 🔄 QUANDO USAR CADA USUÁRIO

### Para ETL (Pipeline de Dados)
```bash
# Usar: johan_geniai
export LOCAL_DB_USER='johan_geniai'
export LOCAL_DB_PASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh'

python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1
```

**Por quê?**
- Owner das tabelas (sem RLS)
- Pode fazer UPSERT sem restrições
- Advisory locks funcionam

### Para Dashboard (Aplicação Web)
```python
# src/multi_tenant/auth/__init__.py
# Usa: isaac (com RLS quando habilitado)

DATABASE_URL = "postgresql://isaac:AllpFit2024@Analytics@localhost/geniai_analytics"
```

**Por quê?**
- RLS funciona corretamente
- Isolamento por tenant
- Segurança multi-tenant

### Para Manutenção Manual (psql)
```bash
# Usar: johan_geniai para operações sem RLS
PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' \
psql -U johan_geniai -h localhost -d geniai_analytics

# Usar: isaac para simular comportamento do app
PGPASSWORD='AllpFit2024@Analytics' \
psql -U isaac -h localhost -d geniai_analytics
```

---

## 🔑 SENHAS E SEGURANÇA

### Desenvolvimento (Atual)
```
isaac:           AllpFit2024@Analytics
integracao_user: vlVMVM6UNz2yYSBlzodPjQvZh
```

### Produção (Recomendações)
```
✅ Gerar senhas fortes (16+ caracteres)
✅ Usar variáveis de ambiente (.env)
✅ Nunca commitar senhas no git
✅ Usar secrets management (Vault, AWS Secrets Manager)
✅ Rotacionar senhas regularmente
```

### Exemplo .env (Produção)
```bash
# .env.production (NUNCA commitar!)
LOCAL_DB_USER=johan_geniai
LOCAL_DB_PASSWORD=<senha-forte-gerada>
REMOTE_DB_USER=hetzner_hyago_read
REMOTE_DB_PASSWORD=<senha-remota>
```

---

## 📝 REFERÊNCIAS RÁPIDAS

### Verificar Usuários
```sql
SELECT
    usename,
    usecreatedb,
    usesuper
FROM pg_user
WHERE usename IN ('isaac', 'johan_geniai', 'integracao_user', 'postgres')
ORDER BY usename;
```

### Verificar Ownership
```sql
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Verificar Permissões
```sql
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee IN ('isaac', 'johan_geniai', 'integracao_user')
ORDER BY grantee, table_name;
```

---

## 🎯 RESUMO

| Usuário | Tipo | Uso Principal | RLS | Status |
|---------|------|---------------|-----|--------|
| `isaac` | Padrão | Dashboard, Queries | ✅ Sim | ✅ Ativo |
| `johan_geniai` | Owner | ETL, Manutenção | ❌ Não | ✅ Ativo |

---

**Criado por:** Isaac (via Claude Code)
**Atualizado:** 2025-11-06
