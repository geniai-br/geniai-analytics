# 🤖 PROMPT PARA NOVO CHAT - IMPLEMENTAÇÃO FASE 4

> **Use este prompt para iniciar um novo chat e implementar a Fase 4 (Dashboard Cliente)**
> **Última atualização:** 2025-11-06 (pós-conclusão Fase 3)
> **Status:** Fase 3 COMPLETA E VALIDADA - Pronto para iniciar Fase 4

---

## ⚠️ PERMISSÕES E ESCOPO

**IMPORTANTE - LEIA ANTES DE COMEÇAR:**

✅ **VOCÊ TEM ACESSO TOTAL A:**
- Leitura de TODOS os arquivos do sistema
- Navegação em TODAS as pastas
- Consulta a QUALQUER documentação

❌ **VOCÊ SÓ PODE FAZER MUDANÇAS EM:**
- `/home/tester/projetos/allpfit-analytics/` (nosso projeto)

🚫 **NÃO FAÇA MUDANÇAS EM:**
- Outros projetos/diretórios fora de `allpfit-analytics`
- Arquivos de sistema
- Configurações globais do servidor

---

## 📋 PROMPT PARA COPIAR E COLAR

```
Olá! Preciso implementar a FASE 4 (Dashboard Cliente) do sistema GeniAI Analytics.

CONTEXTO RÁPIDO:
- Projeto: Sistema multi-tenant SaaS com autenticação e ETL automatizado
- Fase 1: ✅ COMPLETA (banco geniai_analytics, RLS, migração de dados)
- Fase 2: ✅ COMPLETA (autenticação, login, dashboards básicos)
- Fase 3: ✅ COMPLETA (ETL multi-tenant, 1.093 conversas carregadas)
- Próximo: FASE 4 - Dashboard Cliente Avançado

SITUAÇÃO ATUAL:
As Fases 1, 2 e 3 estão COMPLETAS e FUNCIONANDO:

✅ Fase 1 - Banco de Dados:
  - geniai_analytics criado (9 tabelas com RLS)
  - 2 tenants: GeniAI Admin (id=0) + AllpFit (id=1)
  - 4 usuários cadastrados
  - RLS funcionando corretamente

✅ Fase 2 - Autenticação:
  - Login funcionando (http://localhost:8504)
  - Autenticação bcrypt + sessões persistidas
  - Router inteligente (admin → painel, cliente → dashboard)
  - Performance otimizada (cache 5min)
  - Duração real: ~9h

✅ Fase 3 - ETL Multi-Tenant:
  - Pipeline completo: Extractor → Transformer → Loader
  - Watermark incremental por tenant
  - Advisory locks (evita concorrência)
  - 1.093 conversas do AllpFit carregadas
  - 5 inboxes mapeados (IDs: 1, 2, 61, 64, 67)
  - Usuário johan_geniai (owner, sem RLS)
  - Duração real: ~8h
  - Dashboard mostrando dados reais!

LIÇÕES APRENDIDAS (Fases 1-3):
1. ✅ RLS em tabelas de controle bloqueia sistema → Desabilitar em sessions, etl_control
2. ✅ Verificar schema antes de assumir colunas → view remota tem 95 colunas
3. ✅ Owner bypass RLS → johan_geniai para ETL, isaac para dashboard
4. ✅ Chunked processing → Evita memory errors (default 50 rows)
5. ✅ Logging profissional desde o início → Economiza refactoring
6. ✅ Cache é essencial → TTL 5min melhora 94%
7. ✅ Documentação completa → REMOTE_DATABASE.md salvou tempo

DOCUMENTAÇÃO ESSENCIAL:
Por favor, leia estes arquivos para entender o projeto:

1. 📚 docs/multi-tenant/00_CRONOGRAMA_MASTER.md
   → Cronograma completo (3 fases completas, Fase 4 detalhada)

2. 🗄️ docs/multi-tenant/DB_DOCUMENTATION.md
   → Banco de dados, credenciais, tabelas, RLS

3. 🚀 docs/multi-tenant/FASE3_ETL_MULTI_TENANT.md
   → Arquitetura completa do ETL implementado

4. 🌐 docs/multi-tenant/REMOTE_DATABASE.md
   → Schema do banco remoto Chatwoot (95 colunas documentadas)

5. 👥 docs/multi-tenant/README_USUARIOS.md
   → Guia de usuários do banco (johan_geniai vs isaac)

TAREFAS PARA ESTE CHAT (FASE 4):

A Fase 4 foca em melhorar o dashboard do CLIENTE (não o admin).
Objetivos conforme cronograma:
- Adaptar dashboard atual para multi-tenant
- Filtrar dados automaticamente pelo tenant logado
- Personalização por cliente (logo, cores, nome)
- Métricas específicas do cliente

IMPLEMENTAÇÕES SUGERIDAS:

1. 🎨 Personalização Visual
   - Tabela tenant_configs (logo_url, primary_color, secondary_color)
   - Aplicar branding dinâmico por tenant
   - Header personalizado com logo do cliente

2. 📊 Métricas Avançadas
   - Atualmente: Placeholders (is_lead, visit_scheduled, crm_converted = FALSE)
   - Implementar análise de texto para detectar leads
   - Keywords para classificar visitas agendadas
   - Detecção de conversões CRM

3. 📈 Visualizações Aprimoradas
   - Gráficos mais complexos (tendências, comparativos)
   - Filtros avançados (período, inbox, status)
   - Exportação de dados (CSV, Excel)

4. ⚡ Performance
   - Otimizar queries (já existe cache de 5min)
   - Índices adicionais se necessário
   - Lazy loading para tabelas grandes

ARQUIVOS JÁ IMPLEMENTADOS:

✅ Fase 1 (Banco):
  - sql/multi_tenant/*.sql (9 tabelas)

✅ Fase 2 (Auth):
  - src/multi_tenant/auth/ (auth.py, middleware.py)
  - src/multi_tenant/dashboards/ (login_page.py, admin_panel.py, client_dashboard.py, app.py)

✅ Fase 3 (ETL):
  - src/multi_tenant/etl_v4/extractor.py (350+ linhas)
  - src/multi_tenant/etl_v4/transformer.py (400+ linhas)
  - src/multi_tenant/etl_v4/loader.py (369 linhas)
  - src/multi_tenant/etl_v4/watermark_manager.py (483 linhas)
  - src/multi_tenant/etl_v4/pipeline.py (481 linhas)

DASHBOARD ATUAL (Porta 8504):
O dashboard cliente JÁ EXISTE mas tem placeholders:
- Localização: src/multi_tenant/dashboards/client_dashboard.py
- Mostra 773 contatos (últimos 30 dias de 1.093 total)
- Métricas em 0: leads, visitas agendadas, conversões (placeholders Fase 3)
- Próximo passo: Implementar lógica real para essas métricas

CREDENCIAIS DO BANCO LOCAL:
- Host: localhost
- Database: geniai_analytics
- User ETL: johan_geniai (owner, sem RLS)
- Password: vlVMVM6UNz2yYSBlzodPjQvZh
- User Dashboard: isaac (com RLS)
- Password: AllpFit2024@Analytics

CREDENCIAIS DO BANCO REMOTO (Chatwoot):
- Host: 178.156.206.184:5432
- Database: chatwoot
- User: hetzner_hyago_read
- Password: c1d46b41391f
- View: vw_conversations_analytics_final (95 colunas)

USUÁRIOS DE TESTE (senha: senha123):
- admin@geniai.com.br (super_admin, tenant_id=0)
- isaac@allpfit.com.br (admin, tenant_id=1)
- visualizador@allpfit.com.br (client, tenant_id=1)

APLICAÇÃO:
- URL Multi-Tenant: http://localhost:8504 ✅ FUNCIONANDO
- Dashboard Single-Tenant: http://localhost:8503 (NÃO MEXER - referência)

DADOS DISPONÍVEIS (Tenant ID=1: AllpFit):
- Total conversas: 1.093
- Período: 25/Set/2025 - 06/Nov/2025
- Últimos 30 dias: 773 conversas
- 5 inboxes: allpfitjpsulcloud1, allpfitjpsulrecepcao, allpfitjpsulcloud2, AllpFit WhatsApp, Telegram

CLIENTES FUTUROS (Fase 5):
Existem 6 clientes adicionais no Chatwoot para adicionar:
- CDT Mossoró (592 conversas)
- CDT JP Sul (262 conversas)
- CDT Viamao (247 conversas)
- Gestao GeniAI (14 conversas)
- InvestBem (11 conversas)
- CDT Tubarão SC (2 conversas)
→ Serão adicionados via interface admin na Fase 5

IMPORTANTE - ESCOPO:
⚠️ Você tem acesso total a TUDO, mas SÓ FAÇA MUDANÇAS em:
   /home/tester/projetos/allpfit-analytics/

Pronto para implementar a Fase 4 (Dashboard Cliente)?
```

