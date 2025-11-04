# AllpFit Analytics - Complete Application Overview

## Executive Summary

**AllpFit Analytics** is a production-ready Python analytics dashboard system (v1.2.0) that synchronizes conversation data from Chatwoot (a ChatBot/customer service platform) to a local PostgreSQL database, processes it with GPT-4 AI analysis, and presents insights through an interactive Streamlit dashboard. It's built for a CrossFit gym (AllpFit) to track and analyze AI bot conversations with leads.

**Key Stats:**
- Python 3.11+ application
- MIT Licensed, developed by GenIAI
- 506+ conversations tracked
- 60+ KPIs mapped across 6 dimensions
- Production deployment with automated cron scheduling
- ~4 second ETL performance for incremental syncs

---

## 1. PROJECT STRUCTURE & TECHNOLOGY STACK

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.11+ |
| **Web Framework** | Streamlit | 1.28.0+ |
| **Primary Database** | PostgreSQL | 15+ |
| **ORM/Connectors** | SQLAlchemy, psycopg2 | 2.0+, 2.9+ |
| **Data Processing** | Pandas | 2.0+ |
| **Visualization** | Plotly | 5.17.0+ |
| **AI Integration** | OpenAI GPT-4o | - |
| **Environment** | python-dotenv | 1.0+ |
| **Build System** | setuptools/wheel | Python packaging standard |

### Directory Structure

```
allpfit-analytics/
├── src/                          # Main source code
│   ├── app/                      # Streamlit dashboard application
│   │   ├── dashboard.py          # Main dashboard UI (800+ lines)
│   │   ├── config.py             # Theme, formatting, CSS
│   │   └── utils/
│   │       ├── db_connector.py   # PostgreSQL connection pool (cached)
│   │       ├── metrics.py        # KPI calculation & query functions
│   │       └── __init__.py
│   │
│   ├── features/                 # Core business logic
│   │   ├── etl_pipeline_v3.py   # Main ETL orchestrator (286 lines)
│   │   ├── etl/                  # Modular ETL components
│   │   │   ├── extractor.py      # Incremental data extraction (172 lines)
│   │   │   ├── transformer.py    # Data validation/transformation (126 lines)
│   │   │   ├── loader.py         # UPSERT logic (234 lines)
│   │   │   ├── watermark_manager.py  # Sync point tracking (222 lines)
│   │   │   ├── logger.py         # Structured logging
│   │   │   └── __init__.py
│   │   ├── analyzers/            # AI analysis modules
│   │   │   ├── gpt4.py           # GPT-4 conversation analysis (100+ lines)
│   │   │   ├── rule_based.py     # Legacy rule-based analysis
│   │   │   ├── initial_load.py   # Batch analysis setup
│   │   │   └── __init__.py
│   │   ├── crm/                  # CRM integration
│   │   │   ├── crossmatch.py     # Excel<->Bot phone crossmatch
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── integrations/             # External APIs
│   │   ├── evo_crm.py           # EVO CRM API client (80+ lines)
│   │   └── __init__.py
│   │
│   ├── shared/                   # Shared utilities
│   │   ├── config.py            # Centralized configuration (144 lines)
│   │   ├── database.py          # PostgreSQL connection manager (107 lines)
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── sql/                          # Database schemas & views
│   ├── local_schema/
│   │   ├── 01_create_schema.sql  # Main table: conversas_analytics (121 cols)
│   │   ├── 02_create_etl_control.sql  # Audit/control table
│   │   └── 03_create_conversas_analytics_ai.sql  # AI analysis table
│   └── modular_views/            # Remote database views (Chatwoot)
│       ├── 01_vw_conversations_base_complete.sql
│       ├── 02_vw_messages_compiled_complete.sql
│       ├── 03_vw_csat_base.sql
│       ├── 04_vw_conversation_metrics_complete.sql
│       ├── 05_vw_message_stats_complete.sql
│       ├── 06_vw_temporal_metrics.sql
│       ├── 07_vw_conversations_analytics_final.sql  # Main view (118 fields)
│       └── 00_deploy_all_views_CLEAN.sql
│
├── scripts/                      # Automation & operational scripts
│   ├── etl/
│   │   ├── run_manual.sh         # Manual ETL execution
│   │   ├── monitor.sh            # Real-time monitoring (cron status, logs, stats)
│   │   └── status.sh             # ETL status check
│   ├── analysis/
│   │   └── run_gpt4.py           # Manual GPT-4 analysis trigger
│   └── deployment/
│       └── restart_dashboard.sh  # Dashboard restart utility
│
├── tests/                        # Test suite
│   ├── test_config.py            # Configuration tests
│   ├── test_imports.py           # Import validation
│   ├── test_crm.py               # CRM integration tests
│   └── __init__.py
│
├── data/                         # Data storage & artifacts
│   ├── backups/                  # CSV backups of ETL runs
│   ├── input/                    # Input files (e.g., base_evo.xlsx for CRM match)
│   └── reports/                  # Generated analysis reports
│
├── docs/                         # Documentation
│   ├── ETL_V3_README.md          # ETL pipeline documentation (420 lines)
│   ├── schema_explicacao.md      # Database schema explanation
│   ├── CONTEXT.md                # Project context & quick reference
│   ├── CHANGELOG.md              # Version history
│   ├── PGADMIN_CONFIGURATION.md  # PgAdmin setup guide
│   └── project_memory_claude/    # Session history & learnings
│
├── .github/                      # GitHub Actions CI/CD
│   └── workflows/
│       ├── ci.yml                # CI pipeline (linting, tests, security scans)
│       └── release.yml           # Release workflow
│
├── pyproject.toml                # Poetry/setuptools config
├── requirements.txt              # Production dependencies (11 packages)
├── requirements-dev.txt          # Development dependencies (5 packages)
├── .env                          # Runtime configuration (not versioned)
├── .env.example                  # Configuration template
├── .gitignore                    # Git exclusions
├── README.md                     # Main project documentation (408 lines)
├── CONTRIBUTING.md               # Contribution guidelines
├── SECURITY.md                   # Security policy
├── LICENSE                       # MIT License
└── venv/                         # Python virtual environment
```

