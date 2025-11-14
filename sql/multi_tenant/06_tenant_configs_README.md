# Tabela `tenant_configs` - Documentação Completa

## Visão Geral

A tabela `tenant_configs` armazena configurações de personalização visual e funcionalidades específicas para cada cliente (tenant) do sistema GeniAI Analytics.

**Arquivo:** `/home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs.sql`

**Banco:** `geniai_analytics` (PostgreSQL)

**Versão:** 1.0

---

## 📋 Estrutura da Tabela

### Campos Principais

| Campo | Tipo | Default | NOT NULL | Constraints | Descrição |
|-------|------|---------|----------|-------------|-----------|
| `tenant_id` | INTEGER | - | ✅ | PK, FK (tenants) | ID do cliente |
| `logo_url` | TEXT | NULL | ❌ | URL HTTPS (max 500) | URL do logo customizado |
| `favicon_url` | TEXT | NULL | ❌ | URL HTTPS (max 500) | URL do favicon customizado |
| `primary_color` | VARCHAR(7) | #1E40AF | ✅ | Hex regex `^#[0-9A-Fa-f]{6}$` | Cor principal (ex: #FF6B35) |
| `secondary_color` | VARCHAR(7) | #10B981 | ✅ | Hex regex | Cor secundária (ex: #1E90FF) |
| `accent_color` | VARCHAR(7) | #F59E0B | ✅ | Hex regex | Cor de destaque/acento |
| `custom_css` | TEXT | NULL | ❌ | Max 50KB | CSS personalizado adicional |
| `features` | JSONB | (default) | ✅ | Must be object | Features habilitadas/desabilitadas |
| `notifications` | JSONB | (default) | ✅ | Must be object | Config de notificações |
| `dashboard_config` | JSONB | (default) | ✅ | Must be object | Customização do dashboard |
| `integrations` | JSONB | {} | ✅ | Must be object | Integrações externas (APIs) |
| `advanced_config` | JSONB | (default) | ✅ | Must be object | Rate limits, timezone, etc |
| `version` | INTEGER | 1 | ✅ | - | Versionamento automático |
| `change_log` | JSONB | [] | ✅ | Array JSON | Histórico das últimas 50 mudanças |
| `created_at` | TIMESTAMP | NOW() | ✅ | - | Data de criação |
| `updated_at` | TIMESTAMP | NOW() | ✅ | Atualizado por trigger | Data da última mudança |
| `updated_by_user_id` | INTEGER | NULL | ❌ | FK (users) | Quem fez a última mudança |

---

## 🎨 Exemplo de Configuração Completa

### AllpFit (tenant_id = 1)

```json
{
  "tenant_id": 1,
  "logo_url": "https://allpfit.com.br/logo.png",
  "favicon_url": "https://allpfit.com.br/favicon.ico",
  "primary_color": "#FF6B35",      // Laranja vibrante
  "secondary_color": "#1E90FF",    // Azul
  "accent_color": "#00CED1",       // Turquoise
  "custom_css": null,
  "features": {
    "export_csv": true,
    "export_pdf": true,
    "export_excel": false,
    "advanced_filters": true,
    "custom_reports": true,
    "api_access": false,
    "webhooks": false,
    "ai_analysis": true,
    "crm_integration": true,
    "scheduled_reports": true
  },
  "notifications": {
    "email_reports": false,
    "email_alerts": true,
    "sms_alerts": false,
    "webhook_url": null,
    "alert_threshold": 100,
    "alert_email": "isaac@allpfit.com.br"
  },
  "dashboard_config": {
    "show_welcome_message": true,
    "default_date_range": "30d",
    "show_revenue_widget": true,
    "show_customer_satisfaction": true,
    "show_ai_analysis": true,
    "kpi_cards_order": [
      "total_conversations",
      "ai_resolved",
      "conversion_rate",
      "visits_scheduled"
    ]
  },
  "integrations": {},
  "advanced_config": {
    "rate_limit_api": 1000,
    "max_concurrent_sessions": 5,
    "data_retention_days": 365,
    "timezone": "America/Sao_Paulo"
  },
  "version": 1,
  "created_at": "2025-11-06T...",
  "updated_at": "2025-11-06T..."
}
```

---

## 🔧 Funções Helper

### 1. `get_default_tenant_config()`

Retorna configuração padrão (baseline) para novos tenants.

