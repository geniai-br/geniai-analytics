# AllpFit Analytics - Exploration Index

This document serves as an index to the comprehensive exploration of the AllpFit Analytics application.

## Primary Documentation

- **[ALLPFIT_COMPREHENSIVE_SUMMARY.md](./ALLPFIT_COMPREHENSIVE_SUMMARY.md)** - Complete technical overview (1134 lines)
  - Project structure and technology stack
  - Implementation details and core functionality  
  - Configuration files and setup
  - Deployment setup and architecture
  - Database and storage
  - APIs and routes
  - Frontend/Backend architecture
  - Security and operations
  - Testing framework
  - Development workflow

## Quick Navigation

### 1. Project Structure & Technology Stack
- **Section 1** in comprehensive summary
- **Tech Stack**: Python 3.11 + Streamlit + PostgreSQL + GPT-4o
- **Directory Structure**: Complete file tree with descriptions
- **Entry Points**: Dashboard, ETL Pipeline, GPT-4 Analysis, CRM Crossmatch

### 2. Core Implementation

#### ETL Pipeline V3 (Extract-Transform-Load)
- **Purpose**: Hourly synchronization of Chatwoot data to local PostgreSQL
- **Performance**: 2-5 seconds for incremental loads
- **Architecture**: 5 phases (Extract → Transform → Load → Watermark → AI Analysis)
- **Key Files**:
  - `/home/tester/projetos/allpfit-analytics/src/features/etl_pipeline_v3.py` (286 lines)
  - `/home/tester/projetos/allpfit-analytics/src/features/etl/extractor.py` (172 lines)
  - `/home/tester/projetos/allpfit-analytics/src/features/etl/loader.py` (234 lines)
  - `/home/tester/projetos/allpfit-analytics/src/features/etl/watermark_manager.py` (222 lines)

#### Dashboard (Streamlit Web UI)
- **URL**: https://analytcs.geniai.online (production) or localhost:8501
- **Features**: 6 KPI cards, daily metrics, charts, CRM tracking, lead analysis
- **Key Files**:
  - `/home/tester/projetos/allpfit-analytics/src/app/dashboard.py` (800+ lines)
  - `/home/tester/projetos/allpfit-analytics/src/app/config.py` (theme & styling)
  - `/home/tester/projetos/allpfit-analytics/src/app/utils/db_connector.py` (DB access)
  - `/home/tester/projetos/allpfit-analytics/src/app/utils/metrics.py` (KPI calculations)

#### GPT-4 AI Analysis Engine
- **Purpose**: Extract lead intent, objections, conversion probability
- **Model**: OpenAI gpt-4o with temperature 0.3
- **Output**: JSON with analysis, probability (0-5 scale), recommendations
- **Key Files**:
  - `/home/tester/projetos/allpfit-analytics/src/features/analyzers/gpt4.py`

#### CRM Integration
- **Purpose**: Track bot→CRM conversions via phone matching
- **Integrations**: EVO CRM API, Excel crossmatch
- **Key Files**:
  - `/home/tester/projetos/allpfit-analytics/src/integrations/evo_crm.py`
  - `/home/tester/projetos/allpfit-analytics/src/features/crm/crossmatch.py`

### 3. Configuration & Deployment

#### Environment Setup (.env)
- **Location**: `/home/tester/projetos/allpfit-analytics/.env` (runtime)
- **Template**: `/home/tester/projetos/allpfit-analytics/.env.example` (reference)
- **Sections**: Remote DB, Local DB, OpenAI, General config

#### Dependencies
- **Production**: `/home/tester/projetos/allpfit-analytics/requirements.txt` (11 packages)
- **Development**: `/home/tester/projetos/allpfit-analytics/requirements-dev.txt` (5 packages)
- **Build Config**: `/home/tester/projetos/allpfit-analytics/pyproject.toml` (setuptools)

#### Deployment
- **CI/CD**: `/home/tester/projetos/allpfit-analytics/.github/workflows/ci.yml`
- **Cron Schedule**: Hourly ETL at XX:02 (user: isaac)
- **Systemd Service**: allpfit-analytics.service (dashboard)
- **Logging**: Daily ETL logs in `/logs/etl/`

### 4. Database Architecture

#### Remote (Chatwoot)
- **Host**: 178.156.206.184:5432
- **Database**: chatwoot
- **User**: hetzner_dev_isaac_read (read-only)
- **Main View**: vw_conversations_analytics_final (118 fields)

#### Local (AllpFit)
- **Host**: localhost:5432 (or /var/run/postgresql via Unix socket)
- **Database**: allpfit
- **User**: isaac
- **Main Tables**:
  - `conversas_analytics` (121 columns, conversation data)
  - `conversas_analytics_ai` (AI analysis results)
  - `etl_control` (execution audit log)
  - `conversas_crm_match_real` (CRM conversions)

#### SQL Files
- **Local Schema**: `/home/tester/projetos/allpfit-analytics/sql/local_schema/`
- **Remote Views**: `/home/tester/projetos/allpfit-analytics/sql/modular_views/`

### 5. API & Routes

#### Dashboard Routes (Streamlit)
- Single-page app, re-renders on interaction
- **Sections**: Overview, Charts, CRM Conversions, Lead Analysis
- No traditional REST API routes

#### External APIs
- **OpenAI**: https://api.openai.com/v1/chat/completions (GPT-4o)
- **EVO CRM**: https://evo-integracao-api.w12app.com.br (members, sales endpoints)

### 6. Frontend/Backend Architecture

