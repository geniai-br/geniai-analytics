# 📊 AllpFit Analytics

<div align="center">

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)
![Version](https://img.shields.io/badge/version-1.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-black.svg)

Dashboard para análise de conversas de agente de IA do sistema Chatwoot.

[Features](#-principais-features) •
[Instalação](#-setup-inicial) •
[Documentação](#-documentação) •
[Contribuir](#-como-contribuir)

</div>

---

## 📋 Descrição

Sistema completo de analytics que extrai dados de conversas do Chatwoot (banco remoto), processa via ETL e armazena localmente para análises rápidas. Inclui 60+ KPIs mapeados para análise profunda do comportamento do agente de IA.

## ✨ Principais Features

- 🤖 **Dashboard Interativo** - Streamlit com 12 KPIs e visualizações em tempo real
- ⚡ **ETL V3 Incremental** - Extração inteligente apenas de dados novos (2-5 segundos)
- 🔄 **UPSERT Automático** - INSERT para novos, UPDATE para modificados
- 📊 **60+ KPIs Mapeados** - Executive, Operacional, Qualidade, Temporal
- 🧠 **Análise com IA** - GPT-4 para análise de conversas e probabilidade de conversão
- 📞 **Integração CRM** - Crossmatch telefones Bot ↔ EVO CRM
- 🔐 **Seguro** - Credenciais no .env, usuário read-only no banco remoto
- 📈 **Production-Ready** - CI/CD, testes, logs estruturados
- 🎯 **Tracking de Conversões** - Identifica leads que viraram clientes
- 🔔 **Monitoramento** - Scripts de status, logs e alertas

## 🏗️ Estrutura do Projeto

```
allpfit-analytics/
├── src/
│   ├── app/                    # Dashboard Streamlit
│   │   ├── dashboard.py        # Dashboard principal
│   │   ├── config.py           # Tema e formatação
│   │   └── utils/              # Utilidades do dashboard
│   │
│   ├── features/               # Features principais
│   │   ├── etl/                # Pipeline ETL modular
│   │   │   ├── extractor.py
│   │   │   ├── transformer.py
│   │   │   ├── loader.py
│   │   │   └── watermark_manager.py
│   │   │
│   │   ├── etl_pipeline_v3.py  # ETL V3 incremental
│   │   │
│   │   ├── analyzers/          # Analisadores de conversas
│   │   │   ├── rule_based.py   # Análise por regras
│   │   │   ├── gpt4.py         # Análise com IA
│   │   │   └── initial_load.py # Carga inicial
│   │   │
│   │   └── crm/                # Integração CRM
│   │       └── crossmatch.py   # Crossmatch Excel ↔ Bot
│   │
│   ├── integrations/           # Integrações externas
│   │   └── evo_crm.py          # Cliente API EVO
│   │
│   └── shared/                 # Código compartilhado
│       ├── config.py           # Configurações centralizadas
│       └── database.py         # Conexões de banco
│
├── scripts/                    # Scripts de automação
│   ├── etl/
│   │   ├── run_manual.sh       # Executar ETL manualmente
│   │   ├── monitor.sh          # Monitorar ETL
│   │   └── status.sh           # Status do ETL
│   │
│   ├── analysis/
│   │   └── run_gpt4.py         # Análise GPT-4 manual
│   │
│   └── deployment/
│       └── restart_dashboard.sh # Reiniciar dashboard
│
├── data/                       # Dados do projeto
│   ├── backups/                # Backups CSV do ETL
│   ├── input/                  # Arquivos de entrada (Excel)
│   └── reports/                # Relatórios gerados
│
├── sql/
│   ├── modular_views/          # Views do banco remoto (Chatwoot)
│   └── local_schema/           # Schema do banco local
│
├── docs/                       # Documentação
│   ├── ETL_V3_README.md        # Documentação ETL V3
│   ├── schema_explicacao.md    # Explicação do schema
│   ├── CHANGELOG.md            # Histórico de mudanças
│   └── CONTEXT.md              # Contexto do projeto
│
├── tests/                      # Testes (estrutura preparada)
│
├── .env                        # Credenciais (não versionado)
├── .env.example                # Template de configuração
├── requirements.txt            # Dependências de produção
├── requirements-dev.txt        # Dependências de desenvolvimento
└── README.md
```

## 🚀 Setup Inicial

### 1. Clonar o repositório

```bash
git clone git@github.com:geniai-br/allpfit-analytics.git
cd allpfit-analytics
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
```

### 3. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Copie o arquivo de exemplo e configure:

```bash
cp .env.example .env
nano .env  # ou seu editor preferido
```

Configuração do `.env`:

```env
# Banco REMOTO (Chatwoot - source)
SOURCE_DB_HOST=178.156.206.184
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=chatwoot
SOURCE_DB_USER=hetzner_dev_isaac_read
SOURCE_DB_PASSWORD=sua_senha
SOURCE_DB_VIEW=vw_conversations_analytics_final

# Banco LOCAL (Analytics - destino)
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=allpfit
LOCAL_DB_USER=isaac
LOCAL_DB_PASSWORD=sua_senha
LOCAL_DB_TABLE=conversas_analytics
```

### 5. Configurar banco local

```bash
# Criar banco PostgreSQL local
sudo -u postgres psql -c "CREATE DATABASE allpfit OWNER isaac;"

# Criar schema
psql -U isaac -d allpfit -f sql/local_schema/01_create_schema.sql
```

## 🔄 Pipeline ETL

### Executar ETL manualmente

```bash
# Incremental (padrão - apenas dados novos)
bash scripts/etl/run_manual.sh

# Carga completa (todos os dados)
bash scripts/etl/run_manual.sh --full
```

**O que o ETL V3 faz:**
1. **EXTRACT:** Busca dados incrementais da view `vw_conversations_analytics_final` (remoto)
2. **TRANSFORM:** Processa e valida 118 campos
3. **LOAD:** UPSERT inteligente (INSERT novos, UPDATE modificados)
4. **WATERMARK:** Controla ponto de sincronização automático
5. **AUDIT:** Registra execução na tabela `etl_control`

**Performance:**
- ⚡ Modo incremental: ~2-5 segundos (apenas novos dados)
- 📊 118 campos da view remota → 120 campos locais
- 💾 Logs estruturados em `logs/etl/`

### Monitorar ETL

```bash
# Ver status do ETL
bash scripts/etl/status.sh

# Monitorar logs em tempo real
bash scripts/etl/monitor.sh
```

### Agendar ETL (automático - 1x por hora)

O ETL já está agendado via cron para executar a cada hora:

```bash
# Ver agendamentos
crontab -l | grep etl

# Executar manualmente se necessário
bash scripts/etl/run_manual.sh
```

## 📊 Dados e Views

### Arquitetura

```
BANCO REMOTO (Chatwoot)
    ↓
7 Views Modulares
    ↓
vw_conversations_analytics_final (118 campos)
    ↓
ETL Pipeline
    ↓
BANCO LOCAL (allpfit)
    ↓
conversas_analytics (121 colunas, 16 índices)
    ↓
Dashboard Streamlit
```

### Views Remotas (já criadas no Chatwoot)

1. `vw_conversations_base_complete` - Dados base
2. `vw_messages_compiled_complete` - Mensagens em JSON
3. `vw_csat_base` - Satisfação (CSAT/NPS)
4. `vw_conversation_metrics_complete` - Métricas e flags
5. `vw_message_stats_complete` - Estatísticas de mensagens
6. `vw_temporal_metrics` - Análise temporal
7. `vw_conversations_analytics_final` - **View final com tudo**

### Tabela Local

**conversas_analytics:**
- 121 colunas (120 de dados + 1 ID auto-increment)
- 16 índices para performance
- Campos de controle: `etl_inserted_at`, `etl_updated_at`

**Principais campos:**
- Identificação: conversation_id, display_id, contact_name, contact_phone
- Status: status, status_label_pt, priority
- Mensagens: message_compiled (JSON), t_messages
- CSAT: csat_rating, csat_nps_category
- Métricas: first_response_time, resolution_time
- Flags: has_human_intervention, is_bot_resolved, has_csat
- Temporal: conversation_date, year, month, hour, period

## 🛠️ Tecnologias

- **Python 3.11+**
- **PostgreSQL 15** - Banco de dados (remoto + local)
- **Pandas** - Processamento de dados
- **SQLAlchemy** - ORM e conexões
- **Streamlit** - Dashboard interativo (em desenvolvimento)
- **Plotly** - Visualizações
- **python-dotenv** - Variáveis de ambiente

## 📈 KPIs Disponíveis

60+ KPIs mapeados em 6 níveis:

1. **Executive (15 KPIs)** - Visão macro
2. **Operacional (12 KPIs)** - Eficiência
3. **Qualidade (10 KPIs)** - CSAT e satisfação
4. **Segmentos (15 KPIs)** - Por canal, time, agente
5. **Temporal (8 KPIs)** - Tendências e sazonalidade
6. **Drill-down** - Detalhamento individual

Ver: `docs/dashboard_kpis_completo.md`

## 🔗 Integração CRM

### Crossmatch Excel ↔ Bot

Identifica conversões reais (leads que falaram com o bot ANTES de entrar no CRM):

```bash
# 1. Colocar arquivo base_evo.xlsx em data/input/
# 2. Executar crossmatch
python3 src/features/crm/crossmatch.py

# O script irá:
# - Normalizar telefones (remove DDI/DDD, testa com/sem 9)
# - Cruzar com conversas do bot
# - Identificar conversões (bot → CRM)
# - Salvar no banco: conversas_crm_match_real
# - Gerar relatório em data/reports/
```

### Análise com IA (GPT-4)

```bash
# Analisar conversas com GPT-4
python3 scripts/analysis/run_gpt4.py

# Analisar apenas 10 conversas
python3 scripts/analysis/run_gpt4.py --limit 10

# Modo silencioso
python3 scripts/analysis/run_gpt4.py --quiet
```

## 🧪 Testes

```bash
# Testar imports
python3 -c "import sys; sys.path.insert(0, 'src'); from features.etl import extractor; print('✅ OK')"

# Validar dados locais
psql -U isaac -d allpfit -c "SELECT COUNT(*) FROM conversas_analytics;"

# Ver últimas execuções do ETL
psql -U isaac -d allpfit -c "SELECT * FROM etl_control ORDER BY execution_id DESC LIMIT 5;"
```

## 📚 Documentação

- `docs/dashboard_kpis_completo.md` - Lista completa de KPIs
- `docs/etl_resumo_sucesso.md` - Como funciona o ETL
- `docs/schema_explicacao.md` - Estrutura do banco local
- `sql/modular_views/README.md` - Documentação das views

## 🔒 Segurança

- ✅ Credenciais em `.env` (não versionado)
- ✅ Usuário read-only no banco remoto
- ✅ Banco local isolado
- ✅ Backups automáticos

## ✅ Status do Projeto

### Concluído ✅

- [x] Views modulares no banco remoto (7 views)
- [x] Schema do banco local (121 colunas, 16 índices)
- [x] ETL Pipeline V2 funcionando (6 segundos)
- [x] Backup automático em CSV
- [x] Documentação completa
- [x] Mapeamento de 60+ KPIs

### Em Desenvolvimento 🚧

- [ ] Dashboard Streamlit
- [ ] Visualizações interativas
- [ ] Filtros e drill-down

### Futuro 💡

- [ ] Agendamento automático (cron)
- [ ] Alertas e notificações
- [ ] API REST para consultas
- [ ] Análise preditiva com ML

## 👥 Equipe

Desenvolvido por GenIAI

## 🤝 Como Contribuir

Contribuições são bem-vindas! Siga os passos:

1. **Fork o projeto**
2. **Crie uma branch** para sua feature (`git checkout -b feature/MinhaFeature`)
3. **Commit suas mudanças** (`git commit -m 'feat: Adiciona MinhaFeature'`)
4. **Push para a branch** (`git push origin feature/MinhaFeature`)
5. **Abra um Pull Request**

### Convenções de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `refactor:` Refatoração de código
- `test:` Adição de testes
- `chore:` Tarefas de manutenção

### Code Style

- **Python:** Black + Flake8 + MyPy
- **Line Length:** 120 caracteres
- **Docstrings:** Google style

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para mais detalhes.

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE) - veja o arquivo LICENSE para detalhes.

Copyright © 2025 GenIAI
