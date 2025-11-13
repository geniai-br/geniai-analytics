# Documentação do Projeto GeniAI Analytics

## 📁 Estrutura de Documentação

```
docs/
├── public/              # ✅ Documentação pública (commitada no Git)
│   ├── architecture/    # Decisões arquiteturais (ADRs)
│   ├── guides/          # Guias de uso e setup
│   └── api/             # Documentação de API
│
├── private/             # ❌ Documentação privada (NÃO commitada)
│   ├── checkpoints/     # Estados do projeto, cronogramas
│   ├── prompts/         # Prompts Claude, conversas
│   └── sensitive/       # Informações sensíveis
│
└── multi-tenant/        # Documentação do sistema multi-tenant
```

## 🔐 Documentação Privada

A pasta `private/` contém informações internas e sensíveis que **NÃO devem ser compartilhadas publicamente**:

- **Checkpoints**: Progresso do projeto, cronogramas internos
- **Prompts**: Conversas com Claude durante implementação
- **Sensitive**: Chaves de API, credenciais (mesmo que de exemplo)

**Esta pasta é ignorada pelo Git** através do `.gitignore`.

## 📚 Documentação Pública

### Architecture
- [ADR-001](architecture/adr/ADR-001-arquitetura-multitenant-rls.md) - Arquitetura Multi-tenant com RLS
- [ADR-002](architecture/adr/ADR-002-etl-pipeline-incremental.md) - ETL Pipeline Incremental
- [ADR-003](architecture/adr/ADR-003-timescaledb-time-series.md) - TimescaleDB para Séries Temporais
- [ADR-004](architecture/adr/ADR-004-streamlit-dashboard-framework.md) - Streamlit Dashboard Framework
- [ADR-005](architecture/adr/ADR-005-openai-conversation-analysis.md) - OpenAI Conversation Analysis

### Multi-Tenant
- [DB Documentation](multi-tenant/DB_DOCUMENTATION.md) - Documentação completa do banco de dados
- [Remote Database](multi-tenant/REMOTE_DATABASE.md) - Configuração do banco remoto
- [Users Guide](multi-tenant/README_USUARIOS.md) - Guia de usuários

## 🔍 Onde Encontrar

- **Setup do Projeto**: Ver [README.md](../README.md) na raiz
- **Arquitetura**: Ver [architecture/](architecture/)
- **Multi-Tenant**: Ver [multi-tenant/](multi-tenant/)
- **SQL Scripts**: Ver [../sql/](../sql/)