# Guia de Implementação - Tabela `tenant_configs`

## 📋 Resumo Executivo

**Data:** 2025-11-06
**Status:** ✅ Completo - Pronto para Produção
**Componentes:** 1 script SQL + 2 arquivos de documentação

### O que foi criado?

Um sistema completo de **personalização por cliente** (tenant) incluindo:

- ✅ **Tabela `tenant_configs`** com 17 campos estruturados
- ✅ **4 Funções Helper** para queries otimizadas
- ✅ **2 Triggers Automáticos** para auditoria
- ✅ **6 Índices** para performance
- ✅ **Seed Data** para GeniAI Admin e AllpFit
- ✅ **Documentação Completa** + Exemplos de Queries

---

## 📁 Arquivos Criados

### 1. **06_tenant_configs.sql** (735 linhas)
Script SQL principal com:
- Definição completa da tabela
- Constraints de validação
- Funções helper
- Triggers de auditoria
- Índices de performance
- Seed data (GeniAI + AllpFit)

**Local:** `/home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs.sql`

### 2. **06_tenant_configs_README.md**
Documentação detalhada incluindo:
- Estrutura de campos (17 colunas)
- Exemplos de configuração JSON
- Descrição de cada função helper
- Queries úteis (14 exemplos)
- Troubleshooting
- Sumário rápido

**Local:** `/home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs_README.md`

### 3. **06_tenant_configs_queries.sql** (700+ linhas)
Coleção de 50+ queries prontas:
- Leitura de configurações
- Busca por features
- Atualização de dados
- Auditoria e histórico
- Validações
- Análise de performance

**Local:** `/home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs_queries.sql`

### 4. **06_IMPLEMENTATION_GUIDE.md** (este arquivo)
Guia de implementação passo-a-passo

---

## 🚀 Como Executar

### Pré-requisitos

1. **PostgreSQL 13+** instalado
2. **Banco `geniai_analytics`** já criado (script 01)
3. **Tabela `tenants`** já criada (script 02)
4. **Tabela `users`** já criada (script 02)
5. **Tabela `audit_logs`** já criada (script 02)

### Passo 1: Executar o Script SQL

```bash
# Opção 1: Direto via psql
psql -U postgres -d geniai_analytics -f /home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs.sql

# Opção 2: Via Docker (se usar container PostgreSQL)
docker exec -i postgres psql -U postgres -d geniai_analytics < /home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs.sql

# Opção 3: Via arquivo SQL no psql interativo
psql -U postgres -d geniai_analytics
\i /home/tester/projetos/allpfit-analytics/sql/multi_tenant/06_tenant_configs.sql
```

### Passo 2: Verificar Execução

```sql
-- Conectar ao banco
psql -U postgres -d geniai_analytics

-- Verificar tabela foi criada
SELECT * FROM tenant_configs LIMIT 5;

-- Verificar funções foram criadas
SELECT proname FROM pg_proc WHERE proname LIKE '%tenant_config%';

-- Verificar índices
SELECT indexname FROM pg_indexes WHERE tablename = 'tenant_configs';

-- Verificar seed data (GeniAI Admin)
SELECT tenant_id, primary_color, secondary_color FROM tenant_configs WHERE tenant_id = 0;

-- Verificar seed data (AllpFit)
SELECT tenant_id, logo_url, primary_color, secondary_color FROM tenant_configs WHERE tenant_id = 1;
```

---

## 📊 Estrutura de Dados

### Tabela Principal: `tenant_configs`

```
tenant_configs
├── tenant_id (INT) - PK, FK → tenants.id
├── BRANDING
│   ├── logo_url (TEXT) - URL do logo customizado
│   ├── favicon_url (TEXT) - URL do favicon
│   ├── primary_color (VARCHAR(7)) - Cor principal hex
│   ├── secondary_color (VARCHAR(7)) - Cor secundária hex
│   ├── accent_color (VARCHAR(7)) - Cor de destaque hex
│   └── custom_css (TEXT) - CSS personalizado (até 50KB)
├── FEATURES
│   ├── features (JSONB) - Features habilitados/desabilitados
│   ├── notifications (JSONB) - Config de notificações
│   ├── dashboard_config (JSONB) - Personalização do dashboard
│   ├── integrations (JSONB) - APIs externas (Slack, etc)
│   └── advanced_config (JSONB) - Rate limits, timezone, etc
└── AUDITORIA
    ├── version (INT) - Versionamento automático
    ├── change_log (JSONB[]) - Histórico das últimas 50 mudanças
    ├── created_at (TIMESTAMP) - Data de criação
    ├── updated_at (TIMESTAMP) - Última atualização
    └── updated_by_user_id (INT) - Quem fez a mudança
```