### Key Entry Points

1. **Dashboard**: `src/app/dashboard.py` → `streamlit run src/app/dashboard.py`
2. **ETL Pipeline**: `src/features/etl_pipeline_v3.py` → Manual or cron execution
3. **GPT-4 Analysis**: `scripts/analysis/run_gpt4.py` → Manual analysis trigger
4. **CRM Crossmatch**: `src/features/crm/crossmatch.py` → Excel↔Bot phone matching

---

## 2. IMPLEMENTATION DETAILS & CORE FUNCTIONALITY

### 2.1 ETL Pipeline V3 (Incremental Extract-Transform-Load)

**Purpose**: Synchronize conversation data from remote Chatwoot database to local PostgreSQL every hour.

**Architecture**:
```
Chatwoot Remote DB
    ↓
PHASE 1: EXTRACT
  • Connects to remote PostgreSQL (Chatwoot)
  • Uses watermark (last_updated_at) for incremental sync
  • Queries view: vw_conversations_analytics_final (118 fields)
  • Returns only new/modified conversations since last run
  • Performance: ~2-5 seconds for incremental loads
    ↓
PHASE 2: TRANSFORM
  • Validates data integrity
  • Handles NULL/NaN values (converts to None for DB)
  • Formats datetime fields
  • Enriches data where needed
    ↓
PHASE 3: LOAD
  • UPSERT strategy (INSERT new, UPDATE existing)
  • Checks conversation_id uniqueness
  • Only updates if remote updated_at > local updated_at
  • Maintains etl_inserted_at (immutable) and etl_updated_at (mutable)
  • Writes to local table: conversas_analytics (121 columns)
  • Performance: ~500+ records/second
    ↓
PHASE 4: WATERMARK & AUDIT
  • Updates watermark to max(conversation_updated_at)
  • Records execution in etl_control table
  • Logs execution ID, status, row counts, duration
    ↓
PHASE 5: AI ANALYSIS (if rows_inserted > 0 or rows_updated > 0)
  • Identifies conversations needing analysis
  • Calls GPT-4o with structured prompt
  • Stores results in conversas_analytics_ai table
```

**Key Files**:
- `src/features/etl_pipeline_v3.py` (286 lines) - Orchestrator
- `src/features/etl/extractor.py` (172 lines) - Remote data extraction
- `src/features/etl/transformer.py` (126 lines) - Data transformation
- `src/features/etl/loader.py` (234 lines) - UPSERT operations
- `src/features/etl/watermark_manager.py` (222 lines) - Sync state tracking

**Data Models**:

**Source (Remote Chatwoot)**:
- 7 modular views → 1 final view (vw_conversations_analytics_final)
- 118 fields per conversation
- Fields include: IDs, timestamps, contact info, messages (JSON), metrics, CSAT, flags

**Destination (Local)**:
- `conversas_analytics`: 121 columns
  - Core: conversation_id (PK), display_id, account_id
  - Contact: contact_name, contact_phone, contact_email
  - Status: status, priority, assigned_agent, team
  - Messages: message_compiled (JSONB), total_messages
  - CSAT: csat_rating, csat_nps_category, csat_feedback
  - Metrics: first_response_time, resolution_time, duration
  - Timestamps: created_at, updated_at, last_activity_at
  - Flags: has_human_intervention, is_bot_resolved, has_csat (28 boolean columns)
  - Indices: 16 indexes for query optimization