- **Type**: Monolithic, server-side rendered (SSR)
- **Backend**: Python business logic + SQLAlchemy ORM
- **Frontend**: Streamlit (Python), custom CSS, Plotly charts
- **Concurrency**: Single-threaded with WebSocket-based updates
- **Caching**: 5-minute TTL for query results

### 7. Security & Operations

#### Security Measures
- Credentials in .env (never versioned)
- Read-only user for remote DB
- API keys stored securely
- No SQL injection (parameterized queries)
- GitHub Actions security scanning (Bandit)

#### Monitoring Tools
- `scripts/etl/monitor.sh` - Real-time status
- `scripts/etl/status.sh` - Quick health check
- `journalctl` - Systemd service logs
- ETL control table for audit trail

### 8. Testing & Development

#### Test Structure
- **Framework**: pytest 7.4.0+
- **Test Files**:
  - `tests/test_config.py` - Config validation
  - `tests/test_imports.py` - Module imports
  - `tests/test_crm.py` - CRM integration
- **Coverage**: Configured for src/ directory
- **CI/CD**: Automatic on push/PR to main/develop

#### Code Standards
- **Formatter**: Black (120 char line length)
- **Linter**: Flake8 (max-complexity 10)
- **Type Checker**: mypy (Python 3.11)
- **Docstrings**: Google-style

#### Git Workflow
- **Branches**: main, develop, feature/*, bugfix/*
- **Commits**: Conventional Commits format
- **PR Process**: Code review, CI checks, merge to develop

## File Locations Summary

```
/home/tester/projetos/allpfit-analytics/
├── src/                          Main source code
│   ├── app/                      Dashboard (Streamlit)
│   ├── features/                 Core logic (ETL, analyzers, CRM)
│   ├── integrations/             External APIs
│   └── shared/                   Shared utilities
├── sql/                          Database schemas & views
├── scripts/                      Automation & operational scripts
├── tests/                        Test suite
├── data/                         Data artifacts (backups, reports)
├── docs/                         Documentation (420+ lines total)
├── .github/workflows/            CI/CD configuration
├── pyproject.toml                Build configuration
├── requirements.txt              Production dependencies
├── .env                          Runtime configuration
├── .env.example                  Configuration template
└── README.md                     Main documentation
```

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~3,000+ |
| Main Application | 800 lines (dashboard.py) |
| ETL Pipeline | 286 lines (orchestrator) |
| ETL Modules | 748 lines combined (extract, transform, load, watermark) |
| Documentation | 1134+ lines (this summary) |
| Database Columns | 121 (local), 118 (remote view) |
| Database Indexes | 16 (local) |
| KPIs Mapped | 60+ across 6 dimensions |
| Conversations Tracked | 506+ |
| External APIs | 2 (OpenAI, EVO CRM) |
| Deployment Schedule | Hourly (cron) |
| Version | 1.2.0 |

## Performance Metrics

| Operation | Duration |
|-----------|----------|
| ETL Incremental Load | 2-5 seconds |
| ETL Full Load | 30-60 seconds |
| GPT-4 Analysis | 8-12 seconds per conversation |
| Dashboard Load | 1-3 seconds (cached) |
| Query Response | <500ms (most queries) |

## Important Paths

### Configuration Files
- `.env` - Runtime secrets (not versioned)
- `.env.example` - Configuration template
- `pyproject.toml` - Project metadata & build config
- `requirements.txt` - Dependencies
- `.github/workflows/ci.yml` - CI/CD pipeline

### Source Code
- `src/app/dashboard.py` - Main dashboard (800+ lines)
- `src/features/etl_pipeline_v3.py` - ETL orchestrator
- `src/shared/config.py` - Configuration management
- `src/shared/database.py` - DB connection manager

### Database
- `sql/local_schema/` - Local database schema (SQL)
- `sql/modular_views/` - Remote database views (SQL)

### Deployment & Operations
- `scripts/etl/run_manual.sh` - Manual ETL execution
- `scripts/etl/monitor.sh` - Real-time monitoring
- `scripts/etl/status.sh` - Status check
- `scripts/analysis/run_gpt4.py` - Manual GPT-4 trigger

### Documentation
- `README.md` - Main documentation (408 lines)
- `docs/ETL_V3_README.md` - ETL documentation (420 lines)
- `docs/CONTEXT.md` - Project context & quick reference
- `docs/schema_explicacao.md` - Database schema explanation

## Quick Commands

```bash
# Start development
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Run dashboard
streamlit run src/app/dashboard.py

# Run ETL manually
python src/features/etl_pipeline_v3.py --triggered-by manual

# Monitor ETL
bash scripts/etl/monitor.sh

# Run tests
pytest tests/ -v --cov=src

# Code quality checks
black src/ && flake8 src/ && mypy src/
```

## Troubleshooting Quick Links

See comprehensive summary Section 11 for:
- Common commands
- Dashboard issues
- ETL failures
- GPT-4 problems
- Database slowness
- Performance troubleshooting

## Architecture Diagrams

### System Architecture
See Section 4.1 of comprehensive summary for deployment diagram.

### Data Flow
See Section 5.2 of comprehensive summary for ETL data flow diagram.

### ETL Pipeline
See Section 2.1 of comprehensive summary for 5-phase pipeline diagram.

---

**Created**: November 4, 2025
**Exploration Type**: Comprehensive
**Status**: Complete
**Document**: ALLPFIT_COMPREHENSIVE_SUMMARY.md (1134 lines)
