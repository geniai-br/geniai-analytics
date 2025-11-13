# Documentação Pública - GeniAI Analytics

Esta pasta contém a **documentação pública** do projeto GeniAI Analytics - uma plataforma multi-tenant de análise de conversas de agentes de IA integrada ao Chatwoot.

## 📁 Estrutura

```
docs/public/
├── README.md                    # Este arquivo (índice da documentação pública)
├── VISAO_GERAL_PROJETO.md       # Visão geral do projeto GeniAI Analytics
└── ARQUITETURA_DB.md            # Arquitetura técnica do banco de dados
```

## 📄 Documentos Disponíveis

### [VISAO_GERAL_PROJETO.md](VISAO_GERAL_PROJETO.md)
**Visão Geral do Projeto**

Documento completo explicando o projeto GeniAI Analytics:
- **O que é**: Plataforma multi-tenant de análise de conversas
- **Problema que resolve**: Desafios do atendimento digital
- **Arquitetura**: Stack tecnológico e componentes principais
- **Funcionalidades**: Dashboard, análise IA, exportação
- **Casos de uso**: Academias, clínicas, e-commerce, escolas
- **Roadmap**: Fases concluídas e planejadas

**Ideal para**: Apresentações, onboarding, visão executiva

### [ARQUITETURA_DB.md](ARQUITETURA_DB.md)
**Arquitetura do Banco de Dados Multi-Tenant**

Documento técnico detalhando:
- **Escolha arquitetural**: Single Database + Row-Level Security (RLS)
- **Schema do banco**: Tabelas, relacionamentos e constraints
- **Segurança**: Implementação de RLS para isolamento de dados entre tenants
- **Modelo de dados**: Estrutura completa das 9 tabelas multi-tenant
- **Decisões de design**: Justificativas técnicas e trade-offs
- **Migração**: Scripts e validação de dados

**Tecnologias:** PostgreSQL, Row-Level Security (RLS), TimescaleDB

## 🏗️ Arquitetura do Sistema

### Visão Geral

O GeniAI Analytics é uma plataforma **multi-tenant SaaS** que permite múltiplos clientes (academias, empresas) analisarem suas conversas do Chatwoot de forma isolada e segura.

**Principais características:**
- 🔐 **Multi-tenancy com RLS**: Isolamento de dados garantido pelo PostgreSQL
- 📊 **Dashboard interativo**: Interface Streamlit personalizada por cliente
- 🤖 **IA Generativa**: Análise automática de conversas com GPT-4o-mini
- 🔄 **ETL automatizado**: Sincronização incremental a cada 30 minutos
- 👥 **Painel Admin**: Visão consolidada de todos os clientes

### Stack Tecnológico

- **Backend**: Python 3.11+
- **Database**: PostgreSQL com Row-Level Security (RLS)
- **Time-series**: TimescaleDB (hypertables para otimização temporal)
- **Dashboard**: Streamlit
- **ETL**: Pipeline Python customizado (Extract-Transform-Load)
- **IA**: OpenAI GPT-4o-mini
- **Automação**: Systemd Timers

### Modelo Multi-Tenant

```
┌─────────────────────────────────────────────────┐
│ PostgreSQL Database: geniai_analytics           │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Tenant 1 │  │ Tenant 2 │  │ Tenant N │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │            │
│       └─────────────┼─────────────┘            │
│                     ▼                          │
│         ┌──────────────────────┐               │
│         │ conversations        │               │
│         │ + tenant_id (RLS)    │               │
│         └──────────────────────┘               │
│                                                 │
│  🔒 RLS Policy: WHERE tenant_id = current_id   │
└─────────────────────────────────────────────────┘
```

**Vantagens da arquitetura Single Database + RLS:**
- ✅ Simplicidade operacional (1 backup, 1 schema)
- ✅ Custos reduzidos (compartilhamento de recursos)
- ✅ Queries cross-tenant para administração
- ✅ Segurança em camada de banco (não depende do código)

## 🔒 Segurança

### Row-Level Security (RLS)

O PostgreSQL automaticamente filtra os dados por `tenant_id`, garantindo que:
- Cada cliente vê **apenas seus próprios dados**
- Mesmo com bugs no código ou SQL injection, o isolamento é mantido
- Administradores podem visualizar todos os tenants quando autorizado

### Autenticação e Sessões

- **Password hashing**: Bcrypt com salt aleatório
- **Sessões**: UUID aleatórios com expiração de 24h
- **Middleware**: Verificação de autenticação em todas as rotas protegidas

## 📊 Pipeline ETL

O sistema sincroniza dados do Chatwoot a cada 30 minutos:

1. **Extract**: Busca novas conversas por tenant (via API ou banco remoto)
2. **Transform**: Normalização, enriquecimento e validação
3. **Load**: Inserção no banco local com `tenant_id` correto
4. **Watermark**: Controle incremental por tenant

## 🎯 Casos de Uso

1. **Dashboard Cliente**: Academia visualiza métricas de suas conversas
2. **Dashboard Admin**: GeniAI monitora todos os clientes simultaneamente
3. **Análise de IA**: Detecção automática de leads inativos para remarketing
4. **Relatórios**: Exportação de dados e insights para tomada de decisão

## 📚 Documentação Adicional

### Documentação Técnica (Privada)
Para informações operacionais, credenciais e checkpoints do projeto, consulte `docs/private/` (não versionada no Git).

### ADRs (Architecture Decision Records)
Decisões arquiteturais importantes foram documentadas seguindo o padrão ADR e estão disponíveis em `docs/architecture/adr/` (se disponível).

### README Principal
Para informações gerais do projeto, instalação e uso, consulte o [README.md](../../README.md) na raiz do repositório.

## 🤝 Contribuindo

Este projeto segue:
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, etc.
- **Git Flow**: Desenvolvimento em branches `feature/*`, merge para `main`
- **Code Review**: Pull requests obrigatórios antes de merge

## 📞 Suporte

- **Repositório**: https://github.com/geniai-br/geniai-analytics
- **Issues**: https://github.com/geniai-br/geniai-analytics/issues
- **Documentação**: Este diretório (`docs/public/`)

---

**Última atualização:** 2025-11-13
**Versão do projeto:** 1.2.0
**Status:** ✅ Sistema multi-tenant operacional e em produção