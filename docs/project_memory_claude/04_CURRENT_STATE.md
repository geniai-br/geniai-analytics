# 📊 Estado Atual do Sistema - AllpFit Analytics

**Data:** 23/10/2025
**Status:** ✅ Em Produção

---

## 🏗️ Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────┐
│                     CHATWOOT (Remoto)                       │
│           Host: 178.156.206.184                             │
│           Database: chatwoot                                 │
│           View: v_conversas_com_mensagens                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ETL v3 (Incremental)
                     │ Roda: A cada hora (cron)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│               POSTGRESQL LOCAL (allpfit)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │ conversas_analytics (495 registros)               │      │
│  │ - Dados agregados de conversas                    │      │
│  │ - Métricas calculadas                             │      │
│  │ - Message compiled (JSONB)                        │      │
│  └──────────────────────────────────────────────────┘      │
│                     │                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │ conversas_analytics_ai (482 análises)            │      │
│  │ - Análise rule-based (score 1-5)                 │      │
│  │ - Sugestões de disparo                            │      │
│  └──────────────────────────────────────────────────┘      │
│                     │                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │ conversas_crm_match_real (7 conversões)          │      │
│  │ - Leads do bot → Clientes CRM                     │      │
│  │ - Rastreamento de origem                          │      │
│  └──────────────────────────────────────────────────┘      │
│                     │                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │ etl_control (9 execuções)                         │      │
│  │ - Histórico de execuções ETL                      │      │
│  │ - Watermark para incremental                      │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Streamlit
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                DASHBOARD (Porta 8501)                        │
│           https://analytcs.geniai.online                     │
│                                                              │
│  - KPIs principais (6 métricas)                             │
│  - Métricas diárias (6 métricas)                            │
│  - Gráficos (2)                                              │
│  - Conversões rastreadas (7)                                │
│  - Leads com análise IA (Top 50)                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Dados Atuais (23/10/2025)

### Conversas
- **Total:** 495 conversas
- **Com análise IA:** 482
- **Hoje:** 2 conversas

### Conversões
- **Rastreadas:** 7 (3.5%)
- **Total CRM:** 198 clientes
- **Tempo médio:** 6.7 dias

### Visitas
- **Agendadas:** 42 visitas
- **Taxa:** 8.5% dos leads

### ETL
- **Última exec:** 23/10 11:01 (SP)
- **Próxima:** 12:00
- **Status:** ✅ Rodando

---

## 🔧 Serviços Ativos

### 1. ETL (Cron)
```bash
# Agendamento
0 * * * * cd /home/isaac/projects/allpfit-analytics && python3 src/features/etl_pipeline_v3.py --triggered-by scheduler

# Status
./monitor_etl.sh
```

### 2. Dashboard (Streamlit)
```bash
# Processo
streamlit run src/app/dashboard.py --server.port 8501 --server.headless true

# Status
curl -I http://localhost:8501

# Restart
pkill -f "streamlit run" && cd /home/isaac/projects/allpfit-analytics && source venv/bin/activate && streamlit run src/app/dashboard.py --server.port 8501 --server.headless true &
```

---

## 📁 Estrutura de Arquivos

```
allpfit-analytics/
├── src/
│   ├── app/                    # Dashboard Streamlit
│   │   ├── dashboard.py        # ✅ Main dashboard
│   │   ├── config.py           # ✅ Configurações/temas
│   │   └── utils/
│   │       ├── db_connector.py # ✅ Conexão DB
│   │       └── metrics.py      # ✅ Cálculo de KPIs
│   │
│   ├── features/               # ETL e Análises
│   │   ├── etl_pipeline_v3.py  # ✅ ETL principal
│   │   ├── etl/                # ✅ Módulos ETL
│   │   │   ├── extractor.py
│   │   │   ├── transformer.py
│   │   │   ├── loader.py
│   │   │   ├── logger.py
│   │   │   └── watermark_manager.py
│   │   ├── rule_based_analyzer.py       # ✅ Análise IA
│   │   └── rule_based_initial_load.py   # ✅ Carga inicial IA
│   │
│   ├── integrations/           # Integrações externas
│   │   └── evo_crm.py          # ✅ Cliente EVO CRM
│   │
│   └── shared/                 # Compartilhado
│       ├── config.py
│       └── database.py
│
├── docs/                       # Documentação
│   ├── project_memory_claude/  # ✅ Memória Claude
│   ├── archive/                # Docs arquivadas
│   └── *.md                    # Vários docs
│
├── scripts/                    # Scripts utilitários
│   ├── restart_dashboard.sh
│   └── run_etl_manual.sh
│
├── logs/                       # Logs
│   ├── etl/                    # Logs ETL por dia
│   └── etl_cron.log            # Log do cron
│
├── crossmatch_excel_crm.py     # ✅ Script crossmatch
├── monitor_etl.sh              # ✅ Monitor ETL
├── etl_status.sh               # ✅ Status rápido
├── CONTEXTO_PROJETO.md         # ✅ Contexto geral
├── MONITORAMENTO_ETL.md        # ✅ Doc monitoramento
└── README.md                   # ✅ README
```

