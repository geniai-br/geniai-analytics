# ADR-004: Streamlit como Framework de Dashboard

**Status:** Aceito
**Data:** 2025-11-03
**Decisores:** Equipe GenIAI
**Contexto Técnico:** Python 3.11, Streamlit 1.28+, Plotly 5.17+

---

## Contexto e Problema

O sistema AllpFit Analytics precisa de uma interface web para visualização de dados:

### Requisitos
1. **Interatividade:** Filtros dinâmicos, drill-down, atualização em tempo real
2. **Visualizações:** 60+ KPIs, gráficos (barras, linhas, pizza, heatmaps)
3. **Multi-Tenant:** Suportar login, RLS, painel admin vs cliente
4. **Time-to-Market:** Desenvolvimento rápido (semanas, não meses)
5. **Python-First:** Equipe proficiente em Python, não em JS/React
6. **Customização:** Tema dark, branding por tenant
7. **Deployment:** Simples, sem necessidade de Node.js/npm

### Personas
- **Admin GeniAI:** Visualiza todos os clientes, gerencia configurações
- **Admin Cliente:** Configura dashboards, exporta relatórios
- **Viewer Cliente:** Consulta KPIs e gráficos (read-only)

---

## Alternativas Consideradas

### Opção 1: React + Material-UI + FastAPI Backend
```
Frontend (React) ←→ REST API (FastAPI) ←→ PostgreSQL
```
- **Prós:**
  - Máxima flexibilidade e controle
  - Performance excelente
  - Componentização avançada
- **Contras:**
  - **Time-to-market:** 3-4 meses (setup, API, frontend)
  - Requer conhecimento de JavaScript/React
  - Complexidade operacional (2 deploys)
  - Custo de manutenção alto
- **Decisão:** ❌ Rejeitado - over-engineering

### Opção 2: Dash (Plotly)
```python
import dash
from dash import dcc, html

app = dash.Dash(__name__)
app.layout = html.Div([...])
```
- **Prós:**
  - Python puro
  - Integração nativa com Plotly
  - Callbacks para interatividade
- **Contras:**
  - Verboso (muito boilerplate HTML/CSS)
  - Curva de aprendizado média
  - Menos componentes prontos que Streamlit
  - Comunidade menor
- **Decisão:** ❌ Rejeitado - maior complexidade

### Opção 3: Jupyter Notebooks + Voilà
```python
# notebook.ipynb
import pandas as pd
df = pd.read_sql(...)
display(df.plot())
```
- **Prós:**
  - Familiar para data scientists
  - Rápido para protótipos
- **Contras:**
  - Não é um dashboard real (sem navegação)
  - Sem autenticação nativa
  - Performance ruim com muitos usuários
  - Difícil de versionar (.ipynb)
- **Decisão:** ❌ Rejeitado - não é production-ready

### Opção 4: Streamlit ✅
```python
import streamlit as st
import pandas as pd

st.title("Dashboard AllpFit")
df = pd.read_sql("SELECT * FROM ...", conn)
st.dataframe(df)
st.line_chart(df)
```
- **Prós:**
  - ✅ **Extremamente simples:** Código Python puro
  - ✅ **Rápido:** Dashboard funcional em horas
  - ✅ **Componentes ricos:** 40+ widgets out-of-the-box
  - ✅ **Reativo:** Auto-refresh sem JavaScript
  - ✅ **Integração:** Pandas, Plotly, Altair nativos
  - ✅ **Customização:** CSS custom, temas
  - ✅ **Comunidade:** 23k+ stars no GitHub
  - ✅ **Deployment:** Um comando (`streamlit run`)
  - ✅ **Multi-page:** Suporte nativo a apps multi-página
- **Contras:**
  - Menos flexível que React (trade-off aceitável)
  - Session state requer cuidado (boas práticas)
  - Performance limitada para 1000+ usuários simultâneos
- **Decisão:** ✅ **ESCOLHIDO**

---

## Decisão

Implementar dashboards usando **Streamlit** como framework principal:

### Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit App (Multi-Page)                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  app.py (Router Principal)                              │
│  ├─ Login Page           → auth.authenticate_user()     │
│  ├─ Admin Panel          → middleware.require_admin()   │
│  └─ Client Dashboard     → middleware.require_auth()    │
│                                                           │
│  Componentes:                                            │
│  ├─ st.sidebar           → Filtros (data, status)       │
│  ├─ st.metric            → KPIs (cards)                 │
│  ├─ st.plotly_chart      → Gráficos interativos         │
│  ├─ st.dataframe         → Tabelas de dados             │
│  └─ st.cache_data        → Cache de queries SQL         │
│                                                           │
│  Estado:                                                 │
│  └─ st.session_state     → Sessão de usuário, filtros   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Componentes-Chave

