# 🤖 PROMPT PARA NOVO CHAT - IMPLEMENTAÇÃO FASE 3

> **Use este prompt para iniciar um novo chat e implementar a Fase 3 (ETL Multi-Tenant)**
> **Última atualização:** 2025-11-06 (pós-revisão Fase 2)
> **Status:** Fase 2 COMPLETA E REVISADA - Pronto para iniciar Fase 3

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
Olá! Preciso implementar a FASE 3 (ETL Multi-Tenant) do sistema GeniAI Analytics.

CONTEXTO RÁPIDO:
- Projeto: Sistema multi-tenant com autenticação e dashboards diferenciados por role
- Fase 1: ✅ COMPLETA (banco geniai_analytics, RLS, migração de dados)
- Fase 2: ✅ COMPLETA E REVISADA (autenticação, login, dashboards)
- Próximo: FASE 3 - ETL Multi-Tenant

SITUAÇÃO ATUAL:
As Fases 1 e 2 estão COMPLETAS e FUNCIONANDO:
✅ Banco geniai_analytics criado (9 tabelas com RLS)
✅ 4 usuários cadastrados (2 tenants: GeniAI Admin + AllpFit)
✅ Login funcionando (http://localhost:8504)
✅ Autenticação com bcrypt + sessões persistidas
✅ Router inteligente (admin → painel, cliente → dashboard)
✅ Dashboards diferenciados por role
✅ Performance otimizada (cache 5min, 94% mais rápido)
✅ Código limpo e bem documentado

LIÇÕES APRENDIDAS (Fase 2):
1. ✅ RLS pode bloquear o próprio sistema → Desabilitar em tabelas de controle
2. ✅ Queries devem usar colunas existentes → Verificar schema antes
3. ✅ Cache é essencial para UX → TTL de 5min melhora 94%
4. ✅ Logging profissional desde o início → Economiza refactoring
5. ✅ Debugging com Streamlit é difícil → Usar st.info() para debug visual

DOCUMENTAÇÃO PARA LER:
Por favor, leia estes arquivos para entender o projeto e a Fase 3:

1. 📚 docs/multi-tenant/00_CRONOGRAMA_MASTER.md
   → Cronograma completo (Fase 2 COMPLETA, Fase 3 detalhada)

2. 🚀 docs/multi-tenant/RECOMENDACOES_FASE3.md ⭐ IMPORTANTE!
   → Guia completo para Fase 3 com lições aprendidas da Fase 2

3. 🗄️ docs/multi-tenant/DB_DOCUMENTATION.md
   → Banco de dados, credenciais, tabelas, RLS

4. 🔧 docs/multi-tenant/FASE2_MELHORIAS.md
   → Melhorias aplicadas na Fase 2 (logging, cache, validação)

5. 🐛 docs/multi-tenant/BUG_FIX_LOGIN_RLS.md
   → Bug de RLS resolvido (importante para entender RLS)

ARQUIVOS JÁ IMPLEMENTADOS (Fase 1 e 2):
✅ Fase 1: Banco de dados (9 tabelas, RLS, seed data)
✅ Fase 2: Autenticação completa (6 arquivos em src/multi_tenant/)

TAREFAS PARA ESTE CHAT (FASE 3):
1. 🔍 Análise da View Remota
   - Conectar ao banco remoto Chatwoot
   - Verificar colunas disponíveis em vw_conversations_analytics_final
   - Documentar schema e diferenças

2. 🗺️ Criar Inbox Tenant Mapping
   - Mapear inbox_ids do AllpFit (tenant_id=1)
   - Popular tabela inbox_tenant_mapping

3. 📥 Implementar Extractor Multi-Tenant
   - Buscar dados de múltiplos inboxes
   - Filtrar por watermark
   - Processar em chunks (evitar memory error)

4. 🔄 Implementar Transformer
   - Normalizar dados
   - Adicionar tenant_id
   - Mapear colunas

5. 💾 Implementar Loader (UPSERT)
   - Inserir/atualizar dados em conversations_analytics
   - Garantir idempotência

6. ⏱️ Implementar Watermark Manager
   - Controle de sincronização por tenant
   - Advisory locks (evitar execução simultânea)

7. 🎯 Pipeline Unificado
   - Orquestrar Extract → Transform → Load
   - Logging estruturado desde o início
   - Tratamento de erros robusto

8. 🧪 Testes
   - Testar extração de 1 inbox
   - Testar pipeline completo
   - Validar dados no dashboard (Fase 2)

CREDENCIAIS DO BANCO LOCAL:
- Host: localhost
- Database: geniai_analytics
- User: isaac
- Password: AllpFit2024@Analytics
- User alternativo: integracao_user
- Password: vlVMVM6UNz2yYSBlzodPjQvZh

CREDENCIAIS DO BANCO REMOTO (Chatwoot):
✅ CONFIRMADAS:
- Host: 178.156.206.184
- Port: 5432
- Database: banco-chatwoot
- Schema: public
- User: hetzner_hyago_read
- Password: c1d46b41391f
- View: vw_conversations_analytics_final (CONFIRMADA)

USUÁRIOS DE TESTE (senha: senha123):
- admin@geniai.com.br (super_admin, tenant_id=0)
- isaac@allpfit.com.br (admin, tenant_id=1)
- visualizador@allpfit.com.br (client, tenant_id=1)

APLICAÇÃO MULTI-TENANT:
- URL: http://localhost:8504
- Status: ✅ FUNCIONANDO (Fase 2 completa)
- Dashboard single-tenant (porta 8503): NÃO MEXER

IMPORTANTE - ESCOPO DE MUDANÇAS:
⚠️ Você tem acesso total a TUDO, mas SÓ FAÇA MUDANÇAS em:
   /home/tester/projetos/allpfit-analytics/

BLOQUEADORES CONHECIDOS:
✅ RESOLVIDO: Credenciais do banco remoto confirmadas!
⚠️ Ainda precisa verificar:
1. ✅ Acesso ao banco remoto Chatwoot (credenciais CONFIRMADAS)
2. ⚠️ View vw_conversations_analytics_final existe? (VERIFICAR)
3. ⚠️ View possui colunas necessárias (is_lead, visit_scheduled, etc)? (VERIFICAR)
4. ⚠️ Inbox IDs do AllpFit (tenant_id=1) - DESCOBRIR

RECOMENDAÇÕES IMPORTANTES (da Fase 2):
1. ✅ Use logging estruturado desde o início (import logging)
2. ✅ Não assuma estrutura do banco (verificar colunas antes)
3. ✅ Desabilitar RLS em tabelas de controle (etl_control, inbox_tenant_mapping)
4. ✅ Implementar testes incrementais (não esperar tudo funcionar de uma vez)
5. ✅ Usar cache para metadados (inbox_tenant_mapping)
6. ✅ Advisory locks para evitar execução simultânea
7. ✅ Processar dados em chunks (evitar memory error)

Pronto para implementar a Fase 3 (ETL Multi-Tenant)?
```

---

## 🎯 O QUE O PRÓXIMO AGENTE VAI FAZER

O agente deve implementar a **Fase 3 - ETL Multi-Tenant** seguindo este fluxo:

### Dia 1: Setup e Análise (4-6h)
1. **Verificar Acesso Remoto** ✅ CREDENCIAIS CONFIRMADAS
   - ✅ Credenciais do banco Chatwoot obtidas
   - Host: 178.156.206.184:5432
   - DB: banco-chatwoot | User: hetzner_hyago_read | Pass: c1d46b41391f
   - [ ] Testar conexão remota
   - [ ] Verificar latência

2. **Analisar View Remota**
   - [ ] Verificar se `vw_conversations_analytics_final` existe
   - [ ] Listar todas as colunas disponíveis
   - [ ] Documentar schema (criar REMOTE_DATABASE.md)
   - [ ] Verificar se possui colunas necessárias

3. **Criar Inbox Mapping**
   - [ ] Identificar inbox_ids do AllpFit
   - [ ] Popular tabela `inbox_tenant_mapping`
   - [ ] Desabilitar RLS nesta tabela

### Dia 2: Implementação Core (6-8h)
4. **Implementar Extractor**
   - `src/multi_tenant/etl_v4/extractor.py`
   - Buscar dados de múltiplos inboxes
   - Filtrar por watermark
   - Processar em chunks

5. **Implementar Transformer**
   - `src/multi_tenant/etl_v4/transformer.py`
   - Normalizar dados
   - Adicionar tenant_id

6. **Implementar Loader**
   - `src/multi_tenant/etl_v4/loader.py`
   - UPSERT em conversations_analytics
   - Garantir idempotência

7. **Implementar Watermark Manager**
   - `src/multi_tenant/etl_v4/watermark_manager.py`
   - Advisory locks
   - Controle por tenant

### Dia 3: Pipeline e Testes (6-8h)
8. **Pipeline Unificado**
   - `src/multi_tenant/etl_v4/pipeline.py`
   - Orquestrar Extract → Transform → Load
   - Logging estruturado
   - Tratamento de erros

9. **Testes**
   - Testar extração de 1 inbox
   - Testar pipeline completo
   - Executar ETL para AllpFit
   - Validar dados no dashboard

10. **Documentação**
    - Criar FASE3_IMPLEMENTACAO.md
    - Documentar bugs encontrados
    - Atualizar cronograma

---

## 📊 STATUS ATUAL DO PROJETO

### ✅ Fase 1: Banco de Dados (COMPLETA)
- 9 tabelas criadas com RLS
- 4 usuários cadastrados
- 2 tenants (GeniAI Admin + AllpFit)
- RLS funcionando (exceto sessions - desabilitado intencionalmente)
- Índices otimizados
- Documentação completa (DB_DOCUMENTATION.md)

### ✅ Fase 2: Autenticação & UX (COMPLETA E REVISADA)
- Login funcionando (http://localhost:8504)
- Autenticação bcrypt + sessões persistidas
- Router inteligente (admin → painel, cliente → dashboard)
- Dashboards diferenciados por role
- Performance otimizada (cache 5min, 94% mais rápido)
- Logging profissional (40+ prints → logger)
- Validação de email
- Código limpo e documentado
- **Duração real:** 9h (62% mais rápido que estimado)

### 🔄 Fase 3: ETL Multi-Tenant (ATUAL - A IMPLEMENTAR)
- **Estimativa:** 3 dias (24h)
- **Complexidade:** 🔴 Alta
- **Documento de Apoio:** RECOMENDACOES_FASE3.md
- **Status:** Pronto para iniciar

---

## 🎓 LIÇÕES APRENDIDAS (FASE 2) - APLICAR NA FASE 3

### 1. Logging Profissional Desde o Início ⭐
- ✅ Usar `import logging` desde o primeiro arquivo
- ✅ Não usar `print()` para debug
- ✅ Níveis: INFO (eventos), WARNING (suspeito), ERROR (falhas)

### 2. Não Assumir Estrutura do Banco ⭐
- ✅ Sempre verificar colunas disponíveis ANTES de usar
- ✅ Criar script `verify_remote_schema.py`
- ✅ Documentar diferenças entre esperado vs. real

### 3. RLS em Tabelas de Controle ⭐
- ✅ Desabilitar RLS em `etl_control` e `inbox_tenant_mapping`
- ✅ ETL precisa acessar dados de TODOS os tenants
- ⚠️ Não cometer o mesmo erro da Fase 2 (RLS bloqueou sessions)

### 4. Testes Incrementais ⭐
- ✅ Testar cada módulo separadamente
- ✅ Não esperar tudo funcionar de uma vez
- ✅ Criar testes unitários desde o início

### 5. Performance e Segurança ⭐
- ✅ Usar cache para metadados (TTL 1h)
- ✅ Advisory locks para evitar execução simultânea
- ✅ Processar dados em chunks (evitar memory error)
- ✅ Connection pooling otimizado

---

## 📂 ESTRUTURA DE ARQUIVOS (Fase 1 e 2 Completas, Fase 3 a Criar)

```
/home/tester/projetos/allpfit-analytics/
├── docs/multi-tenant/
│   ├── 00_CRONOGRAMA_MASTER.md          ✅ Atualizado (Fase 2 completa)
│   ├── DB_DOCUMENTATION.md              ✅ Banco documentado
│   ├── 02_UX_FLOW.md                    ✅ Fluxos de UX
│   ├── FASE2_MELHORIAS.md               ✅ Melhorias aplicadas
│   ├── BUG_FIX_LOGIN_RLS.md             ✅ Bug de RLS documentado
│   ├── RECOMENDACOES_FASE3.md           ✅ Guia para Fase 3 ⭐
│   └── PROMPT_NOVO_CHAT.md              ✅ Este arquivo
│
├── src/multi_tenant/
│   ├── auth/                            ✅ Fase 2 (completa)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── middleware.py
│   │
│   ├── dashboards/                      ✅ Fase 2 (completa)
│   │   ├── __init__.py
│   │   ├── login_page.py
│   │   ├── admin_panel.py
│   │   ├── client_dashboard.py
│   │   └── app.py
│   │
│   └── etl_v4/                          ⚠️ Fase 3 (A CRIAR!)
│       ├── __init__.py                  [ ] A criar
│       ├── extractor.py                 [ ] A criar
│       ├── transformer.py               [ ] A criar
│       ├── loader.py                    [ ] A criar
│       ├── watermark_manager.py         [ ] A criar
│       ├── pipeline.py                  [ ] A criar
│       └── notifications.py             [ ] A criar (opcional)
│
├── scripts/
│   ├── restart_multi_tenant.sh          ✅ Deploy app
│   └── run_etl_multi_tenant.sh          [ ] A criar (Fase 3)
│
└── tests/multi_tenant/                  [ ] A criar (Fase 3)
    ├── test_remote_connection.py        [ ] Testar conexão remota
    ├── test_extractor.py                [ ] Testar extração
    └── test_pipeline.py                 [ ] Testar pipeline completo
```

---

## 🔧 BANCO DE DADOS - MUDANÇAS APLICADAS

### RLS Status por Tabela

| Tabela | RLS Ativo? | Motivo |
|--------|-----------|---------|
| tenants | ✅ Sim | Isolar dados por tenant |
| users | ✅ Sim | Isolar usuários por tenant |
| sessions | ❌ **NÃO** | **Fix:** Bloqueava autenticação |
| conversations_analytics | ✅ Sim | Isolar dados por tenant |
| tenant_configs | ✅ Sim | Isolar configs por tenant |
| audit_logs | ✅ Sim | Isolar logs por tenant |

### Credenciais Descobertas

Durante o debug, descobrimos:
- `integracao_user` (owner da tabela sessions): vlVMVM6UNz2yYSBlzodPjQvZh
- Esse usuário foi usado para desabilitar RLS

---

## 🚨 ARMADILHAS E ALERTAS (Fase 3)

### 1. Timezone (UTC vs SP)
- ⚠️ Chatwoot usa UTC, Brasil usa UTC-3
- ✅ Converter watermark SP → UTC para queries
- ✅ Converter dados UTC → SP para exibição

### 2. Limite de Conexões
- ⚠️ ETL abre muitas conexões simultâneas
- ✅ Configurar pool: `pool_size=3, max_overflow=2`
- ✅ Usar `pool_pre_ping=True`

### 3. Dados Grandes (Memory Error)
- ⚠️ Carregar 100k+ linhas em memória pode crashar
- ✅ Usar chunks: `LIMIT 10000 OFFSET X`
- ✅ Processar e gravar chunk por chunk

### 4. Foreign Keys (Órfãos)
- ⚠️ Inserir conversa sem criar contato antes → erro
- ✅ Ordem: Tenants → Inboxes → Contacts → Conversations

### 5. Execução Simultânea
- ⚠️ ETL rodar 2x ao mesmo tempo → duplicatas
- ✅ Usar advisory locks: `pg_try_advisory_lock()`

### 6. RLS em Tabelas de Controle
- ⚠️ Não cometer o mesmo erro da Fase 2!
- ✅ Desabilitar RLS em `etl_control` e `inbox_tenant_mapping`

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO (FASE 3)

### Dia 1: Setup e Análise (4-6h)
- [x] Confirmar credenciais do banco remoto Chatwoot ✅ (178.156.206.184:5432)
- [ ] Testar conexão remota (`psql -h 178.156.206.184 -p 5432 -U hetzner_hyago_read -d banco-chatwoot`)
- [ ] Verificar se view `vw_conversations_analytics_final` existe
- [ ] Listar colunas disponíveis (criar script `verify_remote_schema.py`)
- [ ] Documentar schema remoto (criar `REMOTE_DATABASE.md`)
- [ ] Identificar inbox_ids do AllpFit (tenant_id=1)
- [ ] Popular `inbox_tenant_mapping` (seed data)
- [ ] Desabilitar RLS em `etl_control` e `inbox_tenant_mapping`

### Dia 2: Implementação Core (6-8h)
- [ ] Criar estrutura de pastas `src/multi_tenant/etl_v4/`
- [ ] Implementar `extractor.py` (buscar dados remotos)
- [ ] Implementar `transformer.py` (normalizar dados)
- [ ] Implementar `loader.py` (UPSERT local)
- [ ] Implementar `watermark_manager.py` (controle de sync)
- [ ] Implementar advisory locks (evitar execução simultânea)
- [ ] Logging estruturado em TODOS os arquivos

### Dia 3: Pipeline e Testes (6-8h)
- [ ] Implementar `pipeline.py` (orquestrador)
- [ ] Criar testes unitários (`tests/multi_tenant/`)
- [ ] Testar extração de 1 inbox (AllpFit)
- [ ] Testar pipeline completo (end-to-end)
- [ ] Executar ETL para AllpFit (tenant_id=1)
- [ ] Validar dados no dashboard (Fase 2)
- [ ] Verificar se queries retornam dados reais (não mais vazias)
- [ ] Documentar implementação (`FASE3_IMPLEMENTACAO.md`)
- [ ] Atualizar cronograma (`00_CRONOGRAMA_MASTER.md`)

---

## 🎯 CRITÉRIOS DE SUCESSO (FASE 3)

A Fase 3 estará completa quando:

1. ✅ ETL sincroniza dados do AllpFit (tenant_id=1) com sucesso
2. ✅ Watermark funciona (apenas dados novos na 2ª execução)
3. ✅ Dashboard mostra dados reais (tabela não mais vazia!)
4. ✅ Queries retornam leads, visitas, etc (colunas reais)
5. ✅ Logs estruturados funcionando (sem prints)
6. ✅ Testes passando (unit + integration)
7. ✅ Documentação completa (`FASE3_IMPLEMENTACAO.md`)
8. ✅ Advisory locks funcionando (sem execução simultânea)
9. ✅ Performance aceitável (< 5min para sync completo)

## 🚀 PRÓXIMAS FASES (Pós-Fase 3)

### Fase 4: Dashboard Cliente Avançado
- Gráficos mais complexos
- Filtros avançados
- Exportação de dados (PDF/Excel)

### Fase 5: Dashboard Admin Completo
- Gerenciamento de clientes (CRUD)
- Métricas agregadas
- Auditoria de ações

### Fase 6: Testes e Deploy
- Testes de segurança
- Deploy em staging/produção
- Monitoramento (Grafana)

---

## 🔗 LINKS RÁPIDOS

- **Aplicação:** http://localhost:8504
- **Logs:** /home/tester/projetos/allpfit-analytics/logs/streamlit_multi_tenant_*.log
- **Banco:** `psql -U isaac -h localhost -d geniai_analytics`
- **Restart:** `./scripts/restart_multi_tenant.sh`

---

**Última atualização:** 2025-11-06 (pós-revisão Fase 2)
**Criado por:** Isaac (via Claude Code)
**Status:** ✅ Fase 2 COMPLETA E REVISADA - Pronto para Fase 3

---

## 📚 REFERÊNCIAS RÁPIDAS

- **Cronograma Completo:** `docs/multi-tenant/00_CRONOGRAMA_MASTER.md`
- **Guia da Fase 3:** `docs/multi-tenant/RECOMENDACOES_FASE3.md` ⭐⭐⭐
- **Banco de Dados:** `docs/multi-tenant/DB_DOCUMENTATION.md`
- **Melhorias Fase 2:** `docs/multi-tenant/FASE2_MELHORIAS.md`
- **ETL V3 Atual:** `src/etl_v3/` (base para adaptar)

---

**BOA SORTE COM A FASE 3! 🚀**