- `etl_control`: Audit table for every execution
  - execution_id, triggered_by, load_type, status
  - rows_extracted, rows_inserted, rows_updated, rows_unchanged
  - watermark_start, watermark_end
  - duration_seconds, extract_duration, transform_duration, load_duration
  - error_message, error_traceback (if failed)

### 2.2 Dashboard (Streamlit Web UI)

**Purpose**: Real-time analytics and lead management interface for sales team.

**URL**: `https://analytcs.geniai.online` (production) or `localhost:8501` (local)

**Features**:

1. **KPI Overview Section** (6 main metrics):
   - Total Contacts (unique leads)
   - AI Conversations (bot-only chats)
   - Human Conversations (agent-handled)
   - Scheduled Visits
   - Sales from Traffic (bot→CRM conversions)
   - Total Sales (CRM database)

2. **Daily Results Section** (6 daily metrics):
   - New Leads (today's first contacts)
   - Visits Scheduled (for today)
   - Sales Today (converted leads)
   - Total Conversations (today)
   - New Conversations (new chats)
   - Reopened Conversations (returning leads)

3. **Charts & Visualizations**:
   - Bar chart: Average leads per day (30 days) with trend line
   - Bar chart: Distribution by time period (morning, afternoon, evening, night)

4. **CRM Conversions Tracking**:
   - Shows leads from bot that became CRM customers
   - Crossmatch via phone number normalization
   - Displays: Customer name, phone, conversation date, CRM signup date

5. **Lead Analysis Section** (GeniAI Analysis):
   - Advanced filters: Name, Probability, Physical Condition, Goal, Date Range
   - Paginated table (50 leads/page)
   - Columns displayed:
     - Nome, Nome Mapeado Bot, Celular
     - Condição Física (Sedentário | Iniciante | Intermediário | Avançado)
     - Objetivo (Perda de peso, Ganho muscular, Condicionamento, etc.)
     - Data Primeiro Contato, Data Última Conversa
     - Conversa Compilada (formatted chat history)
     - Análise IA (5-paragraph AI analysis)
     - Sugestão de Disparo (personalized follow-up message)
     - Probabilidade (0-5 score with emoji indicators)
   - Download CSV button (matches visible table format)

**Architecture**:
- Single-file application (~800 lines)
- Session state management for filters & pagination
- Streamlit caching (@st.cache_data, @st.cache_resource)
- Custom dark theme (blue/orange, Tailwind-inspired)
- PostgreSQL connection pooling via SQLAlchemy
- Real-time data with 5-minute cache TTL

**Code Structure**:
```python
# 1. Page setup & theme
configure_page()  # Dark theme, custom CSS

# 2. Header with filters
# Date range pickers, refresh button, filter clearance

# 3. Load data
@st.cache_data(ttl=300)
def load_data():
    return get_all_conversations()

# 4. Apply date filters
df_filtered = apply_date_range_filters(df_all, date_start, date_end)

# 5. Display KPI cards (col1-col6 layout)
st.metric("Total Contatos", format_number(total_contacts), ...)

# 6. Display charts (Plotly)
fig = go.Figure()
st.plotly_chart(fig)

# 7. Display lead table with pagination
df_paginated = get_leads_with_ai_analysis(engine, limit=50, offset=offset)
st.dataframe(df_paginated)

# 8. Footer with metadata
st.markdown(f"Atualizado em: {datetime.now()}")
```

### 2.3 GPT-4 AI Analysis Engine

**Purpose**: Intelligently analyze conversations to extract lead intent, objections, and conversion probability.

**Trigger**: Automatically runs after ETL if new/updated conversations found.

**Workflow**:
1. Find conversations without analysis OR updated since last analysis
2. Extract message history (message_compiled JSON)
3. Call OpenAI GPT-4o API with structured prompt
4. Parse JSON response
5. UPSERT into conversas_analytics_ai table
6. Log results

**Analysis Output (JSON)**:
```json
{
  "nome_mapeado_bot": "João Silva",
  "condicao_fisica": "Iniciante",
  "objetivo": "Perda de peso",
  "probabilidade_conversao": 4,
  "visita_agendada": true,
  "analise_ia": "Parágrafo 1: Perfil... Parágrafo 2: Engajamento... etc.",
  "sugestao_disparo": "João, vimos que você é iniciante e quer perder peso! Quer agendar uma visita para conhecer nossa academia?"
}
```

**Probability Scale** (0-5):
- **5 - VERY HIGH**: Scheduled visit OR asked about enrollment OR confirmed start date
- **4 - HIGH**: Asked about pricing + hours + clear interest signals
- **3 - MEDIUM**: Multiple questions without urgency
- **2 - LOW**: Generic questions, short responses
- **1 - VERY LOW**: Objections (expensive, far, no time)
- **0 - NONE**: No engagement, random messages, clearly uninterested

**Model Config**:
- Model: gpt-4o (OpenAI)
- Temperature: 0.3 (consistent, deterministic)
- Max tokens: 1500
- Response format: JSON

**Key Files**:
- `src/features/analyzers/gpt4.py` (100+ lines)

### 2.4 CRM Integration

**Purpose**: Track which leads from Chatwoot bot actually converted to paying customers in the EVO CRM system.

**Capabilities**:
1. **EVO CRM API Client** (`src/integrations/evo_crm.py`):
   - HTTPBasicAuth with DNS + API token
   - Rate limiting (40 req/min)
   - Endpoints: `/api/v2/members`, `/api/v2/sales`

2. **Phone Crossmatch** (`src/features/crm/crossmatch.py`):
   - Loads base_evo.xlsx (CRM customer list with phone numbers)
   - Normalizes phone numbers (removes country/area codes, tests with/without 9)
   - Matches against conversations by phone_number
   - Identifies: Leads who talked to bot THEN became customers
   - Stores matches in conversas_crm_match_real table
   - Generates reports in data/reports/

**Configuration**:
- EVO CRM DNS: Via environment variables
- EVO CRM API Token: sk-xxx (stored in .env)

---

## 3. CONFIGURATION FILES & SETUP

### 3.1 Environment Configuration (.env)

```env
# ============================================
# BANCO DE DADOS REMOTO (SOURCE)
# ============================================
SOURCE_DB_HOST=178.156.206.184
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=chatwoot
SOURCE_DB_USER=hetzner_dev_isaac_read
SOURCE_DB_PASSWORD=89cc59cca789
SOURCE_DB_VIEW=vw_conversations_analytics_final

# ============================================
# BANCO DE DADOS LOCAL
# ============================================
LOCAL_DB_HOST=/var/run/postgresql
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=allpfit
LOCAL_DB_USER=isaac
LOCAL_DB_PASSWORD=AllpFit2024@Analytics
LOCAL_DB_TABLE=conversas_analytics

# ============================================
# OPENAI CONFIGURATION
# ============================================
OPENAI_API_KEY=sk-proj-j6KLtfEtFUA_...
OPENAI_MODEL=gpt-4o

# ============================================
# GENERAL CONFIGURATION
# ============================================
DATA_DIR=data
LOG_LEVEL=INFO
```

### 3.2 Dependencies & Build Configuration

**Production Requirements** (`requirements.txt`):
```
pandas==2.1.4           # Data processing
sqlalchemy==2.0.25      # ORM & connection pooling
psycopg2-binary==2.9.9  # PostgreSQL adapter
python-dotenv==1.0.0    # Environment variable loading
streamlit==1.29.0       # Web dashboard framework
plotly==5.18.0          # Interactive charts
```

**Development Requirements** (`requirements-dev.txt`):
```
pytest>=7.4.0           # Testing framework
pytest-cov>=4.1.0       # Code coverage
black>=23.7.0           # Code formatting
flake8>=6.1.0           # Linting
mypy>=1.5.0             # Type checking
ipython==8.19.0         # Interactive shell
```

**Build Configuration** (`pyproject.toml`):
```toml
[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "allpfit-analytics"
version = "1.2.0"
requires-python = ">=3.11"

[tool.black]
line-length = 120
target-version = ['py311']

[tool.flake8]
max-line-length = 120
extend-ignore = ["E203", "W503"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
```

### 3.3 GitHub Actions CI/CD Configuration

**CI Pipeline** (`.github/workflows/ci.yml`):
1. **Code Quality**:
   - Lint with flake8 (critical errors only)
   - Format check with black
   - Type check with mypy

2. **Testing**:
   - Run pytest with coverage
   - Upload to Codecov

3. **Security**:
   - Bandit security scan

4. **Build**:
   - Package verification
   - Import checks for critical modules

---

## 4. DEPLOYMENT SETUP

### 4.1 Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Internet Users                        │
│              analytcs.geniai.online                     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Reverse Proxy (nginx/Apache)               │
│                    Port 443 → 8501                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         Streamlit Dashboard Server (Port 8501)          │
│  systemctl status allpfit-analytics.service             │
│  /etc/systemd/system/allpfit-analytics.service          │
│  Runs: streamlit run src/app/dashboard.py               │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Local DB       Remote DB (Chatwoot)   OpenAI API
   (allpfit)     (178.156.206.184)      (gpt-4o)
```

### 4.2 Cron Scheduling

**Hourly ETL Execution**:
```bash
# User: isaac
# Runs at minute 2 of every hour (01:02, 02:02, 03:02, etc.)
0 * * * * cd /home/isaac/projects/allpfit-analytics && \
  /home/isaac/projects/allpfit-analytics/venv/bin/python3 \
  src/features/etl_pipeline_v3.py --triggered-by scheduler \
  >> /home/isaac/projects/allpfit-analytics/logs/etl_cron.log 2>&1
```

**Rationale**:
- 2-minute offset: Avoids race conditions at hour boundaries
- Incremental mode: Only syncs new/modified data
- ~2-5 second execution time
- Full historical backup preserved via watermark

### 4.3 Systemd Service Configuration

**Hypothetical Service Definition** (for dashboard persistence):
```ini
[Unit]
Description=AllpFit Analytics Dashboard
After=network.target

[Service]
Type=simple
User=isaac
WorkingDirectory=/home/isaac/projects/allpfit-analytics
ExecStart=/home/isaac/projects/allpfit-analytics/venv/bin/streamlit run src/app/dashboard.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Commands**:
```bash
systemctl status allpfit-analytics.service
systemctl restart allpfit-analytics.service
journalctl -u allpfit-analytics.service -f  # Live logs
```

### 4.4 Logging System

**Log Locations**:
- **ETL Logs**: `/home/isaac/projects/allpfit-analytics/logs/etl/etl_YYYYMMDD.log`
- **Cron Logs**: `/home/isaac/projects/allpfit-analytics/logs/etl_cron.log`
- **Dashboard Logs**: Via systemd journal (`journalctl`)

**Log Format**:
```
[2025-11-04 15:30:45] INFO: 🤖 ETL PIPELINE V3 - AllpFit Analytics
[2025-11-04 15:30:45] INFO: ════════════════════════════════════════
[2025-11-04 15:30:46] INFO: 🔌 Testando conexão com banco remoto...
[2025-11-04 15:30:47] INFO: ✅ Conexão bem-sucedida!
[2025-11-04 15:30:47] INFO: 📅 Watermark encontrado: 2025-11-04 15:00:00
[2025-11-04 15:30:48] INFO: 📊 Extração concluída: 25 registros em 1.23s
[2025-11-04 15:30:49] INFO: ✅ Carga UPSERT concluída!
[2025-11-04 15:30:49] INFO:    ✨ Registros inseridos: 15
[2025-11-04 15:30:49] INFO:    🔄 Registros atualizados: 10
```

**Monitoring Scripts**:
- `scripts/etl/monitor.sh` - Real-time ETL status
- `scripts/etl/status.sh` - Quick status check
- Pulls from: crontab, etl_control table, log files, database stats

---

## 5. DATABASE & STORAGE ARCHITECTURE

### 5.1 PostgreSQL Databases

**Remote (Chatwoot - Read-Only)**:
- **Host**: 178.156.206.184
- **Port**: 5432
- **Database**: chatwoot
- **User**: hetzner_dev_isaac_read (read-only)
- **Connection**: Network/TCP (slow, so we cache locally)
- **Views**: 7 modular views combining:
  - Conversations base data
  - Compiled messages (JSON)
  - CSAT ratings
  - Metrics & timestamps
  - Message statistics
  - Temporal analysis
  - **Final View**: vw_conversations_analytics_final (118 fields)

**Local (AllpFit Analytics - Read-Write)**:
- **Host**: /var/run/postgresql (Unix socket) or localhost:5432
- **Database**: allpfit
- **User**: isaac
- **Connection**: Local, fast access
- **Tables**:
  1. `conversas_analytics` (121 columns, 16 indexes)
     - Core conversation data (replicated from remote)
     - Fields: IDs, contacts, status, messages (JSONB), metrics, flags
     - Primary Key: conversation_id
     - Indexes: conversation_created_at, conversation_updated_at, contact_phone, status, etc.
  
  2. `conversas_analytics_ai` (AI analysis results)
     - Foreign Key: conversation_id → conversas_analytics
     - Fields: condicao_fisica, objetivo, probabilidade_conversao, analise_ia, sugestao_disparo
     - Timestamps: analisado_em, created_at
     - Model identifier: modelo_ia ('gpt-4o', 'rule-based', etc.)
  
  3. `etl_control` (Execution audit log)
     - execution_id (PK)
     - triggered_by (manual, scheduler, api)
     - load_type (incremental, full)
     - status (success, failed, pending)
     - watermark_start, watermark_end
     - rows_extracted, rows_inserted, rows_updated, rows_unchanged
     - duration_seconds (breakdown: extract, transform, load)
     - error_message, error_traceback
     - started_at, completed_at
  
  4. `conversas_crm_match_real` (CRM conversion tracking)
     - conversation_id, contact_phone
     - crm_customer_phone, crm_customer_name
     - match_type, match_score
     - conversation_date, crm_signup_date
     - days_to_conversion

### 5.2 Data Flow

```
Chatwoot Conversations (Remote PostgreSQL)
  ↓
  └─ Query: SELECT * FROM vw_conversations_analytics_final
     WHERE conversation_updated_at > :watermark
  ↓
ETL Extraction (2-5 seconds)
  • Extract ~20-50 rows/run
  • 118 fields per row
  ↓
Data Transformation
  • Clean NULL/NaN values
  • Format datetime fields
  • Validate required fields
  ↓
UPSERT to Local conversas_analytics
  • Check if conversation_id exists
  • If exists: UPDATE (if remote is newer)
  • If not: INSERT new
  ↓
GPT-4 Analysis (if new/updated rows > 0)
  • Batch queries unanalyzed conversations
  • Call OpenAI API (~10 seconds per 5 conversations)
  • Store results in conversas_analytics_ai
  ↓
Dashboard Query (on user request)
  • SELECT * FROM vw_leads_com_ia_analysis
  • Apply filters (name, probability, date range, etc.)
  • Return paginated results (50/page)
  ↓
Dashboard Display (Streamlit)
  • Render KPIs, charts, tables
  • Cache results (5 minute TTL)
```

### 5.3 Data Storage Locations

```
/home/tester/projetos/allpfit-analytics/
├── data/
│   ├── backups/           # CSV snapshots of ETL runs
│   ├── input/             # Upload area for base_evo.xlsx (CRM customer list)
│   └── reports/           # Generated analysis reports & crossmatch results
├── logs/
│   └── etl/               # Daily ETL execution logs (rotating)
│       ├── etl_20251104.log
│       ├── etl_20251103.log
│       └── ...
└── venv/lib/python3.11/   # Installed packages
```

---

## 6. API & ROUTES

### 6.1 Streamlit Dashboard Routes

Streamlit is a single-page application that re-runs from top to bottom on each interaction. There are no traditional REST API routes, but the application has logical "sections":

**Dashboard Routes** (URL: `analytcs.geniai.online` or `localhost:8501`):

1. **Overview Section** (Main landing):
   - Query: `get_all_conversations()`
   - Display: 6 KPI cards + daily metrics
   - Interactions: Date range filters, refresh button

2. **Charts Section**:
   - Query: `calculate_leads_by_day(df, days=30)`
   - Query: `calculate_distribution_by_period(df)`
   - Display: Plotly bar charts

3. **CRM Conversions Section** (if any):
   - Query: `get_crm_conversions_detail(engine)`
   - Display: Table of bot→CRM matches

4. **Lead Analysis Section** (Main data):
   - Query: `get_total_leads_with_ai_analysis(engine, filters=...)`
   - Query: `get_leads_with_ai_analysis(engine, limit=50, offset=offset, filters=...)`
   - Display: Paginated table with 12 columns
   - Interactions: Text filters, multiselect filters, date range, pagination, CSV download

### 6.2 External API Integrations

**OpenAI API** (REST):
- **Endpoint**: https://api.openai.com/v1/chat/completions
- **Auth**: Bearer token (OPENAI_API_KEY)
- **Method**: POST
- **Model**: gpt-4o
- **Request**:
  ```json
  {
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "..."}],
    "temperature": 0.3,
    "max_tokens": 1500,
    "response_format": {"type": "json_object"}
  }
  ```

**EVO CRM API** (REST):
- **Base URL**: https://evo-integracao-api.w12app.com.br
- **Auth**: HTTPBasicAuth (DNS, API_TOKEN)
- **Rate Limit**: 40 requests/minute
- **Endpoints**:
  - `GET /api/v2/members` - List gym members
  - `GET /api/v2/sales` - List sales/conversions

### 6.3 Database Queries (Examples)

**Get all conversations**:
```sql
SELECT * FROM conversas_analytics 
ORDER BY conversation_created_at DESC
```

**Get conversations with AI analysis**:
```sql
SELECT ca.*, cai.condicao_fisica, cai.objetivo, cai.probabilidade_conversao, 
       cai.analise_ia, cai.sugestao_disparo
FROM conversas_analytics ca
LEFT JOIN conversas_analytics_ai cai ON ca.conversation_id = cai.conversation_id
WHERE (filters applied...)
ORDER BY ca.conversation_created_at DESC
LIMIT 50 OFFSET :offset
```

**Get ETL execution history**:
```sql
SELECT * FROM etl_control 
WHERE started_at > NOW() - INTERVAL '24 hours'
ORDER BY execution_id DESC
LIMIT 5
```

---

## 7. FRONTEND/BACKEND ARCHITECTURE

### 7.1 Architecture Type

**Monolithic, Server-Rendered Web Application**

**Not**: SPA (Single Page App), Not: Microservices, Not: Decoupled Frontend/Backend

### 7.2 Technology Breakdown

**Backend**:
- **Type**: Python business logic + caching layer
- **Frameworks**: SQLAlchemy (ORM), psycopg2 (DB driver)
- **Request Handling**: Direct database queries (no REST API)
- **Concurrency**: Single-threaded; Streamlit handles request queueing
- **Caching**: 
  - `@st.cache_data(ttl=300)` for query results
  - `@st.cache_resource` for connection pool
  - Reduces database load by 80%+

**Frontend**:
- **Framework**: Streamlit (Python)
- **Rendering**: Server-side (HTML generated server-side)
- **Interactivity**: WebSocket-based (Streamlit's native approach)
- **Styling**: Custom CSS (dark theme, Tailwind-inspired)
- **Charts**: Plotly (JavaScript rendering client-side)
- **State Management**: Streamlit Session State dict

**Data Flow**:
```
User Action (button click, filter change)
    ↓
Streamlit Client (browser)
    ↓
POST request to /stream/message endpoint (WebSocket)
    ↓
Streamlit Server
    ↓
Run dashboard.py from top to bottom
    ↓
Query database (if not cached)
    ↓
Render HTML/CSS
    ↓
Send back to client
    ↓
Browser displays updated page
```

### 7.3 Deployment Model

**Server-Side Rendering (SSR)**: The entire application runs server-side. The browser is essentially a "thick client" that re-receives the entire page structure on each interaction.

**Pros**:
- Single codebase (Python only)
- Fast development
- Secure (credentials never reach browser)

**Cons**:
- Higher server load
- Slower for real-time updates
- Not suitable for high-concurrency apps (>1000 concurrent users)

### 7.4 Session Management

**Streamlit Session State**:
```python
if 'filter_nome' not in st.session_state:
    st.session_state.filter_nome = ""
if 'leads_page' not in st.session_state:
    st.session_state.leads_page = 1

# User changes filter
new_value = st.text_input("Filtro", value=st.session_state.filter_nome)
if new_value != st.session_state.filter_nome:
    st.session_state.filter_nome = new_value
    st.session_state.leads_page = 1  # Reset pagination
    st.rerun()  # Re-run the script
```

---

## 8. SECURITY & OPERATIONS

### 8.1 Security Measures

1. **Credentials Management**:
   - All credentials in `.env` (never versioned)
   - Database passwords encrypted at rest
   - API keys stored securely
   - Read-only user for remote database

2. **Network Security**:
   - Remote database: TCP connection with password auth
   - Local database: Unix socket (no network exposure)
   - Dashboard: Behind reverse proxy with HTTPS

3. **Code Security**:
   - GitHub Actions security scanning (Bandit)
   - Dependency scanning (via requirements.txt)
   - No SQL injection (using parameterized queries)
   - No hardcoded credentials

4. **Access Control**:
   - Database user permissions: Least privilege (read-only for remote)
   - Application runs as non-root (user: isaac)

### 8.2 Monitoring & Alerting

**Available Tools**:
- `scripts/etl/monitor.sh` - Real-time status dashboard
- `scripts/etl/status.sh` - Quick health check
- `journalctl` - Systemd logs
- PostgreSQL `pg_stat_activity` - Query monitoring

**Metrics Tracked**:
- ETL execution time (extract, transform, load phases)
- Rows processed (extracted, inserted, updated)
- Watermark progress (data freshness)
- Database connection count
- OpenAI API success rate & cost

### 8.3 Backup & Recovery

**ETL Control Table**: Every execution logged with results
- Allows replay of specific timeframes
- Tracks data version history

**CSV Backups**: Optional export of conversas_analytics to CSV
- Location: `data/backups/`
- Manual trigger via scripts or dashboard

**Database Backups**: External (not in codebase)
- Responsibility: DevOps/Infrastructure team

---

## 9. TESTING FRAMEWORK

### 9.1 Test Structure

**Test Directory**: `tests/`

**Test Files**:
- `test_config.py` - Configuration validation
- `test_imports.py` - Module import checks
- `test_crm.py` - CRM integration tests

**Test Framework**: pytest (7.4.0+)

**Coverage**: Configured for src/ directory
- Target: >80% coverage
- CI/CD: Upload to Codecov

### 9.2 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_imports.py -v

# Run via CI/CD
# Automatically runs on: push to main/develop/feature/*, PRs to main/develop
```

---

## 10. DEVELOPMENT & CONTRIBUTION WORKFLOW

### 10.1 Development Setup

```bash
# 1. Clone repository
git clone git@github.com:geniai-br/allpfit-analytics.git
cd allpfit-analytics

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 5. Initialize local database (if needed)
psql -U isaac -d allpfit -f sql/local_schema/01_create_schema.sql

# 6. Run dashboard locally
streamlit run src/app/dashboard.py

# 7. Run ETL manually
python src/features/etl_pipeline_v3.py --triggered-by manual
```

### 10.2 Code Style Standards

**Language**: Python 3.11+

**Formatting**:
- **Tool**: Black
- **Line Length**: 120 characters
- **Command**: `black src/`

**Linting**:
- **Tool**: Flake8
- **Max Line Length**: 120
- **Ignored**: E203 (whitespace before ':'), W503 (line break before binary operator)
- **Command**: `flake8 src/ --max-complexity=10`

**Type Checking**:
- **Tool**: mypy
- **Config**: Ignore missing imports for external packages
- **Command**: `mypy src/ --ignore-missing-imports`

**Documentation**:
- **Style**: Google-style docstrings
- **Required**: All public functions
- **Example**:
  ```python
  def extract_incremental(watermark_start=None):
      """
      Extract incremental data from remote database.
      
      Args:
          watermark_start: Timestamp to start extraction from.
      
      Returns:
          tuple: (DataFrame, watermark_end, duration_seconds)
      """
  ```

### 10.3 Git Workflow

**Branches**:
- `main` - Production code
- `develop` - Development/staging
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches

**Commits**:
- Follow Conventional Commits
- Format: `<type>: <description>`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Example: `feat: Add GPT-4 analysis to ETL pipeline`

**Pull Requests**:
1. Create branch from `develop`
2. Make changes
3. Pass CI checks (lint, format, test, security)
4. Create PR to `develop`
5. Code review
6. Merge to `develop`
7. Eventually merge `develop` → `main` for release

---

## 11. QUICK REFERENCE & TROUBLESHOOTING

### Common Commands

```bash
# Start dashboard
streamlit run src/app/dashboard.py

# Run ETL manually
python src/features/etl_pipeline_v3.py --triggered-by manual

# Run ETL with full reload
python src/features/etl_pipeline_v3.py --full --triggered-by manual

# Run AI analysis manually
python scripts/analysis/run_gpt4.py --limit 10

# Monitor ETL status
bash scripts/etl/monitor.sh

# Check last 5 ETL executions
psql -U isaac -d allpfit -c "SELECT * FROM etl_control ORDER BY id DESC LIMIT 5;"

# View ETL logs
tail -f /home/isaac/projects/allpfit-analytics/logs/etl/etl_$(date +%Y%m%d).log

# Restart dashboard service
systemctl restart allpfit-analytics.service
```

### Troubleshooting Matrix

| Issue | Cause | Solution |
|-------|-------|----------|
| Dashboard won't start | Port 8501 in use | `lsof -i :8501`, kill process |
| ETL connection fails | Remote DB unreachable | Check IP/credentials in .env, ping host |
| GPT-4 analysis fails | API key expired/invalid | Check OPENAI_API_KEY in .env |
| Slow queries | Missing indexes | Run SQL schema creation script |
| Dashboard slow | Cache expired, many filters | Clear cache: `st.cache_data.clear()` |

---

## 12. PERFORMANCE & SCALABILITY

### Current Performance Metrics

- **ETL Incremental Load**: 2-5 seconds
- **ETL Full Load**: ~30-60 seconds
- **GPT-4 Analysis**: ~8-12 seconds per conversation
- **Dashboard Load Time**: 1-3 seconds (cached)
- **Query Response**: <500ms for most dashboard queries
- **Database Size**: ~100MB (506 conversations)
- **Concurrent Users**: Single instance supports ~10 concurrent
- **Data Freshness**: 1 hour (cron interval)

### Scalability Bottlenecks

1. **Single Streamlit Instance**: Can't handle >100 concurrent users
   - Solution: Load balancer + multiple instances + Redis caching

2. **OpenAI API Rate Limits**: 40,000 tokens/minute (tier 1)
   - Solution: Queue system + batch processing

3. **Database Connections**: Connection pool exhaustion
   - Solution: Connection pooling (SQLAlchemy already does this)

4. **Large Batch Operations**: UPSERT becomes slow at >10,000 rows
   - Solution: Batch processing in chunks of 1,000

---

## FINAL SUMMARY TABLE

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.11+ |
| **Framework** | Streamlit (web UI) + SQLAlchemy (ORM) |
| **Databases** | PostgreSQL (remote source + local replica) |
| **AI Integration** | OpenAI GPT-4o |
| **Deployment** | Linux server with cron + systemd |
| **Architecture** | Monolithic, server-side rendering |
| **Frontend/Backend** | Unified in Python (Streamlit) |
| **Authentication** | Database credentials + API tokens |
| **Logging** | File-based, structured logs |
| **Testing** | pytest + CI/CD via GitHub Actions |
| **Version** | 1.2.0 |
| **Status** | Production-ready |
| **Team** | GenIAI (https://github.com/geniai-br/) |

---

**Last Updated**: November 4, 2025
**Explored By**: Claude Code