#### 1. Multi-Page App (Router)
```python
# app.py (main router)
import streamlit as st
from multi_tenant.auth import middleware

# Configuração da página
st.set_page_config(page_title="AllpFit Analytics", layout="wide")

# Validação de autenticação
if not middleware.is_authenticated():
    # Renderizar login page
    from multi_tenant.dashboards.login_page import render_login
    render_login()
else:
    # Roteamento por role
    user = st.session_state.user_data
    if user['role'] in ['super_admin', 'admin'] and user['tenant_id'] == 0:
        # Painel Admin GeniAI
        from multi_tenant.dashboards.admin_panel import render_admin
        render_admin()
    else:
        # Dashboard do Cliente
        from multi_tenant.dashboards.client_dashboard import render_client
        render_client()
```

#### 2. Autenticação e RLS
```python
# middleware.py
def require_authentication():
    """Middleware: protege páginas, configura RLS"""
    if 'session_id' not in st.session_state:
        st.error("Você precisa fazer login")
        st.stop()

    # Validar sessão
    session = auth.validate_session(st.session_state.session_id)
    if not session:
        st.error("Sessão expirada")
        clear_session_state()
        st.rerun()

    # Configurar contexto RLS
    set_rls_context(engine, session['tenant_id'], session['user_id'])
    return session
```

#### 3. KPIs e Métricas
```python
# Dashboard com KPIs
st.title("Dashboard AllpFit")

# Filtros na sidebar
with st.sidebar:
    date_start = st.date_input("Data Início", value=today - timedelta(days=30))
    date_end = st.date_input("Data Fim", value=today)

# Queries (cache automático)
@st.cache_data(ttl=600)  # Cache por 10 minutos
def load_metrics(tenant_id, start, end):
    return pd.read_sql(f"""
        SELECT
            COUNT(*) as total_conversations,
            COUNT(*) FILTER (WHERE is_lead = true) as leads,
            AVG(first_response_time) as avg_response
        FROM conversations_analytics
        WHERE conversation_date BETWEEN '{start}' AND '{end}'
          AND tenant_id = {tenant_id}
    """, conn)

# Renderizar KPIs
metrics = load_metrics(tenant_id, date_start, date_end)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Conversas", f"{metrics['total_conversations']:,}")
with col2:
    st.metric("Leads Gerados", f"{metrics['leads']:,}")
with col3:
    st.metric("Tempo Resposta", f"{metrics['avg_response']:.0f}s")
```

#### 4. Gráficos Interativos (Plotly)
```python
import plotly.express as px

# Gráfico de leads por dia
df_daily = pd.read_sql("""
    SELECT
        DATE(conversation_date) as day,
        COUNT(*) FILTER (WHERE is_lead = true) as leads
    FROM conversations_analytics
    WHERE tenant_id = ? AND conversation_date >= ?
    GROUP BY DATE(conversation_date)
    ORDER BY day
""", conn, params=(tenant_id, date_start))

fig = px.line(df_daily, x='day', y='leads',
              title='Leads por Dia',
              labels={'day': 'Data', 'leads': 'Leads'})
st.plotly_chart(fig, use_container_width=True)
```

#### 5. Tema Customizado (Dark Mode)
```python
# config.py (tema global)
def apply_custom_theme():
    st.markdown("""
    <style>
    /* Dark theme */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }

    /* KPI cards */
    [data-testid="stMetric"] {
        background-color: #1E2127;
        border: 1px solid #1E90FF;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Primary color: Blue #1E90FF */
    .stButton>button {
        background-color: #1E90FF;
        color: white;
    }

    /* Accent color: Orange #FF8C00 */
    .stSelectbox label {
        color: #FF8C00;
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## Consequências

### Positivas ✅

1. **Velocidade de Desenvolvimento:** Dashboard funcional em 2-3 dias (vs 2-3 meses com React)
2. **Manutenção Simples:** Código Python puro, sem build step
3. **Python-First:** Equipe não precisa aprender JavaScript
4. **Componentes Prontos:** 40+ widgets (metrics, charts, tables, forms)
5. **Integração:** Pandas/Plotly/SQLAlchemy funcionam nativamente
6. **Cache Inteligente:** `@st.cache_data` otimiza queries automaticamente
7. **Deployment:** `streamlit run app.py` (sem npm, webpack, etc.)
8. **Community:** 23k+ stars, extensões, documentação rica

### Negativas ❌

1. **Flexibilidade Limitada:** Menos controle que React (layout, animações)
2. **Performance:** Limitado para 1000+ usuários simultâneos
3. **Session State:** Requer cuidado com gestão de estado
4. **Customização CSS:** Menos previsível que frameworks tradicionais
5. **Mobile:** Responsividade limitada (focado em desktop)

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Performance degradada com 100+ usuários | Média | Alto | Nginx cache, Redis cache, múltiplas instâncias |
| Session state bugs (reruns inesperados) | Alta | Médio | Boas práticas, testes, callbacks |
| Customização limitada | Baixa | Baixo | CSS custom + Streamlit components |
| Vendor lock-in | Baixa | Médio | Lógica de negócio separada (módulos) |

---

## Casos de Uso

### 1. Dashboard Cliente (AllpFit)
```python
# client_dashboard.py
st.title("Dashboard AllpFit")

# Filtros
date_range = st.date_input("Período", value=(start, end))