**Assinatura:**
```sql
get_default_tenant_config()
RETURNS TABLE (
    logo_url TEXT,
    favicon_url TEXT,
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    custom_css TEXT,
    features JSONB,
    notifications JSONB,
    dashboard_config JSONB,
    integrations JSONB,
    advanced_config JSONB
)
```

**Uso:**
```sql
-- Inserir novo tenant com configuração padrão
INSERT INTO tenant_configs (tenant_id, features, notifications, ...)
SELECT 2, (get_default_tenant_config()).*;
```

---

### 2. `apply_tenant_config_defaults(tenant_id INTEGER)`

Aplica valores padrão a campos NULL/vazios de um tenant. **Idempotente** (pode ser chamada múltiplas vezes com segurança).

**Assinatura:**
```sql
apply_tenant_config_defaults(p_tenant_id INTEGER)
RETURNS void
```

**Uso:**
```sql
-- Preencher campos NULL com defaults
SELECT apply_tenant_config_defaults(1);

-- Aplicar a todos os tenants
DO $$
DECLARE
    t_id INTEGER;
BEGIN
    FOR t_id IN SELECT DISTINCT tenant_id FROM tenant_configs LOOP
        PERFORM apply_tenant_config_defaults(t_id);
    END LOOP;
END $$;
```

---

### 3. `is_feature_enabled(tenant_id INTEGER, feature_name TEXT)`

Verifica se um feature específico está habilitado para um tenant.

**Assinatura:**
```sql
is_feature_enabled(p_tenant_id INTEGER, p_feature_name TEXT)
RETURNS BOOLEAN
```

**Retorna:**
- `TRUE` = feature ativado
- `FALSE` = feature desativado ou não existe

**Uso:**
```sql
-- Verificar se AllpFit pode exportar CSV
SELECT is_feature_enabled(1, 'export_csv');  -- true

-- Verificar acesso a API
SELECT is_feature_enabled(1, 'api_access');  -- false

-- Em aplicação (pseudocódigo):
IF is_feature_enabled(@tenant_id, 'export_csv') THEN
    SHOW_EXPORT_BUTTON();
END IF;
```

---

### 4. `get_notification_config(tenant_id INTEGER)`

Retorna configurações de notificação de um tenant.

**Assinatura:**
```sql
get_notification_config(p_tenant_id INTEGER)
RETURNS JSONB
```

**Uso:**
```sql
-- Obter config de notificações do AllpFit
SELECT get_notification_config(1);

-- Resultado:
-- {"email_alerts": true, "alert_threshold": 100, ...}
```

---

## 📍 Índices para Performance

| Índice | Tipo | Campo | Propósito |
|--------|------|-------|----------|
| `idx_tenant_configs_tenant_id` | B-tree | tenant_id | FK lookups (já é PK, redundante mas explícito) |
| `idx_tenant_configs_features_gin` | GIN | features | Buscar por features JSON |
| `idx_tenant_configs_notifications_gin` | GIN | notifications | Buscar por notificações |
| `idx_tenant_configs_dashboard_gin` | GIN | dashboard_config | Buscar por config dashboard |
| `idx_tenant_configs_integrations_gin` | GIN | integrations | Buscar integrações |
| `idx_tenant_configs_updated_at` | B-tree DESC | updated_at | Configs alteradas recentemente |

**Exemplo de query otimizada:**
```sql
-- Buscar tenants com feature específico ativado (usa índice GIN)
SELECT tc.tenant_id, t.name
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"api_access": true}'::JSONB;
```

---

## 🔄 Triggers Automáticos

### 1. `trigger_update_tenant_configs_updated_at`

**Descrição:** Atualiza automaticamente `updated_at` e incrementa `version` a cada mudança.

**Quando dispara:** Antes de UPDATE

**O que faz:**
- Define `updated_at = NOW()`
- Incrementa `version += 1`

**Exemplo:**
```sql
UPDATE tenant_configs
SET primary_color = '#FF00FF'
WHERE tenant_id = 1;
-- Automaticamente: updated_at = NOW(), version = 2
```

---

### 2. `trigger_log_tenant_configs_changes`

**Descrição:** Registra histórico de mudanças em `change_log`.

**Quando dispara:** Antes de UPDATE (apenas se há mudanças)

**O que faz:**
- Detecta campos que mudaram (exceto `updated_at`, `version`, `change_log`)
- Registra timestamp, versão, e campos alterados
- Mantém apenas últimas 50 mudanças (evita crescimento infinito)

