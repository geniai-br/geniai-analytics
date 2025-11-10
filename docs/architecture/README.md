# Documentação de Arquitetura - AllpFit Analytics

> Documentação completa da arquitetura do sistema AllpFit Analytics
> Gerado em: 2025-11-10

---

## Visão Geral

O **AllpFit Analytics** é uma plataforma multi-tenant de analytics para análise de conversas do Chatwoot, com foco em geração de leads e insights baseados em IA. O sistema utiliza PostgreSQL com Row-Level Security (RLS), ETL incremental, dashboards Streamlit e integração com OpenAI GPT-4.

### Stack Tecnológico

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| **Backend** | Python | 3.11+ |
| **Banco de Dados** | PostgreSQL | 15 |
| **Time-Series** | TimescaleDB | 2.11+ (planejado) |
| **Dashboard** | Streamlit | 1.28+ |
| **Visualização** | Plotly | 5.17+ |
| **ETL** | Pandas + psycopg2 | 2.0+ |
| **IA** | OpenAI GPT-4 | API v1 |
| **Proxy** | Nginx | 1.18+ |
| **Autenticação** | bcrypt + PostgreSQL | - |

---

## Diagramas C4 Model

A documentação segue o [C4 Model](https://c4model.com/) para representar a arquitetura em diferentes níveis de abstração.

### Nível 1: Contexto do Sistema

**Arquivo:** [`diagrams/c4-level1-context.puml`](./diagrams/c4-level1-context.puml)

Visão de alto nível mostrando:
- Usuários (Admin GeniAI, Admin Cliente, Visualizador)
- Sistema AllpFit Analytics
- Sistemas externos (Chatwoot, OpenAI, EVO CRM)

```bash
# Gerar diagrama PNG (requer PlantUML)
plantuml docs/architecture/diagrams/c4-level1-context.puml
```

### Nível 2: Containers

**Arquivo:** [`diagrams/c4-level2-container.puml`](./diagrams/c4-level2-container.puml)

Mostra os containers principais:
- Nginx Reverse Proxy
- Streamlit Dashboard
- FastAPI Backend (planejado)
- ETL Pipeline V3
- Módulo de Autenticação
- PostgreSQL Local + TimescaleDB
- Sistemas externos

### Nível 3: Componentes

**Arquivo:** [`diagrams/c4-level3-component.puml`](./diagrams/c4-level3-component.puml)

Detalha os componentes internos:
- **ETL:** Extractor, Transformer, Loader, Watermark Manager
- **Dashboard:** Login, Admin Panel, Client Dashboard, Metrics Calculator
- **Auth:** Auth Core, Middleware, RLS Manager
- **Analyzers:** Rule-Based, GPT-4, CRM Crossmatch

---

## Diagramas de Fluxo

### Fluxo de Dados ETL

**Arquivo:** [`diagrams/etl-data-flow.puml`](./diagrams/etl-data-flow.puml)

Diagrama de sequência mostrando:
1. Inicialização (watermark, auditoria)
2. Extract (query incremental)
3. Transform (validação, limpeza)
4. Load (UPSERT em batches)
5. Finalização (atualização de watermark)

**Performance:**
- Incremental: 2-5 segundos
- Full load: 2-3 minutos

### Fluxo de Autenticação Multi-Tenant

**Arquivo:** [`diagrams/auth-flow-multitenant.puml`](./diagrams/auth-flow-multitenant.puml)

Diagrama de sequência mostrando:
1. Login com validação de credenciais (bcrypt)
2. Criação de sessão (UUID, expiração 24h)
3. Validação de sessão em cada request
4. Configuração de contexto RLS (SET LOCAL app.current_tenant_id)
5. Query com RLS automático
6. Logout

### Esquema de Banco com RLS

**Arquivo:** [`diagrams/database-schema-rls.puml`](./diagrams/database-schema-rls.puml)

Diagrama de entidades mostrando:
- Tabelas core (tenants, users, sessions)
- Tabelas de analytics (conversations_analytics, gpt_analysis)
- Tabelas de controle (etl_control, inbox_tenant_mapping)
- Políticas RLS aplicadas
- Relacionamentos e índices

---

## Architecture Decision Records (ADRs)

Os ADRs documentam decisões arquiteturais importantes, incluindo contexto, alternativas consideradas, decisão tomada e consequências.

### ADR-001: Arquitetura Multi-Tenant com RLS

**Arquivo:** [`adr/ADR-001-arquitetura-multitenant-rls.md`](./adr/ADR-001-arquitetura-multitenant-rls.md)

**Decisão:** Usar Row-Level Security do PostgreSQL para isolamento de dados por tenant.

**Razões:**
- Segurança enforced no banco (não na aplicação)
- Performance nativa do PostgreSQL
- Transparência para queries (filtro automático)
- Uma única instância de código e banco

**Alternativas Rejeitadas:**
- Banco separado por tenant (custo operacional)
- Schema separado por tenant (complexidade)
- Filtro na aplicação (risco de vazamento)

**Status:** ✅ Implementado

---

### ADR-002: Pipeline ETL V3 Incremental com Watermark

**Arquivo:** [`adr/ADR-002-etl-pipeline-incremental.md`](./adr/ADR-002-etl-pipeline-incremental.md)

**Decisão:** Usar ETL incremental baseado em watermark (timestamp) com UPSERT.

**Razões:**
- Performance: 2-5s (incremental) vs 2-3min (full load)
- Captura atualizações em conversas antigas
- Não requer permissões especiais no banco remoto
- Auditoria completa via tabela `etl_control`

**Componentes:**
- Watermark Manager (controle de sincronização)
- Extractor (query incremental com LIMIT)
- Transformer (validação de 118 campos)
- Loader (UPSERT em batches de 1000)

**Status:** ✅ Implementado

---

### ADR-003: TimescaleDB para Séries Temporais

**Arquivo:** [`adr/ADR-003-timescaledb-time-series.md`](./adr/ADR-003-timescaledb-time-series.md)

**Decisão:** Usar TimescaleDB (extensão PostgreSQL) para otimizar queries temporais.

**Razões:**
- Performance 10-20x melhor em queries temporais
- Compressão automática (economia de 90% de espaço)
- Particionamento automático (chunks de 7 dias)
- Continuous Aggregates (views materializadas auto-refresh)
- 100% compatível com PostgreSQL + RLS

**Benefícios Esperados:**
- Query de KPIs: 850ms → 45ms
- Armazenamento: 10GB → 1GB
- Manutenção: Zero (particionamento automático)

**Status:** 🔄 Planejado para Q1 2026

---

### ADR-004: Streamlit como Framework de Dashboard

**Arquivo:** [`adr/ADR-004-streamlit-dashboard-framework.md`](./adr/ADR-004-streamlit-dashboard-framework.md)

**Decisão:** Usar Streamlit para desenvolvimento rápido de dashboards interativos.

**Razões:**
- Time-to-market: Dashboard em 2-3 dias (vs 2-3 meses com React)
- Python puro (equipe não precisa aprender JavaScript)
- 40+ componentes prontos (metrics, charts, tables)
- Cache inteligente (@st.cache_data)
- Deployment simples (sem npm/webpack)

**Trade-offs:**
- Menos flexível que React (layout, animações)
- Performance limitada para 1000+ usuários (mitigação: Nginx cache)

**Status:** ✅ Implementado

---

### ADR-005: OpenAI GPT-4 para Análise de Conversas

**Arquivo:** [`adr/ADR-005-openai-conversation-analysis.md`](./adr/ADR-005-openai-conversation-analysis.md)

**Decisão:** Usar OpenAI GPT-4 em modo híbrido (rule-based pre-filter + GPT-4 seletivo).

**Razões:**
- Alta precisão (85-90% vs 60-70% rule-based)
- Entende contexto, gírias, português BR
- Zero setup de ML (não precisa treinar modelo)
- ROI positivo (+15% leads identificados)

**Estratégia de Custo:**
- Análise seletiva: Apenas conversas high-priority
- Modelo: GPT-4o-mini para casos simples (10x mais barato)
- Batch processing: Análise noturna (off-peak)
- Custo estimado: $330/mês (análise incremental)

**Status:** ✅ Implementado (modo manual), 🔄 Batch automático planejado

---

## Como Usar Esta Documentação

### Para Desenvolvedores

1. **Entender a Arquitetura:**
   - Comece com o diagrama de contexto (C4 Level 1)
   - Aprofunde nos containers (C4 Level 2)
   - Veja os componentes (C4 Level 3)

2. **Implementar Features:**
   - Consulte os ADRs para entender decisões
   - Use os diagramas de fluxo como referência
   - Siga os padrões estabelecidos

3. **Troubleshooting:**
   - Veja o fluxo de autenticação para problemas de RLS
   - Consulte o fluxo ETL para problemas de sincronização
   - Use queries de monitoramento nos ADRs

### Para Arquitetos

1. **Revisar Decisões:**
   - Leia os ADRs para entender trade-offs
   - Valide se decisões ainda são adequadas
   - Proponha mudanças via novos ADRs

2. **Planejar Evolução:**
   - Identifique limitações arquiteturais
   - Considere alternativas futuras
   - Documente novas decisões

### Para Product Managers

1. **Entender Capacidades:**
   - Veja o que o sistema faz (C4 Context)
   - Entenda limitações técnicas (ADRs)
   - Planeje features realistas

2. **Estimar Custos:**
   - Consulte ADR-005 para custos de IA
   - Consulte ADR-003 para custos de infra
   - Considere trade-offs de performance

---

## Ferramentas Necessárias

### Visualizar Diagramas PlantUML

#### Opção 1: PlantUML CLI
```bash
# Instalar PlantUML
sudo apt install plantuml

# Gerar PNG de todos os diagramas
cd docs/architecture/diagrams
plantuml *.puml
```

#### Opção 2: VS Code Extension
```bash
# Instalar extensão PlantUML
code --install-extension jebbs.plantuml

# Abrir arquivo .puml e usar Ctrl+Shift+P → "PlantUML: Preview Current Diagram"
```

#### Opção 3: Online
- [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
- Copiar/colar conteúdo do arquivo .puml

---

## Manutenção da Documentação

### Quando Atualizar

1. **Mudanças Arquiteturais Significativas:**
   - Novo container/componente
   - Mudança de tecnologia
   - Nova integração externa

2. **Novas Decisões:**
   - Criar novo ADR (ADR-006, ADR-007, etc.)
   - Seguir template dos ADRs existentes

3. **Mudanças em Fluxos:**
   - Atualizar diagramas de sequência
   - Re-gerar PNGs

### Processo de Revisão

1. **Mensal:** Revisar se documentação está atualizada
2. **Trimestral:** Revisar ADRs (seção "Notas de Revisão")
3. **Anual:** Arquitetura review completa

---

## Histórico de Versões

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2025-11-10 | Claude Code + Isaac | Documentação inicial completa |
| | | | - 7 diagramas C4/UML |
| | | | - 5 ADRs |
| | | | - README de navegação |

---

## Contato

**Mantido por:** Isaac (GenIAI)
**Revisores:** Equipe GenIAI
**Dúvidas:** Abrir issue no repositório

---

## Licença

Esta documentação está sob a mesma licença do projeto AllpFit Analytics (MIT License).

Copyright © 2025 GenIAI