---

## 🎯 O QUE O PRÓXIMO AGENTE VAI FAZER

O agente deve implementar a **Fase 4 - Dashboard Cliente Avançado** seguindo este fluxo:

### Opção A: Melhorias Incrementais (Recomendado)
1. **Criar Tabela de Configurações** (2-3h)
   - `tenant_configs` (logo, cores, CSS customizado)
   - Aplicar branding dinâmico
   - Testar com AllpFit

2. **Implementar Análise de IA** (4-6h)
   - Detectar leads via keywords no texto
   - Classificar visitas agendadas
   - Detectar conversões CRM
   - Substituir placeholders FALSE por lógica real

3. **Melhorar Visualizações** (3-4h)
   - Gráficos de tendências
   - Filtros avançados
   - Exportação CSV/Excel

4. **Testes de Isolamento** (1-2h)
   - Validar RLS funciona
   - Múltiplos usuários do mesmo tenant
   - Performance com dados reais

### Opção B: Foco em IA (Alternativo)
1. **Análise de Texto com IA** (6-8h)
   - Implementar NLP para detectar leads
   - Classificação de intenções
   - Score de qualificação

2. **Dashboard de Insights** (4-6h)
   - Palavras-chave mais comuns
   - Análise de sentimento
   - Recomendações automáticas