**Exemplo:**
```sql
-- Histórico fica assim:
[
  {
    "timestamp": "2025-11-06T14:30:00",
    "version": 3,
    "changed_fields": {
      "primary_color": "#FF6B35"
    }
  },
  {
    "timestamp": "2025-11-06T14:25:00",
    "version": 2,
    "changed_fields": {
      "logo_url": "https://..."
    }
  }
  // ... até 50 entradas
]
```

---

## 📝 Queries Úteis

### Buscar configuração de um tenant

```sql
SELECT
    tenant_id,
    primary_color,
    secondary_color,
    features,
    notifications
FROM tenant_configs
WHERE tenant_id = 1;
```

### Listar tenants com feature específico ativado

```sql
SELECT tc.tenant_id, t.name, tc.primary_color
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"export_csv": true}'::JSONB
  AND t.status = 'active';
```

### Buscar tenants que usam um webhook específico

```sql
SELECT tc.tenant_id, t.name,
       tc.notifications->>'webhook_url' AS webhook
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.notifications->>'webhook_url' IS NOT NULL;
```

### Ver histórico de mudanças de um tenant

```sql
SELECT
    tc.version,
    tc.updated_at,
    jsonb_array_elements(tc.change_log) ->> 'timestamp' AS change_time,
    jsonb_array_elements(tc.change_log) -> 'changed_fields' AS changes
FROM tenant_configs tc
WHERE tc.tenant_id = 1
ORDER BY tc.updated_at DESC;
```

### Atualizar cores de um tenant

```sql
UPDATE tenant_configs
SET
    primary_color = '#FF6B35',
    secondary_color = '#1E90FF',
    updated_by_user_id = 123  -- ID do usuário que fez a mudança
WHERE tenant_id = 1;
```

### Habilitar feature para um tenant

```sql
UPDATE tenant_configs
SET features = jsonb_set(
    features,
    '{api_access}',
    'true'::jsonb
)
WHERE tenant_id = 1;
```

### Desabilitar múltiplos features

```sql
UPDATE tenant_configs
SET features = features
    - 'api_access'      -- Remove completamente a chave
    - 'webhooks'
WHERE tenant_id = 1;
```

### Ver tamanho em bytes da tabela

```sql
SELECT
    pg_size_pretty(pg_total_relation_size('tenant_configs')) AS total_size,
    pg_size_pretty(pg_indexes_size('tenant_configs')) AS indexes_size;
```

---

## ⚠️ Restrições e Validações

### Validações de Constraints

