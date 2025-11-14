# ADR-001: Arquitetura Multi-Tenant com Row-Level Security (RLS)

**Status:** Aceito
**Data:** 2025-11-06
**Decisores:** Equipe GenIAI, Isaac (Cliente AllpFit)
**Contexto Técnico:** PostgreSQL 15, Python 3.11, Streamlit

---

## Contexto e Problema

A plataforma AllpFit Analytics precisa suportar múltiplos clientes (tenants) com requisitos críticos:

1. **Isolamento de Dados:** Cada cliente deve ver APENAS seus próprios dados
2. **Performance:** Queries devem ser rápidas mesmo com milhões de registros
3. **Segurança:** Impossibilidade de vazamento de dados entre tenants
4. **Escalabilidade:** Facilidade para adicionar novos clientes sem redeployment
5. **Manutenção:** Uma única instância de código e banco de dados
6. **Auditoria:** Rastreabilidade de quem acessa quais dados

### Alternativas Consideradas

#### Opção 1: Banco de Dados Separado por Tenant
- **Prós:** Isolamento físico total, backup granular
- **Contras:** Custo operacional alto, difícil manutenção de schema, escalabilidade limitada
- **Decisão:** ❌ Rejeitado - operacionalmente inviável para 10+ tenants

#### Opção 2: Schema Separado por Tenant (PostgreSQL Schemas)
- **Prós:** Isolamento lógico forte, namespace próprio
- **Contras:** Complexidade de migrations, queries cross-tenant difíceis, limite de schemas
- **Decisão:** ❌ Rejeitado - complexidade de manutenção

#### Opção 3: Tabelas Compartilhadas com Filtro por tenant_id (Aplicação)
- **Prós:** Simplicidade de schema, fácil manutenção
- **Contras:** **Risco de segurança crítico** - bug na aplicação vaza dados
- **Decisão:** ❌ Rejeitado - risco inaceitável de vazamento

#### Opção 4: Row-Level Security (RLS) do PostgreSQL ✅
- **Prós:**
  - Segurança enforced no banco (não na aplicação)
  - Performance nativa do PostgreSQL
  - Transparente para queries
  - Auditoria nativa
  - Proteção contra SQL injection
- **Contras:**
  - Requer PostgreSQL 9.5+
  - Curva de aprendizado inicial
- **Decisão:** ✅ **ESCOLHIDO**

---

## Decisão

Implementar **arquitetura multi-tenant com Row-Level Security (RLS)** do PostgreSQL:

### Componentes-Chave

#### 1. Modelo de Dados
```sql
-- Tabela de Tenants (clientes)
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Todas as tabelas têm tenant_id
CREATE TABLE conversations_analytics (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    conversation_id INTEGER NOT NULL,
    -- ... outros campos
    UNIQUE(tenant_id, conversation_id)
);
```

#### 2. Políticas RLS
```sql
-- Habilitar RLS
ALTER TABLE conversations_analytics ENABLE ROW LEVEL SECURITY;

-- Política: usuários veem apenas dados do seu tenant
CREATE POLICY tenant_isolation ON conversations_analytics
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- Exceção para super admins
CREATE POLICY super_admin_access ON conversations_analytics
    USING (current_setting('app.current_tenant_id')::INTEGER = 0);
```

#### 3. Configuração de Contexto (Middleware)
```python
def set_rls_context(engine, tenant_id, user_id):
    """Configura contexto RLS antes de cada query"""
    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL app.current_tenant_id = {tenant_id}"))
        conn.execute(text(f"SET LOCAL app.current_user_id = {user_id}"))
```

#### 4. Fluxo de Autenticação
```
Login → Validar Credenciais → Obter tenant_id →
Configurar RLS Context → Queries Automáticas Filtradas
```

---

## Consequências

### Positivas ✅

1. **Segurança Enforced no DB:** Impossível retornar dados de outro tenant (mesmo com bug)
2. **Performance:** PostgreSQL otimiza RLS nativamente (índices em tenant_id)
3. **Transparência:** Aplicação faz queries normais, filtro é automático
4. **Auditoria:** `pg_stat_activity` mostra contexto RLS de cada conexão
5. **Escalabilidade:** Adicionar novo tenant = INSERT em `tenants`, sem código
6. **Manutenção:** Uma única migration aplica a todos os tenants
7. **Backup Granular:** Possível fazer backup por tenant se necessário

### Negativas ❌

1. **Dependência de PostgreSQL:** Não funciona com MySQL/SQLite
2. **Configuração Inicial:** Requer setup cuidadoso de políticas
3. **Debug:** Precisa verificar contexto RLS em troubleshooting
4. **Connection Pooling:** Requer `SET LOCAL` (não `SET SESSION`) para pgBouncer
5. **Documentação:** Equipe precisa entender RLS para manutenção

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Contexto RLS não configurado | Média | Alto | Middleware obrigatório, testes automatizados |
| Performance degradada | Baixa | Médio | Índices em tenant_id, monitoramento de queries |
| Esquecimento de tenant_id em nova tabela | Média | Alto | Checklist de migration, template de tabela |
| Super admin acessa dados errados | Baixa | Alto | Auditoria de acessos, confirmação antes de ações |

---

## Implementação

### Fase 1: Schema Multi-Tenant (Completo)
- ✅ Criação de tabela `tenants`
- ✅ Adição de `tenant_id` em todas as tabelas
- ✅ Migração de dados existentes (AllpFit = tenant_id: 1)

### Fase 2: RLS Policies (Completo)
- ✅ Habilitação de RLS em 7 tabelas principais
- ✅ Políticas `tenant_isolation` e `super_admin_access`
- ✅ Testes de isolamento (`sql/multi_tenant/06_test_isolation.sql`)

### Fase 3: Autenticação (Completo)
- ✅ Módulo `auth/auth.py` (bcrypt, sessões UUID)
- ✅ Middleware `auth/middleware.py` (RLS context, proteção de rotas)
- ✅ Login page multi-tenant

### Fase 4: Dashboards (Completo)
- ✅ Painel admin (GeniAI - acesso a todos os tenants)
- ✅ Dashboard cliente (filtrado automaticamente por RLS)

---

## Validação

### Testes de Isolamento
```sql
-- Teste 1: Cliente vê apenas seus dados
SET app.current_tenant_id = 1;
SELECT COUNT(*) FROM conversations_analytics;
-- Esperado: Apenas dados tenant_id=1

-- Teste 2: Super admin vê tudo
SET app.current_tenant_id = 0;
SELECT COUNT(*) FROM conversations_analytics;
-- Esperado: Todos os dados
```

### Métricas de Sucesso
- ✅ 0 vazamentos de dados em testes de penetração
- ✅ Performance: queries < 200ms (com índices)
- ✅ Auditoria: 100% de acessos rastreados em `sessions`

---

## Referências

- [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/15/ddl-rowsecurity.html)
- [Multi-Tenancy with RLS (AWS Blog)](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)
- [Citus Multi-Tenant Best Practices](https://docs.citusdata.com/en/stable/sharding/multi_tenant.html)
- Documentação interna: `sql/multi_tenant/05_row_level_security.sql`

---

## Notas de Revisão

**Próxima Revisão:** 2025-12-01
**Responsável:** Isaac (GenIAI)
**Gatilhos de Revisão:**
- Adição de 10+ novos tenants
- Degradação de performance (queries > 500ms)
- Requisito de compliance (LGPD, SOC2)