# KPIs
metrics = load_metrics(tenant_id, *date_range)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Conversas", f"{metrics.total:,}")
col2.metric("Leads", f"{metrics.leads:,}", delta="+12%")
col3.metric("Taxa Conversão", f"{metrics.conv_rate:.1%}")
col4.metric("CSAT Médio", f"{metrics.csat:.1f}/5")

# Gráficos
st.plotly_chart(create_leads_chart(tenant_id, date_range))
st.plotly_chart(create_hourly_heatmap(tenant_id, date_range))

# Tabela de leads
st.subheader("Últimos Leads")
st.dataframe(load_recent_leads(tenant_id), use_container_width=True)
```

### 2. Painel Admin (GeniAI)
```python
# admin_panel.py
st.title("Painel Admin - GeniAI")

# Overview de todos os clientes
tenants = load_tenants()
col1, col2, col3 = st.columns(3)
col1.metric("Clientes Ativos", len(tenants))
col2.metric("Conversas (Total)", f"{sum(t['conversations'] for t in tenants):,}")
col3.metric("Leads (Total)", f"{sum(t['leads'] for t in tenants):,}")

# Cards de clientes
for tenant in tenants:
    with st.expander(f"📊 {tenant['name']}"):
        col1, col2 = st.columns(2)
        col1.metric("Conversas", f"{tenant['conversations']:,}")
        col2.metric("Leads", f"{tenant['leads']:,}")

        if st.button(f"Ver Dashboard", key=f"btn_{tenant['id']}"):
            st.session_state.selected_tenant = tenant['id']
            st.rerun()
```

### 3. Filtros Dinâmicos e Drill-Down
```python
# Filtros interligados
status = st.multiselect("Status", options=['open', 'resolved', 'pending'])
priority = st.selectbox("Prioridade", options=['all', 'high', 'medium', 'low'])

# Query dinâmica baseada em filtros
query = "SELECT * FROM conversations_analytics WHERE tenant_id = ?"
params = [tenant_id]

if status:
    query += " AND status IN ({})".format(','.join(['?']*len(status)))
    params.extend(status)

if priority != 'all':
    query += " AND priority = ?"
    params.append(priority)

df = pd.read_sql(query, conn, params=params)
st.dataframe(df)
```

---

## Métricas de Sucesso

### Performance
- ✅ Tempo de carregamento inicial: < 2 segundos
- ✅ Refresh de gráficos: < 500ms (com cache)
- ✅ Suporte: 50+ usuários simultâneos (single instance)

### Desenvolvimento
- ✅ Time-to-market: Dashboard funcional em 3 dias
- ✅ Velocidade de iteração: Features novas em horas (não dias)
- ✅ Manutenção: 1 desenvolvedor mantém todo o frontend

### Usabilidade
- ✅ Onboarding: Usuários conseguem usar sem treinamento
- ✅ Satisfação: NPS > 8 (interfaces intuitivas)

---

## Implementação

### Fase 1: Setup Inicial (Completo)
- ✅ Instalação: `pip install streamlit plotly pandas`
- ✅ Estrutura multi-page (`app.py` + subpáginas)
- ✅ Tema dark customizado (`config.py`)

### Fase 2: Autenticação (Completo)
- ✅ Login page com validação
- ✅ Middleware para proteção de rotas
- ✅ Session state management

### Fase 3: Dashboards (Completo)
- ✅ Admin panel (GeniAI)
- ✅ Client dashboard (AllpFit)
- ✅ 12 KPIs principais
- ✅ 5 gráficos interativos (Plotly)

### Fase 4: Otimização (Em Progresso)
- 🔄 Cache de queries SQL
- 🔄 Lazy loading de gráficos
- 🔄 Compressão de dados no frontend

---

## Deployment

### Local Development
```bash
streamlit run src/multi_tenant/dashboards/app.py --server.port=8504
```

### Production (Nginx + Gunicorn)
```nginx
# /etc/nginx/sites-available/allpfit-analytics
server {
    listen 443 ssl;
    server_name analytics.allpfit.com;

    location / {
        proxy_pass http://localhost:8504;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Systemd Service
```ini
# /etc/systemd/system/streamlit-dashboard.service
[Unit]
Description=Streamlit Dashboard AllpFit
After=postgresql.service

[Service]
User=isaac
WorkingDirectory=/home/isaac/allpfit-analytics
ExecStart=/home/isaac/allpfit-analytics/venv/bin/streamlit run src/multi_tenant/dashboards/app.py --server.port=8504
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Referências

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Gallery](https://streamlit.io/gallery)
- [Multi-Page Apps](https://docs.streamlit.io/library/get-started/multipage-apps)
- [Caching](https://docs.streamlit.io/library/advanced-features/caching)

---

## Notas de Revisão

**Próxima Revisão:** 2026-02-01
**Responsável:** Isaac (GenIAI)
**Gatilhos de Revisão:**
- Performance < 50 usuários simultâneos
- Necessidade de mobile app
- Requisito de customização extrema (considerar React)
- Feedback negativo de usuários (UX)