1. **Logo URL:**
   - Formato: `^https?://` (deve começar com http:// ou https://)
   - Tamanho máximo: 500 caracteres
   - NULL é permitido (usa logo padrão)

2. **Cores (hex):**
   - Formato: `^#[0-9A-Fa-f]{6}$` (ex: #FF6B35)
   - Comprimento: exatamente 7 caracteres
   - Obrigatório (NOT NULL)
   - Valores default: primary=#1E40AF, secondary=#10B981, accent=#F59E0B

3. **CSS Customizado:**
   - Tamanho máximo: 50KB
   - NULL é permitido (sem CSS adicional)

4. **JSONB Objects:**
   - `features`, `notifications`, `dashboard_config`, `integrations`, `advanced_config`
   - Devem ser objetos JSON válidos (não arrays)
   - Constraint: `jsonb_typeof(field) = 'object'`

---

## 🚀 Deployment

### Executar o script

```bash
# Conectar ao banco e executar
psql -U postgres -d geniai_analytics -f sql/multi_tenant/06_tenant_configs.sql

# Ou via Docker
docker exec -i postgres psql -U postgres -d geniai_analytics < sql/multi_tenant/06_tenant_configs.sql
```

### Sequência de scripts (ordem completa)

```bash
1. 01_create_database.sql          # Criar banco, extensões, roles
2. 02_create_schema.sql             # Criar tabelas (tenants, users, sessions, etc)
3. 03_seed_data.sql                 # Seed data inicial (tenants, users)
4. 04_migrate_allpfit_data.sql      # Migrar dados AllpFit
5. 05_row_level_security.sql        # Habilitar RLS
6. 06_tenant_configs.sql            # ← VOCÊ ESTÁ AQUI (criar configs de tenants)
7. 07_create_analytics_tables.sql   # Tabelas de analytics
8. 08_migrate_data.sql              # Migrar dados de analytics
9. 09_add_rls_analytics.sql         # RLS em analytics
10. 10_test_rls_analytics.sql       # Testes
```

---

## 🔐 Segurança

### Dados Sensíveis

⚠️ **IMPORTANTE:** A tabela `integrations` pode conter credenciais de APIs. Em produção:

1. **Criptografar credenciais** usando extensão `pgcrypto`:
   ```sql
   UPDATE tenant_configs
   SET integrations = jsonb_set(
       integrations,
       '{slack, webhook_url}',
       to_jsonb(pgp_sym_encrypt(value, 'encryption_key'))
   )
   WHERE integrations->>'slack' IS NOT NULL;
   ```

2. **Restringir acesso** via RLS ou GRANT/REVOKE:
   ```sql
   -- Apenas admin pode ver integrations
   CREATE POLICY admin_only_integrations ON tenant_configs
       FOR SELECT TO authenticated_users
       USING (integrations IS NULL);
   ```

3. **Auditoria:** Todas as mudanças são logadas em `audit_logs`.

---

## 📊 Casos de Uso

### 1. Customização Visual por Cliente

```sql
-- App busca cores do cliente
SELECT primary_color, secondary_color, accent_color, logo_url
FROM tenant_configs
WHERE tenant_id = 1;

-- Resultado:
-- primary_color  | secondary_color | accent_color | logo_url
-- ===============|=================|==============|===================
-- #FF6B35        | #1E90FF         | #00CED1      | https://allpfit...
```

### 2. Feature Flags por Tenant

```sql
-- App verifica se pode exportar PDF
IF is_feature_enabled(@tenant_id, 'export_pdf') THEN
    SHOW_EXPORT_PDF_BUTTON();
END IF;
```

### 3. Personalizações do Dashboard

```sql
-- Dashboard carrega ordem de KPIs customizada
SELECT dashboard_config->>'kpi_cards_order' AS kpi_order
FROM tenant_configs
WHERE tenant_id = 1;

-- Resultado: ["total_conversations", "ai_resolved", "conversion_rate", "visits_scheduled"]
```

### 4. Timezone por Tenant

```sql
-- App usa timezone do tenant para reports
SELECT advanced_config->>'timezone' AS tz
FROM tenant_configs
WHERE tenant_id = 1;

-- Usar em query:
-- SELECT ... AT TIME ZONE (advanced_config->>'timezone')
```

---

## 🐛 Troubleshooting

### Problema: Cores inválidas

**Erro:** `new row for relation "tenant_configs" violates check constraint "chk_primary_color_format"`

**Solução:** Usar formato hex válido com 6 dígitos (sem prefixo):
```sql
-- ❌ Errado:
UPDATE tenant_configs SET primary_color = 'FF6B35' WHERE tenant_id = 1;

-- ✅ Correto:
UPDATE tenant_configs SET primary_color = '#FF6B35' WHERE tenant_id = 1;
```

---

### Problema: JSON inválido em features

**Erro:** `invalid input syntax for type jsonb`

**Solução:** Certificar que é um objeto JSON válido:
```sql
-- ❌ Errado (é um array):
UPDATE tenant_configs SET features = '["export_csv", "api_access"]'::jsonb;

-- ✅ Correto (é um objeto):
UPDATE tenant_configs SET features = '{"export_csv": true, "api_access": false}'::jsonb;
```

---

### Problema: change_log crescendo infinitamente

**Solução:** O trigger mantém apenas 50 últimas mudanças. Se quiser histórico completo, migrar para tabela separada:
```sql
CREATE TABLE tenant_configs_history (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    version INTEGER,
    changed_at TIMESTAMP DEFAULT NOW(),
    changes JSONB
);
```

---

## 📌 Sumário Rápido

| Item | Descrição | Arquivo |
|------|-----------|---------|
| **Tabela Principal** | tenant_configs | 06_tenant_configs.sql |
| **Seed Data** | GeniAI Admin + AllpFit | 06_tenant_configs.sql (linhas 444-605) |
| **Funções** | 4 helpers para queries | Linhas 193-315 |
| **Triggers** | 2 triggers automáticos | Linhas 321-373 |
| **Índices** | 6 índices de performance | Linhas 173-182 |
| **Documentação** | Este arquivo | 06_tenant_configs_README.md |

---

## 📞 Suporte

Para dúvidas ou melhorias, consulte:
- Documentação PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
- Padrão de RLS: `sql/multi_tenant/05_row_level_security.sql`
- Schema completo: `sql/multi_tenant/02_create_schema.sql`

---

**Versão:** 1.0
**Última atualização:** 2025-11-06
**Status:** ✅ Pronto para produção