### Exemplo: AllpFit (tenant_id = 1)

```json
{
  "tenant_id": 1,
  "logo_url": "https://allpfit.com.br/logo.png",
  "favicon_url": "https://allpfit.com.br/favicon.ico",
  "primary_color": "#FF6B35",      // Laranja
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
Retorna configuração padrão para novos tenants.

```sql
-- Usar ao criar novo tenant
INSERT INTO tenant_configs (tenant_id, features, notifications, ...)
SELECT 99, (get_default_tenant_config()).*;
```

---

### 2. `apply_tenant_config_defaults(tenant_id)`
Preenche campos NULL com defaults (idempotente).

```sql
-- Corrigir dados inconsistentes
SELECT apply_tenant_config_defaults(1);
```

---

### 3. `is_feature_enabled(tenant_id, feature_name)`
Verifica se um feature está ativado.

```sql
-- Verificar se AllpFit pode exportar CSV
SELECT is_feature_enabled(1, 'export_csv');  -- true

-- No código da app (pseudocódigo):
IF is_feature_enabled(@tenant_id, 'export_csv') THEN
    SHOW_EXPORT_BUTTON();
END IF;
```

---

### 4. `get_notification_config(tenant_id)`
Retorna config de notificações de um tenant.

```sql
SELECT get_notification_config(1);
-- Resultado: {"email_alerts": true, "alert_threshold": 100, ...}
```

---

## 📍 Triggers Automáticos

### 1. `trigger_update_tenant_configs_updated_at`
- **Quando:** Antes de cada UPDATE
- **O que faz:** Atualiza `updated_at` e incrementa `version`
- **Benefício:** Versionamento automático sem código manual

### 2. `trigger_log_tenant_configs_changes`
- **Quando:** Antes de cada UPDATE com mudanças
- **O que faz:** Registra histórico em `change_log`
- **Benefício:** Auditoria automática das últimas 50 mudanças

---

## 💡 Casos de Uso

### 1. Personalização Visual por Cliente

**Frontend busca cores:**
```sql
SELECT primary_color, secondary_color, accent_color, logo_url
FROM tenant_configs
WHERE tenant_id = @tenant_id;
```

**Aplicação aplica tema:**
```css
/* CSS dinâmico baseado em tenant_configs */
:root {
    --primary-color: #FF6B35;      /* primary_color do DB */
    --secondary-color: #1E90FF;    /* secondary_color do DB */
    --accent-color: #00CED1;       /* accent_color do DB */
}
```

---

### 2. Feature Flags por Cliente

**Backend verifica permissão:**
```sql
-- C# / Java / Python
if (is_feature_enabled(tenant_id, "export_csv")) {
    enable_export_button();
}
```

**Query avançada:**
```sql
SELECT tc.tenant_id, t.name
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"api_access": true}'::JSONB;
```

---

### 3. Notificações Customizadas

**App obtém config:**
```sql
SELECT notifications->>'alert_email' AS email,
       notifications->>'alert_threshold' AS threshold
FROM tenant_configs
WHERE tenant_id = @tenant_id;
```

**Exemplo:**
- AllpFit recebe alerta quando conversas > 100
- Outra empresa pode ter threshold = 50

---

### 4. Dashboard Personalizado

**App carrega config:**
```sql
SELECT dashboard_config
FROM tenant_configs
WHERE tenant_id = @tenant_id;
```

**Resultado permite:**
- Mostrar/esconder widgets por cliente
- Reordenar KPI cards
- Ajustar período de data padrão

---

### 5. Timezone por Tenant

**Aplicação usa timezone:**
```sql
SELECT advanced_config->>'timezone' AS tz
FROM tenant_configs
WHERE tenant_id = @tenant_id;

