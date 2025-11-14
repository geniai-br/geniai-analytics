# 📚 AllpFit Analytics - Índice da Documentação

> **Projeto:** AllpFit Analytics - Sistema Multi-Tenant de Analytics com IA
> **Versão:** 1.2.0
> **Última Atualização:** 2025-11-10
> **Status:** 🟢 Em Produção

---

## 🚀 Quick Start

**Novo no projeto?** Comece por aqui:
1. [README.md](../README.md) - Visão geral e setup inicial
2. [CONTEXT.md](CONTEXT.md) - Contexto e objetivos do projeto
3. [Multi-Tenant/00_INDEX.md](multi-tenant/00_INDEX.md) - Documentação multi-tenant

**Procurando algo específico?**
- 🏗️ [Arquitetura](#-arquitetura) - Diagramas e decisões técnicas
- 📖 [Guias Práticos](#-guias-práticos) - Setup, deployment, troubleshooting
- 🗄️ [Base de Dados](#-base-de-dados) - Schema, queries, RLS
- 🤖 [Integração OpenAI](#-integração-openai) - Análise de leads com IA
- 🔄 [ETL Pipeline](#-etl-pipeline) - Pipeline de dados incremental

---

## 📂 Estrutura da Documentação

```
docs/
├── 00_INDEX.md                    # Este arquivo - índice principal
│
├── 📖 CORE DOCUMENTATION
│   ├── CONTEXT.md                 # Contexto do projeto
│   ├── CHANGELOG.md               # Histórico de versões
│   ├── ALLPFIT_COMPREHENSIVE_SUMMARY.md  # Resumo técnico completo
│   ├── PROJECT_TRANSFORMATION_2025.md    # Transformação do projeto
│   └── REFACTORING_2025.md        # Refatorações aplicadas
│
├── 🏗️ ARCHITECTURE
│   ├── architecture/
│   │   ├── diagrams/              # Diagramas C4, PlantUML (a ser gerado)
│   │   ├── adr/                   # Architecture Decision Records
│   │   └── data-flow/             # Fluxos de dados
│   └── schema_explicacao.md       # Schema do banco local
│
├── 📖 GUIDES
│   └── guides/                    # Guias práticos (a ser criado)
│
├── 🗄️ MULTI-TENANT
│   └── multi-tenant/              # Documentação completa multi-tenant
│       ├── 00_INDEX.md            # Índice multi-tenant
│       ├── 00_CRONOGRAMA_MASTER.md
│       ├── 01_ARQUITETURA_DB.md
│       ├── 02_UX_FLOW.md
│       ├── DB_DOCUMENTATION.md    # Banco geniai_analytics
│       ├── PROGRESS.md
│       └── ...
│
├── 🔄 ETL
│   └── ETL_V3_README.md           # Pipeline ETL V3
│
├── 🤖 AI INTEGRATION
│   └── multi-tenant/
│       ├── EXECUTIVE_SUMMARY.md   # Resumo OpenAI
│       └── FASE5_7_OTIMIZACOES_OPENAI.md  # Última versão
│
├── 📦 ARCHIVE
│   └── archive/                   # Documentos históricos
│       ├── BUG_FIX_LOGIN_RLS.md
│       ├── FASE2_MELHORIAS.md
│       └── ... (15 arquivos)
│
└── 🧠 PROJECT MEMORY (Claude)
    └── project_memory_claude/
        ├── 00_INDEX.md
        ├── 02_SESSION_HISTORY.md
        └── 04_CURRENT_STATE.md
```

---

## 📖 Documentação por Categoria

### 🏗️ Arquitetura

#### Visão Geral
- [ALLPFIT_COMPREHENSIVE_SUMMARY.md](ALLPFIT_COMPREHENSIVE_SUMMARY.md) - **Resumo técnico completo**
  - Stack tecnológico
  - Estrutura do projeto
  - Componentes principais
  - Fluxo de dados

#### Base de Dados
- [multi-tenant/01_ARQUITETURA_DB.md](multi-tenant/01_ARQUITETURA_DB.md) - Arquitetura do banco
- [multi-tenant/DB_DOCUMENTATION.md](multi-tenant/DB_DOCUMENTATION.md) - **Documentação completa do banco geniai_analytics**
  - 9 tabelas documentadas
  - Credenciais de acesso
  - Queries úteis
  - Row-Level Security (RLS)
- [schema_explicacao.md](schema_explicacao.md) - Schema do banco local (conversas_analytics)
- [multi-tenant/REMOTE_DATABASE.md](multi-tenant/REMOTE_DATABASE.md) - Banco remoto Chatwoot

#### Diagramas e ADRs
- [architecture/diagrams/](architecture/diagrams/) - Diagramas C4 e PlantUML (a ser gerado)
- [architecture/adr/](architecture/adr/) - Architecture Decision Records (a ser criado)
- [architecture/data-flow/](architecture/data-flow/) - Fluxos de dados (a ser gerado)

---

### 📖 Guias Práticos

#### Setup e Instalação
- [../README.md](../README.md) - **Setup inicial completo**
  - Requisitos
  - Instalação
  - Configuração
  - Primeiro uso

#### UX e Fluxos
- [multi-tenant/02_UX_FLOW.md](multi-tenant/02_UX_FLOW.md) - Fluxos de usuário
  - Admin vs Cliente
  - Wireframes
  - Componentes

#### Deployment
- [multi-tenant/README_USUARIOS.md](multi-tenant/README_USUARIOS.md) - Guia de usuários
- Ver também: `sql/multi_tenant/README.md`, `systemd/README.md`

#### Troubleshooting
- [multi-tenant/00_INDEX.md#troubleshooting](multi-tenant/00_INDEX.md#troubleshooting) - Problemas comuns
- [fix_rls_login_policy.md](fix_rls_login_policy.md) - Fix de RLS

---

### 🔄 ETL Pipeline

#### Documentação Principal
- [ETL_V3_README.md](ETL_V3_README.md) - **Pipeline ETL V3**
  - Extração incremental
  - Transformação
  - UPSERT inteligente
  - Watermarks
  - Performance (~2-5s)

#### Multi-Tenant ETL
- [multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md](multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md) - **ETL V4 otimizado**
  - Processamento paralelo (5x mais rápido)
  - Integração OpenAI
  - Skip inteligente

---

### 🤖 Integração OpenAI

#### Implementação Atual
- [multi-tenant/EXECUTIVE_SUMMARY.md](multi-tenant/EXECUTIVE_SUMMARY.md) - Resumo executivo
- [multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md](multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md) - **Versão atual (Fase 5.7)**
  - GPT-4o-mini
  - 95% accuracy
  - Análise de leads
  - Probabilidade de conversão

#### Planejamento
- [multi-tenant/OPENAI_MULTI_TENANT_IMPLEMENTATION_PLAN.md](multi-tenant/OPENAI_MULTI_TENANT_IMPLEMENTATION_PLAN.md) - Plano de implementação

---

### 🗂️ Gestão do Projeto

#### Cronograma e Progresso
- [multi-tenant/00_CRONOGRAMA_MASTER.md](multi-tenant/00_CRONOGRAMA_MASTER.md) - Cronograma completo (6 fases)
- [multi-tenant/PROGRESS.md](multi-tenant/PROGRESS.md) - Progresso atual
- [CHANGELOG.md](CHANGELOG.md) - Histórico de versões

#### Transformações
- [PROJECT_TRANSFORMATION_2025.md](PROJECT_TRANSFORMATION_2025.md) - Transformação 2025
- [REFACTORING_2025.md](REFACTORING_2025.md) - Refatorações aplicadas

---

### 🧠 Memória do Projeto (Claude)

Para continuidade de desenvolvimento com Claude Code:
- [project_memory_claude/00_INDEX.md](project_memory_claude/00_INDEX.md) - Índice da memória
- [project_memory_claude/02_SESSION_HISTORY.md](project_memory_claude/02_SESSION_HISTORY.md) - Histórico de sessões
- [project_memory_claude/04_CURRENT_STATE.md](project_memory_claude/04_CURRENT_STATE.md) - Estado atual

---

## 🎯 Casos de Uso

### "Sou novo no projeto"
1. Leia [README.md](../README.md) - Setup e contexto geral
2. Leia [CONTEXT.md](CONTEXT.md) - Objetivos de negócio
3. Leia [ALLPFIT_COMPREHENSIVE_SUMMARY.md](ALLPFIT_COMPREHENSIVE_SUMMARY.md) - Visão técnica
4. Explore [multi-tenant/00_INDEX.md](multi-tenant/00_INDEX.md) - Sistema multi-tenant

### "Preciso fazer deploy"
1. [README.md](../README.md) - Setup inicial
2. `sql/multi_tenant/README.md` - Scripts SQL
3. `systemd/README.md` - Configuração de serviços
4. [multi-tenant/DB_DOCUMENTATION.md](multi-tenant/DB_DOCUMENTATION.md) - Credenciais

### "Vou desenvolver uma feature"
1. [multi-tenant/00_CRONOGRAMA_MASTER.md](multi-tenant/00_CRONOGRAMA_MASTER.md) - Ver roadmap
2. [multi-tenant/01_ARQUITETURA_DB.md](multi-tenant/01_ARQUITETURA_DB.md) - Entender arquitetura
3. [architecture/adr/](architecture/adr/) - Consultar decisões técnicas
4. [REFACTORING_2025.md](REFACTORING_2025.md) - Padrões de código

### "Estou debugando um problema"
1. [project_memory_claude/04_CURRENT_STATE.md](project_memory_claude/04_CURRENT_STATE.md) - Estado atual
2. [multi-tenant/00_INDEX.md#troubleshooting](multi-tenant/00_INDEX.md#troubleshooting) - Problemas comuns
3. [fix_rls_login_policy.md](fix_rls_login_policy.md) - Fixes aplicados
4. `logs/` - Verificar logs do sistema

### "Preciso entender o ETL"
1. [ETL_V3_README.md](ETL_V3_README.md) - Pipeline base
2. [multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md](multi-tenant/FASE5_7_OTIMIZACOES_OPENAI.md) - Versão otimizada
3. `src/features/etl/` - Código fonte
4. `tests/test_etl_openai_incremental.py` - Testes

---

## 📞 Referências Rápidas

### Credenciais e Acesso
```bash
# Banco Multi-Tenant
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics

# Ver tenants
SELECT id, name, slug FROM tenants;
```

Ver: [multi-tenant/DB_DOCUMENTATION.md](multi-tenant/DB_DOCUMENTATION.md#credenciais-de-acesso)

### Comandos Úteis
```bash
# ETL manual
bash scripts/etl/run_manual.sh

# Status do ETL
bash scripts/etl/status.sh

# Monitorar logs
bash scripts/etl/monitor.sh

# Reiniciar dashboard
bash scripts/restart_multi_tenant.sh
```

### Portas
- **8501:** Dashboard single-tenant (legado)
- **8502:** Dashboard multi-tenant (produção)
- **8503:** Admin panel
- **5432:** PostgreSQL

---

## 🗃️ Arquivos Arquivados

Documentos históricos (mantidos para referência) em [archive/](archive/):
- Comparações single vs multi-tenant
- Documentação de fases antigas (FASE2-FASE5.6)
- Bug fixes históricos
- Melhorias aplicadas

**Total:** 15 arquivos arquivados

---

## 📊 Estatísticas da Documentação

- **Total de arquivos MD:** ~42 ativos + 15 arquivados
- **Documentos principais:** 12
- **Guias e tutoriais:** 8
- **Documentação técnica:** 15
- **Documentação multi-tenant:** 17
- **Última limpeza:** 2025-11-10

---

## 🔄 Manutenção

### Ao adicionar nova documentação:
1. Adicione o arquivo na pasta apropriada
2. Atualize este índice
3. Adicione entrada no [CHANGELOG.md](CHANGELOG.md)
4. Atualize referências cruzadas

### Ao arquivar documentação:
1. Mova para `archive/` com contexto
2. Atualize este índice
3. Remova links quebrados

### Ao criar diagramas:
1. Coloque em `architecture/diagrams/`
2. Use PlantUML/Mermaid (texto versionável)
3. Documente decisões em `architecture/adr/`

---

## 📝 Notas

- Este índice é atualizado manualmente
- Última reorganização: 2025-11-10
- Próxima etapa: Gerar diagramas arquiteturais (C4 + PlantUML)

---

**Mantido por:** Isaac (via Claude Code)
**Última atualização:** 2025-11-10
**Versão:** 2.0 (pós-reorganização)
