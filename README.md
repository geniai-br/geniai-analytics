# 🤖 GeniAI Analytics

<div align="center">

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)
![License](https://img.shields.io/badge/license-proprietary-red.svg)

**Plataforma Multi-Tenant de Analytics com IA para Chatwoot**

Sistema SaaS de análise de conversas com Inteligência Artificial para empresas que utilizam Chatwoot como plataforma de atendimento.

[Documentação](#-documentação) • [Features](#-principais-features) • [Tecnologias](#-tecnologias)

</div>

---

## 📋 Sobre o Projeto

GeniAI Analytics é uma plataforma multi-tenant completa que transforma conversas do Chatwoot em insights acionáveis através de análise automatizada com IA.

**Aplicável a qualquer segmento:** academias, educação, saúde, varejo, financeiro, e-commerce.

### Diferenciais

- 🎯 **Multi-Tenant Nativo** - Isolamento total com Row-Level Security (RLS)
- 🤖 **Análise IA Automatizada** - GPT-4o-mini para análise de leads e remarketing
- ⚡ **ETL Incremental** - Processamento apenas de dados novos (2-5s)
- 🔒 **Segurança Enterprise** - Autenticação bcrypt, RLS, auditoria completa
- 📊 **Dashboard Interativo** - Visualizações em tempo real com Streamlit
- 🔄 **Auto-Sync de Inboxes** - Detecção automática de novos canais

---

## ✨ Principais Features

### 🎨 Dashboard Multi-Tenant
- **Autenticação segura** por tenant com sessões isoladas
- **KPIs Executivos**: conversões, leads, taxa de conversão, tempo de resposta
- **Análise por Inbox**: métricas separadas por canal (WhatsApp, Instagram, API)
- **Gráficos Interativos**: evolução temporal, distribuição, comparações
- **Filtros Avançados**: 6 filtros rápidos + período customizável
- **Conversas Compiladas**: visualização completa com emojis por tipo de sender

### 🤖 Sistema de Remarketing Inteligente
- **Categorização Automática**: Lead, Atendimento, Dúvida, Reclamação, Outros
- **Análise Temporal**: Recente (0-24h), Médio (1-7 dias), Frio (7+ dias)
- **Mensagens Personalizadas**: geração com IA contextual
- **Identificação de Oportunidades**: leads sem resposta do time
- **Templates Dinâmicos**: adaptação por contexto e histórico

### ⚡ ETL v4 Multi-Tenant
- **Extração Incremental**: watermark automático por tenant
- **Auto-Discovery de Inboxes**: FASE 0 detecta novos canais
- **UPSERT Inteligente**: INSERT novos + UPDATE modificados
- **Transformação Completa**: 25+ colunas com limpeza e validação
- **Advisory Locks**: previne execuções concorrentes
- **Audit Trail**: registro completo de todas as execuções

### 🛡️ Segurança e Isolamento
- **Row-Level Security (RLS)**: isolamento nativo no PostgreSQL
- **Autenticação bcrypt**: hash seguro de senhas (cost factor 12)
- **Sessões com UUID**: controle de acesso por token
- **Policies por Role**: super_admin, admin, client
- **Audit Logs**: rastreamento de ações administrativas

### 📊 Análise com IA
- **Análise de Sentimento**: positivo, neutro, negativo
- **Classificação de Leads**: Alto, Médio, Baixo interesse
- **Score de Conversão**: 0-100% probabilidade
- **Extração de Dados**: nome, condição física, objetivo (contexto academia)
- **Sugestões de Remarketing**: mensagens personalizadas

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND                          │
├─────────────────────────────────────────────────────┤
│  Streamlit Multi-Tenant                             │
│  - Dashboard Cliente (analytics + remarketing)      │
│  - Painel Admin (gestão de tenants e usuários)      │
│  - Autenticação com RLS                             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   BACKEND                           │
├─────────────────────────────────────────────────────┤
│  Python 3.11+                                       │
│  - ETL v4 (incremental com watermark)               │
│  - Sistema de Remarketing (GPT-4o-mini)             │
│  - Auto-Discovery de Inboxes                        │
│  - Rate Limiter + Cost Tracker                      │
│  - Template Manager                                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   DATABASE                          │
├─────────────────────────────────────────────────────┤
│  PostgreSQL 15+ com RLS                             │
│  - TimescaleDB (hypertables)                        │
│  - 10 tabelas principais                            │
│  - 20+ índices otimizados                           │
│  - Policies de isolamento por tenant                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│               FONTE DE DADOS                        │
├─────────────────────────────────────────────────────┤
│  Chatwoot (Open Source)                             │
│  - PostgreSQL remoto (read-only)                    │
│  - View agregada de conversas                       │
│  - Multi-inbox, multi-canal                         │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Estrutura do Projeto

```
geniai-analytics/
├── src/
│   ├── multi_tenant/              # Sistema multi-tenant
│   │   ├── auth/                  # Autenticação e middleware RLS
│   │   ├── dashboards/            # Dashboards Streamlit
│   │   │   ├── app.py             # Router principal
│   │   │   ├── login_page.py      # Autenticação
│   │   │   ├── admin_panel.py     # Gestão de tenants
│   │   │   └── client_dashboard.py # Dashboard do cliente
│   │   ├── etl_v4/                # Pipeline ETL
│   │   │   ├── pipeline.py        # Orquestrador principal
│   │   │   ├── extractor.py       # Extração do Chatwoot
│   │   │   ├── transformer.py     # Transformação de dados
│   │   │   ├── loader.py          # Carga no banco local
│   │   │   ├── inbox_sync.py      # Auto-discovery de inboxes
│   │   │   ├── remarketing_analyzer.py # Análise de remarketing
│   │   │   └── analyzers/         # Analisadores de IA
│   │   └── utils/                 # Utilitários
│   │       ├── rate_limiter.py    # Controle de taxa OpenAI
│   │       ├── cost_tracker.py    # Tracking de custos
│   │       └── template_manager.py # Gestão de templates
│   │
│   └── app/                       # Configurações do dashboard
│       ├── config.py              # Tema e formatação
│       └── utils/                 # Utilidades
│           └── metrics.py         # Cálculo de KPIs
│
├── scripts/                       # Scripts de automação
│   ├── restart_multi_tenant.sh    # Reiniciar dashboard
│   ├── analysis/                  # Scripts de análise
│   ├── maintenance/               # Manutenção
│   └── investigation/             # Debug e investigação
│
├── sql/                           # Database
│   ├── migrations/                # Migrations
│   └── 11_add_ai_analysis_columns.sql
│
├── docs/                          # Documentação
│   ├── public/                    # Documentação pública
│   │   └── VISAO_GERAL_PROJETO.md
│   └── private/                   # Documentação interna
│       └── checkpoints/           # Checkpoints de desenvolvimento
│
├── tests/                         # Testes automatizados
│
├── .env.example                   # Template de configuração
├── requirements.txt               # Dependências Python
└── README.md                      # Este arquivo
```

---

## 🛠️ Tecnologias

### Backend
- **Python 3.11+** - Linguagem principal
- **Pandas** - Manipulação de dados
- **SQLAlchemy** - ORM e conexões de banco
- **psycopg2** - Driver PostgreSQL
- **OpenAI SDK** - Integração GPT-4o-mini
- **bcrypt** - Hash seguro de senhas

### Frontend
- **Streamlit** - Framework web para dashboards
- **Plotly** - Gráficos interativos
- **Pandas** - Processamento de dados

### Database
- **PostgreSQL 15+** - Banco de dados relacional
- **TimescaleDB** - Extensão para séries temporais
- **Row-Level Security (RLS)** - Isolamento multi-tenant nativo

### DevOps
- **Systemd Timers** - Agendamento de tarefas
- **GitHub Actions** - CI/CD (testes automatizados)
- **Git** - Controle de versão

---

## 📚 Documentação

### Documentação Pública
- [Visão Geral do Projeto](docs/public/VISAO_GERAL_PROJETO.md)
- [Arquitetura do Banco de Dados](docs/public/ARQUITETURA_DB.md)

### Documentação Técnica (Privada)
- Estado Atual do Projeto
- Checkpoints de Desenvolvimento
- Guia de Usuários do Banco

---

## 📄 Licença

Copyright © 2025 GeniAI. Todos os direitos reservados.

Este é um software proprietário. O uso, cópia, modificação e distribuição não autorizados são estritamente proibidos.

---