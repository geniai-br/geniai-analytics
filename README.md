# 📊 AllpFit Analytics

Dashboard para análise de conversas de agente de IA do sistema Chatwoot.

## 📋 Descrição

Sistema completo de analytics que extrai dados de conversas do Chatwoot (banco remoto), processa via ETL e armazena localmente para análises rápidas. Inclui 60+ KPIs mapeados para análise profunda do comportamento do agente de IA.

## 🏗️ Estrutura do Projeto

```
allpfit-analytics/
├── src/
│   ├── app/                    # Dashboard Streamlit (em desenvolvimento)
│   ├── features/               # Pipeline ETL e processamento
│   │   └── etl_pipeline_v2.py  # ETL principal (120 campos)
│   └── shared/                 # Código compartilhado
│       ├── config.py           # Configurações centralizadas
│       └── database.py         # Conexões de banco
│
├── sql/
│   ├── modular_views/          # Views do banco remoto (Chatwoot)
│   │   ├── 00_deploy_all_views_CLEAN.sql  # Deploy de todas as views
│   │   ├── 01-06_*.sql         # Views modulares
│   │   └── 07_vw_conversations_analytics_final.sql  # View final (118 campos)
│   └── local_schema/
│       └── 01_create_schema.sql  # Schema do banco local
│
├── scripts/                    # Scripts utilitários
│   ├── test_connection.py
│   └── test_new_views.py
│
├── docs/                       # Documentação completa
│   ├── dashboard_kpis_completo.md  # 60+ KPIs mapeados
│   ├── etl_resumo_sucesso.md       # Resumo do ETL
│   └── schema_explicacao.md        # Explicação do schema
│
├── data/backups/               # Backups CSV (não versionados)
├── .env                        # Credenciais (não versionado)
├── .env.example                # Template de configuração
├── requirements.txt            # Dependências
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
python3 src/features/etl_pipeline_v2.py
```

**O que o ETL faz:**
1. **EXTRACT:** Busca dados da view `vw_conversations_analytics_final` (remoto)
2. **TRANSFORM:** Processa e limpa 118 campos
3. **LOAD:** Insere 4.169+ conversas no banco local
4. **BACKUP:** Salva CSV em `data/backups/`
5. **STATS:** Mostra estatísticas dos dados

**Performance:**
- ⚡ 4.169 conversas em ~6 segundos
- 📊 118 campos da view remota → 120 campos locais
- 💾 Backup automático de 14+ MB

### Agendar ETL (1x por dia às 3h)

```bash
# Editar crontab
crontab -e

# Adicionar:
0 3 * * * cd /home/isaac/projects/allpfit-analytics && source venv/bin/activate && python3 src/features/etl_pipeline_v2.py >> logs/etl_$(date +\%Y\%m\%d).log 2>&1
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

## 🧪 Testes

```bash
# Testar conexão com banco remoto
python3 scripts/test_connection.py

# Testar views remotas
python3 scripts/test_new_views.py

# Validar dados locais
psql -U isaac -d allpfit -c "SELECT COUNT(*) FROM conversas_analytics;"
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

## 📄 Licença

Projeto interno - Todos os direitos reservados
