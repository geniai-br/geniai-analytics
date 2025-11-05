# 🎨 UX FLOW - FASE 2: AUTENTICAÇÃO MULTI-TENANT

> **Documento:** Fluxo de experiência do usuário por role
> **Criado em:** 2025-11-05
> **Versão:** 1.0 (Nova estratégia)

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Personas](#personas)
3. [Fluxo Completo por Role](#fluxo-completo-por-role)
4. [Wireframes](#wireframes)
5. [Componentes Reutilizáveis](#componentes-reutilizáveis)
6. [Navegação e Estados](#navegação-e-estados)
7. [Interações e Feedback](#interações-e-feedback)

---

## 🎯 VISÃO GERAL

### Princípios de Design

1. **Simplicidade:** Interface limpa, sem distrações
2. **Consistência:** Mesmo tema dark em todas as telas
3. **Feedback Visual:** Sempre informar o estado da ação
4. **Responsividade:** Funcionar em diferentes resoluções
5. **Performance:** Carregamento rápido, cache inteligente

### Tema Visual

**Base: Porta 8503 (tema dark azul/laranja)**

```css
/* Cores Principais */
--primary: #1E90FF;      /* Azul */
--secondary: #FF8C00;    /* Laranja */
--success: #00C853;      /* Verde */
--danger: #E53935;       /* Vermelho */

/* Backgrounds */
--bg-dark: #0E1117;      /* Fundo escuro principal */
--bg-card: #1A1F2E;      /* Cards */
--bg-secondary: #262B3D; /* Secundário */

/* Texto */
--text-primary: #FFFFFF;
--text-secondary: #B0B8C4;
--text-muted: #6C757D;
```

---

## 👥 PERSONAS

### 1. **Lucas - Super Admin GeniAI**

**Perfil:**
- Cargo: CTO da GeniAI
- Objetivo: Monitorar todos os clientes, acessar qualquer dashboard
- Necessidades:
  - Ver overview geral
  - Acessar dashboard de qualquer cliente
  - Gerenciar configurações

**Jornada:**
```
Login → Painel Admin → Ver Métricas Gerais → Selecionar Cliente → Ver Dashboard Específico → Voltar ao Painel
```

---

### 2. **Mariana - Suporte GeniAI**

**Perfil:**
- Cargo: Analista de Suporte
- Objetivo: Ajudar clientes com problemas
- Necessidades:
  - Ver dados de qualquer cliente (suporte)
  - Verificar se ETL está rodando
  - Acessar logs

**Jornada:**
```
Login → Painel Admin → Selecionar Cliente com Problema → Analisar Dados → Reportar Solução
```

---

### 3. **Isaac - Admin AllpFit (Cliente)**

**Perfil:**
- Cargo: Gestor da AllpFit
- Objetivo: Ver métricas do seu negócio
- Necessidades:
  - Dashboard com KPIs
  - Filtros por período
  - Exportar relatórios

**Jornada:**
```
Login → Dashboard AllpFit (direto) → Filtrar Período → Analisar KPIs → Visualizar Leads
```

---

### 4. **Ana - Visualizadora AllpFit (Cliente)**

**Perfil:**
- Cargo: Recepcionista da AllpFit
- Objetivo: Apenas visualizar dados
- Necessidades:
  - Ver métricas básicas
  - Não pode editar nada

**Jornada:**
```
Login → Dashboard AllpFit (somente leitura) → Ver Métricas
```

---

## 🗺️ FLUXO COMPLETO POR ROLE

### 🔹 FLUXO 1: SUPER ADMIN / ADMIN GENIAI

**Usuários:** admin@geniai.com.br, suporte@geniai.com.br
**tenant_id:** 0 (GeniAI Admin)

```
┌──────────────────────────────────────────────────────────────┐
│                     TELA 1: LOGIN                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              🔐 GeniAI Analytics                             │
│               Sistema Multi-Tenant                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  📧 Email                                              │ │
│  │  [_____________________________________________]       │ │
│  │                                                        │ │
│  │  🔑 Senha                                              │ │
│  │  [_____________________________________________]       │ │
│  │                                                        │ │
│  │           [🚀 Entrar - Botão Azul]                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  💡 Credenciais de DEV:                                     │
│  • admin@geniai.com.br / senha123                           │
│  • suporte@geniai.com.br / senha123                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓ [Autenticar]
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                 TELA 2: PAINEL ADMIN                         │
├──────────────────────────────────────────────────────────────┤
│  🎛️  PAINEL ADMIN GENIAI                    [🚪 Sair]      │
│  Bem-vindo, Administrador GeniAI                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Overview Geral                                          │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │Clientes │Conversas│  Leads  │  Taxa   │                 │
│  │    2    │  1.234  │   567   │  45.9%  │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  👥 Selecione um Cliente                                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📦 AllpFit CrossFit                                │   │
│  │  Slug: allpfit                                       │   │
│  │  Inboxes: 2  │  Usuários: 2  │  [📊 Ver Dashboard] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📦 Academia XYZ (Futuro cliente)                   │   │
│  │  Slug: academia-xyz                                  │   │
│  │  Inboxes: 1  │  Usuários: 3  │  [📊 Ver Dashboard] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ⚙️ Gerenciamento                                           │
│  🚧 Gerenciar clientes (Fase 5)                             │
└──────────────────────────────────────────────────────────────┘
                            ↓ [Clicar "Ver Dashboard"]
                            ↓
┌──────────────────────────────────────────────────────────────┐
│              TELA 3: DASHBOARD DO CLIENTE                    │
│            (Admin visualizando cliente específico)           │
├──────────────────────────────────────────────────────────────┤
│  [← Voltar]  📊 Analytics - AllpFit CrossFit  [🚪 Sair]    │
│              👤 Administrador GeniAI (super_admin)           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Início: 01/10/24] [Fim: 31/10/24] [🔄 Atualizar]         │
│                                                              │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │Contatos │Conv. IA │  Leads  │ Visitas │                 │
│  │   234   │   189   │   78    │   45    │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
│                                                              │
│  [Gráficos de Leads por Dia...]                             │
│  [Tabela de Leads...]                                       │
│  [Análise de IA...]                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Características:**
- ✅ Botão "← Voltar" para retornar ao painel
- ✅ Nome do cliente no cabeçalho
- ✅ Indicação de que é admin visualizando outro tenant
- ✅ Todos os dados filtrados via RLS pelo tenant selecionado

---

### 🔹 FLUXO 2: CLIENTE (Admin ou Visualizador)

**Usuários:** isaac@allpfit.com.br, visualizador@allpfit.com.br
**tenant_id:** 1 (AllpFit)

```
┌──────────────────────────────────────────────────────────────┐
│                     TELA 1: LOGIN                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              🔐 GeniAI Analytics                             │
│               Sistema Multi-Tenant                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  📧 Email                                              │ │
│  │  [_____________________________________________]       │ │
│  │                                                        │ │
│  │  🔑 Senha                                              │ │
│  │  [_____________________________________________]       │ │
│  │                                                        │ │
│  │           [🚀 Entrar - Botão Azul]                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  💡 Credenciais de DEV:                                     │
│  • isaac@allpfit.com.br / senha123                          │
│  • visualizador@allpfit.com.br / senha123                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓ [Autenticar]
                            ↓ [Redireciona DIRETO para dashboard]
                            ↓
┌──────────────────────────────────────────────────────────────┐
│              TELA 2: DASHBOARD (DIRETO)                      │
├──────────────────────────────────────────────────────────────┤
│  📊 ANALYTICS - ALLPFIT CROSSFIT             [🚪 Sair]      │
│  👤 Isaac Santos (admin)                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Início: 01/10/24] [Fim: 31/10/24] [🔄 Atualizar]         │
│                                                              │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │Contatos │Conv. IA │  Leads  │ Visitas │                 │
│  │   234   │   189   │   78    │   45    │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
│                                                              │
│  📈 Leads por Dia                                           │
│  [Gráfico de barras...]                                     │
│                                                              │
│  📊 Taxa de Conversão (Últimos 30 dias)                     │
│  [Gráfico de linha...]                                      │
│                                                              │
│  📋 Tabela de Leads                                         │
│  ┌───────────┬──────────┬──────────┬──────────┐            │
│  │   Nome    │ Celular  │  Status  │   Ação   │            │
│  ├───────────┼──────────┼──────────┼──────────┤            │
│  │ João S.   │ (83)9... │  Lead    │ [Ver]    │            │
│  │ Maria A.  │ (83)9... │ Agendado │ [Ver]    │            │
│  └───────────┴──────────┴──────────┴──────────┘            │
│                                                              │
│  [Paginação: ← 1 2 3 4 5 →]                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Características:**
- ✅ **SEM painel de seleção** (vê apenas seus dados)
- ✅ Nome do tenant no título (AllpFit CrossFit)
- ✅ Role do usuário exibido
- ✅ Dados automaticamente filtrados via RLS
- ✅ Mesmo layout da porta 8503

---

## 🖼️ WIREFRAMES

### Tela de Login (Detalhada)

```
┌──────────────────────────────────────────────────┐
│                                                  │
│                                                  │
│          [LOGO GENIAI - Opcional]                │
│                                                  │
│       ┌────────────────────────────────┐        │
│       │                                │        │
│       │   🔐 GeniAI Analytics          │        │
│       │   Sistema Multi-Tenant         │        │
│       │                                │        │
│       │  ┌──────────────────────────┐ │        │
│       │  │ 📧 Email                 │ │        │
│       │  │                          │ │        │
│       │  │ [input email]            │ │        │
│       │  └──────────────────────────┘ │        │
│       │                                │        │
│       │  ┌──────────────────────────┐ │        │
│       │  │ 🔑 Senha                 │ │        │
│       │  │                          │ │        │
│       │  │ [input password]         │ │        │
│       │  └──────────────────────────┘ │        │
│       │                                │        │
│       │  ┌──────────────────────────┐ │        │
│       │  │  🚀 Entrar               │ │        │
│       │  └──────────────────────────┘ │        │
│       │                                │        │
│       │  ─────────────────────────────│        │
│       │                                │        │
│       │  💡 Credenciais de DEV:       │        │
│       │  • Admin: admin@geniai...     │        │
│       │  • Cliente: isaac@allpfit...  │        │
│       │                                │        │
│       └────────────────────────────────┘        │
│                                                  │
│          Powered by GeniAI © 2025               │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Estados:**
1. **Inicial:** Form vazio, botão habilitado
2. **Validando:** Spinner no botão "Autenticando..."
3. **Sucesso:** Mensagem verde + balloons + redirect
4. **Erro:** Mensagem vermelha abaixo do form

---

### Painel Admin (Card de Cliente)

```
┌─────────────────────────────────────────────────┐
│  📦 AllpFit CrossFit                            │
│  Slug: allpfit                                  │
│                                                 │
│  ┌──────────────┬──────────────┬─────────────┐ │
│  │  Inboxes: 2  │ Usuários: 2  │ [Ver Dash]  │ │
│  └──────────────┴──────────────┴─────────────┘ │
│                                                 │
│  📊 Métricas Rápidas:                          │
│  • Conversas: 234                              │
│  • Leads: 78                                   │
│  • Última Sincronização: 05/11/25 10:30       │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Interação:**
- Hover: Card com borda azul
- Click no botão: Redireciona para dashboard

---

### Header do Dashboard

```
┌──────────────────────────────────────────────────────────┐
│  [← Voltar]  📊 Analytics - AllpFit  [🔄] [⚙️] [🚪 Sair] │
│              👤 Isaac Santos (admin)                      │
└──────────────────────────────────────────────────────────┘
```

**Componentes:**
- `[← Voltar]`: Só aparece se admin visualizando outro tenant
- `[🔄]`: Atualizar dados (clear cache)
- `[⚙️]`: Configurações (futuro)
- `[🚪 Sair]`: Logout

---

## 🔧 COMPONENTES REUTILIZÁVEIS

### 1. **Header Component**

```python
def render_header(session, tenant_name, show_back=False):
    """
    Header padrão para dashboards

    Args:
        session: Dados da sessão
        tenant_name: Nome do tenant exibido
        show_back: Se mostra botão voltar
    """
    cols = st.columns([1, 5, 1])

    with cols[0]:
        if show_back:
            if st.button("← Voltar"):
                return 'back'

    with cols[1]:
        st.title(f"📊 Analytics - {tenant_name}")
        st.caption(f"👤 {session['full_name']} ({session['role']})")

    with cols[2]:
        if st.button("🚪 Sair"):
            return 'logout'

    return None
```

---

### 2. **KPI Card Component**

```python
def render_kpi_card(label, value, delta=None, icon="📊"):
    """
    Card de KPI estilizado

    Args:
        label: Nome da métrica
        value: Valor principal
        delta: Variação (opcional)
        icon: Emoji (opcional)
    """
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {f'<div class="kpi-delta">{delta}</div>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)
```

---

### 3. **Client Card Component (Admin Panel)**

```python
def render_client_card(tenant):
    """
    Card de cliente no painel admin

    Args:
        tenant: Dict com dados do tenant
    """
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"### 📦 {tenant['name']}")
            st.caption(f"Slug: {tenant['slug']}")

        with col2:
            st.metric("Inboxes", len(tenant['inbox_ids']))
            st.metric("Usuários", tenant['user_count'])

        with col3:
            if st.button("📊 Ver Dashboard", key=f"dash_{tenant['id']}"):
                st.session_state['selected_tenant_id'] = tenant['id']
                st.rerun()

        st.divider()
```

---

### 4. **Date Filter Component**

```python
def render_date_filters():
    """
    Filtros de data padrão

    Returns:
        tuple: (date_start, date_end, refresh_clicked)
    """
    col1, col2, col3 = st.columns([3, 1, 1])

    with col2:
        date_start = st.date_input("Início", value=datetime.now() - timedelta(days=30))

    with col3:
        date_end = st.date_input("Fim", value=datetime.now())

    with col1:
        st.write("")  # Espaçamento
        refresh = st.button("🔄 Atualizar Dados")

    return date_start, date_end, refresh
```

---

## 🔀 NAVEGAÇÃO E ESTADOS

### Estados do Session State

```python
# Após login bem-sucedido
st.session_state = {
    'authenticated': True,
    'session_id': 'uuid-da-sessao',
    'user': {
        'user_id': 1,
        'tenant_id': 0,
        'email': 'admin@geniai.com.br',
        'full_name': 'Administrador GeniAI',
        'role': 'super_admin',
        'tenant_name': 'GeniAI Admin',
        'tenant_slug': 'geniai-admin'
    },
    'selected_tenant_id': None  # Usado por admins para navegar entre clientes
}
```

### Matriz de Navegação

| Role | tenant_id | Após Login | Pode Voltar? | Vê Outros Tenants? |
|------|-----------|------------|--------------|-------------------|
| super_admin | 0 | Painel Admin | N/A | ✅ Sim |
| admin | 0 | Painel Admin | N/A | ✅ Sim |
| admin | 1+ | Dashboard Direto | ❌ Não | ❌ Não |
| client | 1+ | Dashboard Direto | ❌ Não | ❌ Não |

---

## 💬 INTERAÇÕES E FEEDBACK

### 1. **Login**

**Estados:**
```python
# Inicial
[🚀 Entrar]

# Validando
[⏳ Autenticando...]  # Spinner

# Sucesso
✅ Bem-vindo, Isaac Santos!
🎈 [Balloons animation]
[Aguarda 1s e redireciona]

# Erro - Senha incorreta
❌ Email ou senha incorretos

# Erro - Usuário inativo
⚠️ Sua conta está inativa. Entre em contato com o suporte.

# Erro - Tenant suspenso
⚠️ Acesso temporariamente suspenso. Entre em contato.
```

---

### 2. **Seleção de Cliente (Admin)**

**Estados:**
```
# Hover no card
[Card com borda azul brilhante]

# Click em "Ver Dashboard"
[Spinner] Carregando dados do cliente...
[Redireciona para dashboard]
```

---

### 3. **Carregamento de Dados**

```python
# Ao filtrar período
with st.spinner("🔄 Carregando dados..."):
    df = load_conversations(tenant_id, date_start, date_end)

if df.empty:
    st.warning("⚠️ Nenhum dado encontrado para o período selecionado")
else:
    st.success(f"✅ {len(df)} conversas carregadas")
```

---

### 4. **Logout**

```python
# Click em "Sair"
with st.spinner("🚪 Fazendo logout..."):
    logout_user(engine, session_id)
    clear_session_state()

st.success("✅ Logout realizado!")
time.sleep(0.5)
st.rerun()  # Volta para login
```

---

### 5. **Sessão Expirada**

```python
# Ao validar sessão
if not session:
    st.error("⏰ Sua sessão expirou. Faça login novamente.")
    st.info("💡 Por segurança, sessões expiram após 24 horas de inatividade.")
    time.sleep(2)
    clear_session_state()
    st.rerun()
```

---

## 📱 RESPONSIVIDADE

### Breakpoints

```python
# Desktop (> 1200px)
col1, col2, col3, col4 = st.columns(4)  # 4 KPIs por linha

# Tablet (768px - 1200px)
col1, col2 = st.columns(2)  # 2 KPIs por linha

# Mobile (< 768px)
col1 = st.columns(1)  # 1 KPI por linha (vertical)
```

**Streamlit já é responsivo por padrão, mas ajustes:**
- Reduzir padding em telas pequenas
- Esconder botões secundários em mobile
- Simplificar gráficos em mobile

---

## ✅ CHECKLIST DE UX

### Login
- [ ] Form centralizado e legível
- [ ] Validação de campos vazios
- [ ] Feedback de erro claro
- [ ] Credenciais de DEV visíveis (apenas dev)
- [ ] Animação de sucesso (balloons)

### Painel Admin
- [ ] Overview com métricas agregadas
- [ ] Cards de clientes com hover effect
- [ ] Botão "Ver Dashboard" destaque
- [ ] Logout acessível

### Dashboard Cliente
- [ ] Header com nome do tenant
- [ ] Role do usuário visível
- [ ] Filtros de data funcionais
- [ ] KPIs destacados
- [ ] Gráficos legíveis
- [ ] Tabelas com paginação

### Navegação
- [ ] Botão "Voltar" apenas para admins
- [ ] Transições suaves entre telas
- [ ] Breadcrumbs (se necessário)

### Performance
- [ ] Cache de queries longas
- [ ] Loading states em todas as ações
- [ ] Lazy loading de gráficos pesados

---

## 📚 REFERÊNCIAS

- [Streamlit Docs - Layouts](https://docs.streamlit.io/library/api-reference/layout)
- [Streamlit Docs - Session State](https://docs.streamlit.io/library/api-reference/session-state)
- [Material Design - Dark Theme](https://material.io/design/color/dark-theme.html)
- [Dashboard da Porta 8503](../../src/app/dashboard.py) - Base de design

---

**Última atualização:** 2025-11-05
**Mantido por:** Isaac (via Claude Code)
**Status:** 📋 Documento de planejamento - Implementação na Fase 2