---

## 📊 STATUS ATUAL DO PROJETO

### ✅ Fase 1: Banco de Dados (COMPLETA)
- 9 tabelas criadas com RLS
- 2 tenants (GeniAI Admin + AllpFit)
- 4 usuários cadastrados
- Índices otimizados

### ✅ Fase 2: Autenticação (COMPLETA)
- Login funcionando
- Router inteligente
- Cache 5min (94% mais rápido)
- Código limpo
- Duração: ~9h (62% mais rápido)

### ✅ Fase 3: ETL Multi-Tenant (COMPLETA)
- Pipeline completo (Extract → Transform → Load)
- Watermark incremental
- Advisory locks
- 1.093 conversas carregadas
- 5 inboxes mapeados
- Documentação completa
- Duração: ~8h (75% mais rápido)

### 🔄 Fase 4: Dashboard Cliente (ATUAL - A IMPLEMENTAR)
- **Estimativa:** 2-3 dias (16-24h)
- **Complexidade:** 🟡 Média
- **Status:** Pronto para iniciar
- **Dashboard atual:** Funcional mas com placeholders

---

## 🎓 LIÇÕES APRENDIDAS (FASES 1-3) - APLICAR NA FASE 4

### 1. Verificar Schema Antes de Assumir ⭐
- ✅ Fase 3: view remota tinha nomes diferentes (t_messages vs total_messages)
- ✅ Sempre consultar `\d table_name` ou `INFORMATION_SCHEMA`

### 2. RLS em Tabelas Corretas ⭐
- ✅ Dados: RLS habilitado (conversations_analytics, users, tenants)
- ❌ Controle: RLS desabilitado (sessions, etl_control, inbox_tenant_mapping)

### 3. Separação de Usuários ⭐
- ✅ johan_geniai (owner): ETL sem RLS
- ✅ isaac (authenticated_users): Dashboard com RLS

### 4. Performance é Crítica ⭐
- ✅ Cache TTL 5min → 94% mais rápido
- ✅ Índices em colunas filtradas (tenant_id, conversation_date)
- ✅ Chunked processing (evita memory error)

### 5. Logging Profissional ⭐
- ✅ Não usar `print()` para debug
- ✅ Usar `import logging` desde o início
- ✅ Níveis: INFO, WARNING, ERROR

---

## 📂 ESTRUTURA DE ARQUIVOS (Fases 1-3 Completas, Fase 4 a Implementar)