---

## 🔐 Credenciais e Configurações

### PostgreSQL Local
```
Host: localhost
Port: 5432
Database: allpfit
User: isaac
Password: AllpFit2024@Analytics
```

### PostgreSQL Remoto (Chatwoot)
```
Host: 178.156.206.184
Database: chatwoot
User: hetzner_dev_isaac_read
Password: [ver .env ou código]
```

### EVO CRM API
```
Base URL: https://evo-integracao-api.w12app.com.br
DNS: allpfit
Token: AF61C223-2C8D-4619-94E3-0A5A37D1CD8D
Rate Limit: 40 req/min
```

---

## 🎯 KPIs do Dashboard

### Principais (Seção 1)
1. **Total Contatos:** 495 leads
2. **Agente AI:** 100% conversas bot
3. **Humano:** Conversas com intervenção
4. **Visitas:** 42 agendadas (8.5%)
5. **Vendas/Tráfego:** 7 conversões (3.5%)
6. **Vendas/Geral:** 198 clientes CRM

### Diárias (Seção 2)
1. **Novos Leads:** Primeiro contato hoje
2. **Visitas Dia:** Agendadas para hoje
3. **Vendas Dia:** Conversões hoje
4. **Total Conversas:** Novas + reabertas
5. **Novas:** Iniciadas hoje
6. **Reabertas:** Retornaram hoje

### Gráficos (Seção 3)
1. **Média Leads:** Últimos 30 dias
2. **Distribuição:** Por período do dia

### Conversões (Seção 4)
- Tabela com 7 conversões rastreadas
- Nome (Bot), Nome (CRM), Telefone, Origem
- Datas, Dias para converter, Mensagens

### Leads IA (Seção 5)
- Top 50 leads com score 1-5
- Análise detalhada em 3 tópicos
- Sugestão de disparo

---

## ⚙️ Funcionalidades Implementadas

### ✅ ETL Incremental
- Roda a cada hora (cron)
- Sincroniza apenas novos/modificados
- Watermark automático
- Auditoria completa (etl_control)
- Logs por dia

### ✅ Análise de IA (Rule-Based)
- Score 0-10+ baseado em comportamento
- 3 tópicos: Sinais, Balanço, Recomendação
- Priorização automática (1-5)
- 482 conversas analisadas

### ✅ Rastreamento de Conversões
- Crossmatch Excel CRM ↔ Bot
- Normalização inteligente de telefone
- Validação temporal (antes/depois)
- 7 conversões identificadas (3.5%)

### ✅ Dashboard Interativo
- Filtros por data
- Métricas em tempo real
- Gráficos interativos
- Tooltips explicativos
- Contador de dias rodando

### ✅ Monitoramento
- Script completo (monitor_etl.sh)
- Status rápido (etl_status.sh)
- Logs estruturados
- Alertas de erro

---

## 🚨 Pontos de Atenção

### 1. Timezone
- **Banco:** UTC
- **Display:** SP (UTC-3)
- **Conversão:** `started_at - INTERVAL '3 hours'`

### 2. Telefones
- **Normalização:** Remove DDI/DDD, gera 2 versões
- **Match:** Com e sem 9º dígito
- **Formato completo:** +558393255303

### 3. Arquivos Ignorados
- Excel: `base_evo.xlsx`, `leads_contatos.xlsx`
- Relatórios: `relatorio_conversoes_*.txt`
- Logs: `*.log`

### 4. Cron
- **Importante:** `cd` antes de executar python
- **Log:** Verificar `/logs/etl_cron.log`
- **Falha silenciosa:** Verificar `crontab -l`

---

## 📊 Performance

### ETL
- **Tempo médio:** 0.4-0.5 segundos
- **Extração:** ~0.3s
- **Transform:** ~0.01s
- **Load:** ~0.03s

### Dashboard
- **Load time:** ~2-3 segundos
- **Queries:** Otimizadas com índices
- **Cache:** Streamlit cache habilitado

---

## 🔗 URLs Importantes

- **Dashboard:** https://analytcs.geniai.online
- **Local:** http://localhost:8501
- **Docs EVO:** https://evo-abc.readme.io/reference

---

**Status Geral:** ✅ **SISTEMA FUNCIONANDO PERFEITAMENTE**

**Última verificação:** 23/10/2025 11:30