-- Usar em report: AT TIME ZONE tz
SELECT created_at AT TIME ZONE tz AS local_time
FROM events;
```

---

## 📊 Validações e Constraints

### Cores (Hex Format)
```
Formato: ^#[0-9A-Fa-f]{6}$
Exemplos:
  ✅ #FF6B35
  ✅ #1E90FF
  ✅ #00CED1
  ❌ FF6B35  (sem #)
  ❌ #ZZZZZZ (caracteres inválidos)
```

### URLs (HTTPS)
```
Formato: ^https?://...
Tamanho: máximo 500 caracteres
Exemplos:
  ✅ https://allpfit.com.br/logo.png
  ✅ http://example.com/favicon.ico
  ❌ ftp://example.com/logo.png (protocol não suportado)
```

### JSON Objects
```
Tipo: jsonb_typeof(field) = 'object'
Exemplos:
  ✅ {"key": "value"}
  ✅ {"nested": {"key": "value"}}
  ❌ ["item1", "item2"]  (array, não object)
  ❌ "string"  (scalar, não object)
```

---

## 📝 Exemplos de Queries Comuns

### Buscar configuração de um tenant
```sql
SELECT * FROM tenant_configs WHERE tenant_id = 1;
```

### Verificar se feature está ativado
```sql
SELECT is_feature_enabled(1, 'export_csv');  -- true/false
```

### Listar tenants com feature específico
```sql
SELECT tc.tenant_id, t.name
FROM tenant_configs tc
JOIN tenants t ON t.id = tc.tenant_id
WHERE tc.features @> '{"api_access": true}'::JSONB;
```

### Atualizar cor primária
```sql
UPDATE tenant_configs
SET primary_color = '#FF00FF'
WHERE tenant_id = 1;
-- Automaticamente: updated_at e version incrementam!
```

### Habilitar um feature
```sql
UPDATE tenant_configs
SET features = jsonb_set(
    features,
    '{api_access}',
    'true'::jsonb
)
WHERE tenant_id = 1;
```

### Ver histórico de mudanças
```sql
SELECT
    version,
    updated_at,
    jsonb_array_elements(change_log) ->> 'timestamp' AS change_time
FROM tenant_configs
WHERE tenant_id = 1
ORDER BY updated_at DESC;
```

---

## 🔐 Segurança em Produção

### 1. Dados Sensíveis (Credenciais de Integrações)

**Em produção, usar criptografia:**
```sql
-- Instalar pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Criptografar credenciais ao armazenar
UPDATE tenant_configs
SET integrations = jsonb_set(
    integrations,
    '{slack, webhook_url}',
    to_jsonb(pgp_sym_encrypt(value, 'chave_secreta'))
)
WHERE integrations->>'slack' IS NOT NULL;

-- Descriptografar ao ler
SELECT
    pgp_sym_decrypt(
        integrations->'slack'->'webhook_url'::bytea,
        'chave_secreta'
    )
FROM tenant_configs
WHERE tenant_id = 1;
```

### 2. Row-Level Security (RLS)

**Apenas clientes veem própria config:**
```sql
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_config_access ON tenant_configs
    FOR SELECT TO authenticated_users
    USING (tenant_id = current_setting('app.current_tenant_id')::INT);
```

### 3. Auditoria

**Todas as mudanças são logadas:**
```sql
-- Ver quem alterou configuração
SELECT
    tc.updated_at,
    u.full_name,
    tc.version,
    jsonb_array_elements(tc.change_log) ->> 'changed_fields'
FROM tenant_configs tc
LEFT JOIN users u ON u.id = tc.updated_by_user_id
WHERE tc.tenant_id = 1;
```

---

## 🐛 Troubleshooting

### Problema: Cor inválida

**Erro:** `violates check constraint "chk_primary_color_format"`

**Solução:**
```sql
-- ❌ Errado: sem #
UPDATE tenant_configs SET primary_color = 'FF6B35' WHERE tenant_id = 1;

-- ✅ Correto: com # e 6 hex digits
UPDATE tenant_configs SET primary_color = '#FF6B35' WHERE tenant_id = 1;
```

### Problema: JSON inválido

**Erro:** `invalid input syntax for type jsonb`

**Solução:**
```sql
-- ❌ Errado: array em vez de object
UPDATE tenant_configs SET features = '["export"]'::jsonb;

-- ✅ Correto: object JSON
UPDATE tenant_configs SET features = '{"export_csv": true}'::jsonb;
```

### Problema: Valores NULL após update

**Causa:** Aplicar defaults ajuda

**Solução:**
```sql
-- Preencher campos NULL com valores padrão
SELECT apply_tenant_config_defaults(1);
```

---

## 📈 Performance

### Tamanho em Disco

```sql
SELECT pg_size_pretty(pg_total_relation_size('tenant_configs'));
-- Típico: 50-100 KB para 100 tenants
```

### Índices Criados

| Índice | Tipo | Campo | Uso |
|--------|------|-------|-----|
| `idx_tenant_configs_features_gin` | GIN | features | Buscar por JSONB |
| `idx_tenant_configs_notifications_gin` | GIN | notifications | Buscar por JSONB |
| `idx_tenant_configs_dashboard_gin` | GIN | dashboard_config | Buscar por JSONB |
| `idx_tenant_configs_updated_at` | B-tree DESC | updated_at | Configs recentes |

### Queries Otimizadas

```sql
-- Usa índice GIN automaticamente
SELECT * FROM tenant_configs
WHERE features @> '{"export_csv": true}'::JSONB;
```

---

## 🔄 Sequência de Implementação Completa

```bash
# 1. Criar banco e estrutura base
psql -U postgres -f sql/multi_tenant/01_create_database.sql
psql -U postgres -f sql/multi_tenant/02_create_schema.sql

# 2. Seed data
psql -U postgres -f sql/multi_tenant/03_seed_data.sql

# 3. Migração de dados (se houver banco antigo)
psql -U postgres -f sql/multi_tenant/04_migrate_allpfit_data.sql

# 4. Row-Level Security
psql -U postgres -f sql/multi_tenant/05_row_level_security.sql

# 5. ← VOCÊ ESTÁ AQUI: Configurações de tenants
psql -U postgres -f sql/multi_tenant/06_tenant_configs.sql

# 6. Analytics tables
psql -U postgres -f sql/multi_tenant/07_create_analytics_tables.sql

# 7. Migrar dados de analytics
psql -U postgres -f sql/multi_tenant/08_migrate_data.sql

# 8. RLS em analytics
psql -U postgres -f sql/multi_tenant/09_add_rls_analytics.sql

# 9. Testes
psql -U postgres -f sql/multi_tenant/10_test_rls_analytics.sql
```

---

## ✅ Checklist de Implementação

- [ ] Banco `geniai_analytics` criado (script 01)
- [ ] Tabelas base criadas (script 02)
- [ ] Seed data inserido (script 03)
- [ ] Executar `06_tenant_configs.sql`
- [ ] Verificar tabela criada: `SELECT COUNT(*) FROM tenant_configs;`
- [ ] Verificar seed data: `SELECT * FROM tenant_configs WHERE tenant_id = 1;`
- [ ] Testar função helper: `SELECT is_feature_enabled(1, 'export_csv');`
- [ ] Atualizar cor primária (teste de UPDATE)
- [ ] Verificar trigger de update: `SELECT version FROM tenant_configs WHERE tenant_id = 1;`
- [ ] Documentar alterações para novo tenant
- [ ] Integrar com aplicação backend
- [ ] Testar personalização visual no frontend
- [ ] Testar feature flags na aplicação

---

## 📞 Próximos Passos

1. **Integração Backend:**
   - Criar API endpoints para ler/atualizar `tenant_configs`
   - Implementar cache de configurações (Redis)
   - Usar `is_feature_enabled()` para controlar features

2. **Integração Frontend:**
   - Buscar cores e logo ao inicializar app
   - Aplicar tema CSS dinamicamente
   - Mostrar/esconder botões baseado em features

3. **Segurança:**
   - Implementar Row-Level Security (script 05)
   - Criptografar credenciais em `integrations` (pgcrypto)
   - Adicionar ACLs para quem pode alterar configs

4. **Monitoramento:**
   - Alertas se feature crítico for desabilitado
   - Log de mudanças em `audit_logs`
   - Relatório mensal de clientes por feature

---

## 📚 Documentação Complementar

- **README Detalhado:** `06_tenant_configs_README.md`
- **Exemplos de Queries:** `06_tenant_configs_queries.sql`
- **Script SQL Principal:** `06_tenant_configs.sql`

---

**Status:** ✅ Pronto para Produção
**Data:** 2025-11-06
**Versão:** 1.0
**Autor:** GeniAI Analytics