```
/home/tester/projetos/allpfit-analytics/
├── docs/multi-tenant/
│   ├── 00_CRONOGRAMA_MASTER.md          ✅ Fase 3 completa
│   ├── DB_DOCUMENTATION.md              ✅ Banco documentado
│   ├── FASE2_MELHORIAS.md               ✅ Melhorias Fase 2
│   ├── FASE3_ETL_MULTI_TENANT.md        ✅ Arquitetura ETL
│   ├── REMOTE_DATABASE.md               ✅ 95 colunas documentadas
│   ├── README_USUARIOS.md               ✅ Guia de usuários
│   └── PROMPT_NOVO_CHAT.md              ✅ Este arquivo
│
├── src/multi_tenant/
│   ├── auth/                            ✅ Fase 2 (completa)
│   │   ├── auth.py
│   │   └── middleware.py
│   │
│   ├── dashboards/                      ✅ Fase 2 (básico)
│   │   ├── login_page.py                    ⚠️ Fase 4: melhorar
│   │   ├── admin_panel.py                   ⚠️ Fase 5: expandir
│   │   ├── client_dashboard.py              🔄 Fase 4: IMPLEMENTAR
│   │   └── app.py
│   │
│   └── etl_v4/                          ✅ Fase 3 (completa)
│       ├── extractor.py
│       ├── transformer.py
│       ├── loader.py
│       ├── watermark_manager.py
│       └── pipeline.py
│
├── sql/multi_tenant/
│   ├── tenant_configs.sql               [ ] Fase 4: criar tabela
│   └── ... (9 tabelas existentes)
│
└── scripts/
    ├── restart_multi_tenant.sh          ✅ Deploy app
    └── run_etl.sh                       ✅ ETL manual
```

---

## 🚨 PONTOS DE ATENÇÃO (FASE 4)

### 1. Dashboard Já Existe
- ⚠️ NÃO reescrever do zero
- ✅ Melhorar incrementalmente
- ✅ Manter compatibilidade com Fase 2

### 2. Placeholders vs Dados Reais
Atualmente o dashboard tem:
```python
# client_dashboard.py (linha ~61)
FALSE as is_lead,          # Placeholder Fase 3
FALSE as visit_scheduled,  # Placeholder Fase 3
FALSE as crm_converted     # Placeholder Fase 3
```

**Fase 4 deve substituir por:**
- Análise de texto real (keywords, regex)
- Lógica de negócio do AllpFit
- Configurável por tenant

### 3. Performance com Dados Reais
- ✅ Cache já existe (5min TTL)
- ⚠️ 1.093 conversas → queries podem ficar lentas
- ✅ Adicionar índices se necessário
- ✅ Lazy loading em tabelas

### 4. Multi-Tenant Awareness
- ✅ RLS já funciona
- ⚠️ Personalização deve ser por tenant
- ✅ Usar `tenant_configs` para branding

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO (FASE 4)

### Dia 1: Personalização (4-6h)
- [ ] Criar tabela `tenant_configs`
- [ ] Adicionar seed data para AllpFit
- [ ] Implementar função `apply_tenant_branding()`
- [ ] Testar branding dinâmico
- [ ] Atualizar client_dashboard.py

### Dia 2: Análise de IA (6-8h)
- [ ] Implementar detecção de leads (keywords)
- [ ] Implementar classificação de visitas
- [ ] Implementar detecção de conversões CRM
- [ ] Substituir placeholders por lógica real
- [ ] Adicionar coluna calculada no transformer?

### Dia 3: Visualizações e Testes (4-6h)
- [ ] Melhorar gráficos (tendências, comparativos)
- [ ] Adicionar filtros avançados
- [ ] Implementar exportação CSV/Excel
- [ ] Testes de isolamento (RLS)
- [ ] Testes de performance
- [ ] Documentar Fase 4

---

## 🎯 CRITÉRIOS DE SUCESSO (FASE 4)

A Fase 4 estará completa quando:

1. ✅ Dashboard mostra métricas REAIS (não mais placeholders)
2. ✅ Branding personalizado por tenant funcionando
3. ✅ Análise de IA detecta leads/visitas/conversões
4. ✅ Filtros avançados implementados
5. ✅ Exportação de dados funcionando
6. ✅ Performance aceitável (< 3s para carregar dashboard)
7. ✅ RLS continua funcionando
8. ✅ Documentação atualizada

---

## 🚀 PRÓXIMAS FASES (Pós-Fase 4)

### Fase 5: Dashboard Admin Completo
- Gerenciamento de clientes (CRUD)
- Adicionar 6 clientes do Chatwoot
- Métricas agregadas
- Auditoria de ações

### Fase 6: Testes e Deploy
- Testes de segurança
- Deploy em staging/produção
- Monitoramento (Grafana)

---

## 🔗 LINKS RÁPIDOS

- **Aplicação:** http://localhost:8504
- **Banco:** `PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -h localhost -d geniai_analytics`
- **Restart:** `./scripts/restart_multi_tenant.sh`
- **ETL Manual:** `python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1`

---

**Última atualização:** 2025-11-06 (pós-conclusão Fase 3)
**Criado por:** Isaac (via Claude Code)
**Status:** ✅ Fase 3 COMPLETA - Pronto para Fase 4

---

**BOA SORTE COM A FASE 4! 🚀**
