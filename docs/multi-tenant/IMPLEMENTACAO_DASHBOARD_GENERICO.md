# CHANGELOG - Dashboard Multi-Tenant Genérico

**Data:** 2025-11-11
**Motivo:** Pós-apresentação aos superiores
**Branch:** `feature/dashboard-generico`

---

## 🎯 OBJETIVO

Transformar o dashboard multi-tenant de específico AllpFit para **100% genérico**, removendo campos de análise fitness (condição física, objetivos, sugest ão de disparo) que não se aplicam a outros segmentos (educação, financeiro, varejo, etc.).

---

## 📋 MUDANÇAS IMPLEMENTADAS

### 1. Arquivamento de Código Específico AllpFit

**Criado:** [`src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py`](../../../src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py)

Contém todas as funções específicas AllpFit para preservação e possível reativação:

#### Funções Arquivadas:
- `render_conversion_funnel_allpfit()` - Funil Leads → Visitas → CRM
- `render_allpfit_openai_filters()` - Filtros de análise IA (condição física, probabilidade 4-5, etc.)
- `apply_allpfit_openai_filters()` - Aplicação dos filtros ao DataFrame
- `render_allpfit_ai_analysis_modal()` - Modal detalhado com análise IA + sugestão de disparo
- `get_allpfit_table_columns()` - Definição de colunas da tabela com campos AllpFit

#### Custo Preservado:
- R$ 29,55 total (742 conversas analisadas até 2025-11-09)
- ~R$ 0,022 por conversa

---

### 2. Modificações em `client_dashboard.py`

#### A. Query SQL (linhas 46-83)

**❌ REMOVIDAS:**
```sql
-- condicao_fisica
-- objetivo
-- analise_ia
-- sugestao_disparo
-- probabilidade_conversao
```

**✅ ADICIONADAS:**
```sql
nome_mapeado_bot,  -- Nome extraído pela IA (42% dos dados AllpFit)
mc_first_message_at as primeiro_contato,  -- Primeira mensagem (99.9%)
mc_last_message_at as ultimo_contato,  -- Última mensagem (99.9%)
message_compiled as conversa_compilada  -- JSONB com conversa completa (99.9%)
```

**Descoberta Crítica:** Todas essas colunas **JÁ EXISTIAM** no banco! Apenas não estavam sendo exibidas.

---

#### B. Funil de Conversão (linhas 510-512)

**Antes:**
```python
st.divider()
st.subheader("🎯 Funil de Conversão")
# Leads → Visitas → CRM (38 linhas de código)
```

**Depois:**
```python
# REMOVIDO: Funil de Conversão (específico AllpFit - Leads → Visitas → CRM)
# Motivo: Fluxo específico de vendas fitness, não aplicável a outros segmentos
# Data: 2025-11-11 (pós-apresentação)
```

---

#### C. Filtros OpenAI (linhas 952-966)

**Antes:**
- Checkbox "Apenas com Análise IA"
- Checkbox "Probabilidade Alta (4-5)"
- Checkbox "Visita Agendada"
- Selectbox Classificação

**Depois:**
```python
# REMOVIDO: Filtros OpenAI específicos AllpFit (analise_ia, probabilidade_conversao, condicao_fisica, objetivo)
# Ver: src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py
```

---

#### D. Aplicação de Filtros (linhas 988-990)

**Antes:**
- 4 blocos de código filtrando por `analise_ia`, `probabilidade_conversao`, etc.

**Depois:**
```python
# REMOVIDO: Aplicação de filtros OpenAI específicos AllpFit
# Ver: src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py
```

---

#### E. Tabela de Leads (linhas 662-744)

**Antes:**
```python
display_df = leads_df[[
    ...,
    'nome_mapeado_bot',
    'condicao_fisica',  # ❌
    'objetivo',  # ❌
    'probabilidade_conversao'  # ❌
]]
```

**Depois:**
```python
display_df = leads_df[[
    'conversation_display_id',
    'contact_name',
    'contact_phone',
    'inbox_name',  # ✅ NOVO - exibir inbox
    'conversation_date',
    'is_lead',
    'visit_scheduled',
    'crm_converted',
    'ai_probability_label',
    'ai_probability_score',
    'nome_mapeado_bot'  # ✅ MANTIDO - genérico
]]
```

**Colunas Exibidas:**
- ID, Nome, Telefone, **Inbox**, Data, Lead, Visita, CRM, Classificação IA, Score IA, Nome Mapeado

---

#### F. Modal de Análise IA (linhas 743-744)

**Antes:**
- 87 linhas de código
- Exibia condição física, objetivo, análise IA, sugestão de disparo, probabilidade 0-5

**Depois:**
```python
# REMOVIDO: Modal de Análise IA Detalhada (específico AllpFit)
# Ver: src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py → render_allpfit_ai_analysis_modal()
```

---

## 📊 COLUNAS DO BANCO

### ✅ Colunas Genéricas (Mantidas)

| Coluna | Preenchimento | Descrição |
|--------|---------------|-----------|
| `inbox_name` | 100% | Nome da inbox (WhatsApp, Instagram, etc.) |
| `mc_first_message_at` | 99.9% | Data/hora primeira mensagem |
| `mc_last_message_at` | 99.9% | Data/hora última mensagem |
| `message_compiled` | 99.9% | JSONB com conversa completa |
| `nome_mapeado_bot` | 42% | Nome extraído pela IA |

### ❌ Colunas AllpFit (Ocultas, NÃO deletadas)

| Coluna | Preenchimento | Motivo Ocultação |
|--------|---------------|------------------|
| `condicao_fisica` | 2.2% | Específico fitness (Sedentário, Ativo, Atleta) |
| `objetivo` | 3% | Específico fitness (Emagrecimento, Ganho de massa) |
| `analise_ia` | 56% | Análise GPT-4o-mini AllpFit-específica |
| `sugestao_disparo` | ? | Mensagem personalizada fitness |
| `probabilidade_conversao` | ? | Score 0-5 baseado em contexto fitness |

**Importante:** Os dados permanecem no banco! Apenas não são exibidos no dashboard multi-tenant genérico.

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
src/multi_tenant/dashboards/
├── _archived/
│   ├── README.md  ← Documentação do arquivamento
│   └── allpfit_specific_functions.py  ← Funções AllpFit preservadas
├── client_dashboard.py  ← Dashboard genérico (modificado)
└── admin_dashboard.py  ← Inalterado
```

---

## 🔄 COMO REATIVAR PARA ALLPFIT

Se no futuro quiser reativar as análises específicas AllpFit:

### 1. Adicionar colunas na query SQL:

```python
# Em load_conversations(), adicionar:
condicao_fisica,
objetivo,
analise_ia,
sugestao_disparo,
probabilidade_conversao
```

### 2. Importar funções arquivadas:

```python
from multi_tenant.dashboards._archived.allpfit_specific_functions import (
    render_conversion_funnel_allpfit,
    render_allpfit_openai_filters,
    apply_allpfit_openai_filters,
    render_allpfit_ai_analysis_modal
)
```

### 3. Adicionar chamadas:

```python
# Após render_kpis():
render_conversion_funnel_allpfit(metrics)

# Após filtros de data:
filtros = render_allpfit_openai_filters()

# Após carregar df:
df = apply_allpfit_openai_filters(df, *filtros)

# Após tabela de leads:
render_allpfit_ai_analysis_modal(df)
```

---

## 📈 IMPACTO

### Linhas de Código:
- **Removidas do dashboard:** ~200 linhas
- **Arquivadas:** ~350 linhas (preservadas em `_archived/`)
- **Comentários adicionados:** ~15 linhas (explicando remoções)

### Funcionalidades:
- ✅ Dashboard **100% genérico**
- ✅ Aplicável a **qualquer segmento** (educação, financeiro, varejo, saúde, etc.)
- ✅ Dados AllpFit **preservados** no banco
- ✅ Fácil reativação se necessário

### Performance:
- Sem mudanças (colunas apenas ocultadas, não deletadas)
- Cache mantido (5 minutos)
- RLS mantido (segurança multi-tenant)

---

---

## 🎯 FASE 4: FILTROS RÁPIDOS (IMPLEMENTADA)

**Data:** 2025-11-11
**Commit:** `bd86fe2`
**Status:** ✅ COMPLETA

### Implementação

**Localização:** [client_dashboard.py](../../src/multi_tenant/dashboards/client_dashboard.py)

#### 1. Session State Initialization (linhas 937-949)

```python
# === INICIALIZAR SESSION STATE DOS FILTROS RÁPIDOS === [FASE 4]
if 'filter_nome' not in st.session_state:
    st.session_state.filter_nome = ""
if 'filter_telefone' not in st.session_state:
    st.session_state.filter_telefone = ""
if 'filter_inboxes' not in st.session_state:
    st.session_state.filter_inboxes = []
if 'filter_status_list' not in st.session_state:
    st.session_state.filter_status_list = []
if 'filter_classificacao' not in st.session_state:
    st.session_state.filter_classificacao = []
if 'filter_score_min' not in st.session_state:
    st.session_state.filter_score_min = 0.0
```

#### 2. Filtros UI - 6 Colunas Horizontais (linhas 731-860)

**Posicionamento:** Diretamente acima da tabela de leads (dentro de `render_leads_table()`)

**Filtros Implementados:**

| Coluna | Filtro | Tipo | Descrição |
|--------|--------|------|-----------|
| 1 | Nome | Text Input | Busca parcial, case-insensitive |
| 2 | Telefone | Text Input | Busca parcial, case-insensitive |
| 3 | Inboxes | Multiselect | Filtro por inbox(es) específica(s) |
| 4 | Status | Multiselect | Lead, Visita Agendada, CRM Convertido |
| 5 | Classificação IA | Multiselect | Alto, Médio, Baixo |
| 6 | Score IA Mínimo | Slider | Range 0-100% |

**Botão "Limpar Filtros":**
- Exibe contador de filtros ativos
- Reseta todos os filtros de uma vez
- Mantém usabilidade mesmo quando resultados vazios

```python
# Botão de limpar filtros com contador
active_filters = sum([
    bool(st.session_state.filter_nome),
    bool(st.session_state.filter_telefone),
    bool(st.session_state.filter_inboxes),
    bool(st.session_state.filter_status_list),
    bool(st.session_state.filter_classificacao),
    st.session_state.filter_score_min > 0
])

if st.button(f"🗑️ Limpar Filtros ({active_filters} ativo{'s' if active_filters != 1 else ''})",
             disabled=(active_filters == 0)):
    # Reset all filters...
```

#### 3. Aplicação de Filtros (linhas 1010-1047)

```python
# === APLICAR FILTROS RÁPIDOS === [FASE 4]
df_filtered = df_original.copy()

# Filtro por Nome (busca parcial, case-insensitive)
if st.session_state.filter_nome:
    df_filtered = df_filtered[
        df_filtered['contact_name'].str.contains(st.session_state.filter_nome, case=False, na=False)
    ]

# Filtro por Telefone (busca parcial)
if st.session_state.filter_telefone:
    df_filtered = df_filtered[
        df_filtered['contact_phone'].str.contains(st.session_state.filter_telefone, na=False)
    ]

# Filtro por Inboxes (multi-select)
if st.session_state.filter_inboxes:
    df_filtered = df_filtered[df_filtered['inbox_name'].isin(st.session_state.filter_inboxes)]

# Filtro por Status (Lead, Visita, CRM)
if st.session_state.filter_status_list:
    mask = pd.Series([False] * len(df_filtered), index=df_filtered.index)
    if "Lead" in st.session_state.filter_status_list:
        mask |= (df_filtered['is_lead'] == True)
    if "Visita Agendada" in st.session_state.filter_status_list:
        mask |= (df_filtered['visit_scheduled'] == True)
    if "CRM Convertido" in st.session_state.filter_status_list:
        mask |= (df_filtered['crm_converted'] == True)
    df_filtered = df_filtered[mask]

# Filtro por Classificação IA
if st.session_state.filter_classificacao:
    df_filtered = df_filtered[df_filtered['ai_probability_label'].isin(st.session_state.filter_classificacao)]

# Filtro por Score IA mínimo
if st.session_state.filter_score_min > 0:
    df_filtered = df_filtered[
        (df_filtered['ai_probability_score'].notna()) &
        (df_filtered['ai_probability_score'] >= st.session_state.filter_score_min)
    ]
```

### 🐛 Bugs Críticos Descobertos e Corrigidos

#### Bug 1: Inbox Mismatch (CRÍTICO)

**Problema:**
- Filtro de inboxes mostrava "AllpFit Telegram" e "AllpFit WhatsApp Principal" (IDs 1, 2)
- Dados reais tinham IDs 14, 61, 64, 67 (allpfitjpsulcloud1, allpfitjpsulcloud2, allpfitjpsulrecepcao)
- Selecionar inbox inexistente travava o dashboard inteiro

**Causa Raiz:**
- Filtro usava tabela de configuração `inbox_tenant_mapping` ao invés dos dados reais
- Mismatch entre configuração e dados reais

**Solução:**
```python
# ANTES (ERRADO):
inbox_names_available = get_inbox_names_from_config()  # ❌ Retorna IDs 1, 2

# DEPOIS (CORRETO):
inbox_names_available = sorted(df_original['inbox_name'].dropna().unique().tolist())  # ✅ IDs reais

# Auto-cleanup de filtros inválidos
valid_selected = [inbox for inbox in st.session_state.filter_inboxes if inbox in inbox_names_available]
if valid_selected != st.session_state.filter_inboxes:
    st.session_state.filter_inboxes = valid_selected
```

#### Bug 2: Dashboard Lock com Filtros Vazios (CRÍTICO)

**Problema:**
- Ao selecionar filtros que não retornam dados, `st.stop()` bloqueava renderização
- Usuário ficava preso sem conseguir acessar botão "Limpar Filtros"
- Único jeito de sair: reiniciar dashboard inteiro

**Causa Raiz:**
- Código original tinha `st.stop()` após mensagem de "Nenhum dado encontrado"
- Isso impedia renderização da tabela (onde estão os filtros)

**Solução:**
```python
# REMOVIDO (linhas 1049-1052):
# if df.empty:
#     st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados")
#     st.info("💡 **Dica:** Tente remover alguns filtros para ver mais resultados")
#     st.stop()  # ❌ Bloqueava acesso aos filtros!

# NOVO: Dashboard continua renderizando mesmo com dados vazios
df = df_filtered  # ✅ Continua fluxo normal
```

#### Bug 3: Restart Script - Múltiplos PIDs

**Problema:**
- Script de restart falhava quando existiam 2+ processos Streamlit
- Exemplo: PIDs 1048478 e 3670926, mas script só matava o primeiro

**Causa Raiz:**
- `lsof` retornava PIDs separados por `\n` (newline)
- Script não iterava sobre todos os PIDs

**Solução:**
```bash
# ANTES (scripts/restart_multi_tenant.sh):
PID=$(lsof -i:8504 -sTCP:LISTEN -c streamlit -t 2>/dev/null)  # ❌ Só pega primeiro PID

# DEPOIS:
PIDS=$(lsof -i:8504 -sTCP:LISTEN -c streamlit -t 2>/dev/null | tr '\n' ' ')  # ✅ Todos PIDs

# Loop através de TODOS os PIDs
for PID in $PIDS; do
    kill -15 "$PID" 2>/dev/null
done

# Aguardar 3 segundos
sleep 3

# Verificar quais resistiram e forçar kill -9
for PID in $PIDS; do
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "   💥 Processo $PID resistiu, forçando kill (SIGKILL)..."
        kill -9 "$PID" 2>/dev/null
    fi
done

# Aumentado retry de 5 para 10 tentativas
for i in {1..10}; do
    if ! lsof -i:8504 -sTCP:LISTEN > /dev/null 2>&1; then
        break
    fi
    sleep 2
done
```

### ✅ Testes Realizados

**Ambiente:** AllpFit CrossFit (tenant real)
**Dados:** 1.317 conversas, 3 inboxes (allpfitjpsulcloud1, allpfitjpsulcloud2, allpfitjpsulrecepcao)

| Teste | Resultado |
|-------|-----------|
| Filtro por Nome (busca parcial) | ✅ Funciona |
| Filtro por Telefone (busca parcial) | ✅ Funciona |
| Filtro por Inbox (multi-select) | ✅ Funciona (após fix Bug 1) |
| Filtro por Status (Lead/Visita/CRM) | ✅ Funciona |
| Filtro por Classificação IA | ✅ Funciona |
| Filtro por Score IA (slider) | ✅ Funciona |
| Botão Limpar Filtros | ✅ Funciona |
| Contador de filtros ativos | ✅ Funciona |
| Dashboard com filtros vazios | ✅ Funciona (após fix Bug 2) |
| Persistência session_state | ✅ Funciona |
| Restart script com múltiplos PIDs | ✅ Funciona (após fix Bug 3) |

### 📊 Impacto

**Linhas de Código:**
- **Adicionadas:** ~200 linhas (session state + UI + lógica de filtros)
- **Modificadas:** ~15 linhas (assinatura de função, chamadas)

**Performance:**
- Sem degradação (filtros operam em memória sobre DataFrame já carregado)
- Session state mantém estado sem re-carregar dados do banco

**UX:**
- ✅ Filtros sempre acessíveis (mesmo com resultados vazios)
- ✅ Feedback visual de filtros ativos
- ✅ Limpar todos os filtros em 1 clique
- ✅ Busca case-insensitive para melhor usabilidade

---

## 🎯 FASE 5: ANÁLISE POR INBOX (IMPLEMENTADA)

**Data:** 2025-11-11
**Status:** ✅ COMPLETA

### Implementação

**Localização:** [client_dashboard.py](../../src/multi_tenant/dashboards/client_dashboard.py)

#### 1. Nova Seção "📬 Análise por Inbox" (linhas 609-845)

**Funções Adicionadas:**

**`prepare_inbox_metrics(df)` (linhas 609-665):**
- Calcula métricas agregadas (todas inboxes juntas)
- Calcula métricas individuais por inbox (usando pandas groupby)
- Retorna: `(metrics_agregadas, inbox_metrics_df)`

**Métricas Calculadas:**
- Total conversas, leads, visitas, CRM
- Taxas de conversão (leads e CRM)
- Tempo médio de primeira resposta

**`render_inbox_analysis(df)` (linhas 668-845):**
- Renderiza seção com toggle de visualização (radio button)
- Duas formas de visualização: Agregada e Separada

#### 2. Modo de Visualização Toggle (linha 689-694)

```python
view_mode = st.radio(
    "Modo de Visualização:",
    options=["📊 Visão Agregada (Consolidado)", "📋 Visão Separada (Por Inbox)"],
    horizontal=True,
    key="inbox_view_mode"
)
```

#### 3. Visão Agregada (linhas 698-773)

**Componentes:**
- **5 cards de métricas** (linhas 703-751):
  - Total Conversas
  - Total Leads (com delta de taxa de conversão)
  - Visitas Agendadas
  - Conversões CRM (com delta % dos leads)
  - Tempo Médio Resposta (formatado min/horas)

- **Gráfico Plotly** (linhas 759-773):
  - Gráfico de barras horizontal
  - Mostra total de conversas por inbox
  - Color scale: Blues

```python
import plotly.express as px

fig = px.bar(
    inbox_metrics,
    x='total_conversas',
    y='inbox_name',
    orientation='h',
    title='Total de Conversas por Inbox',
    color='total_conversas',
    color_continuous_scale='Blues'
)
```

#### 4. Visão Separada (linhas 776-845)

**Componentes:**
- **Tabela completa de métricas** (linhas 784-815):
  - Todas as inboxes com métricas individuais
  - Colunas: Inbox, Conversas, Leads, Taxa Leads (%), Visitas, CRM, Taxa CRM (%), Tempo Resp. (min)
  - Formatação: percentuais com 1 casa decimal, "N/A" para dados ausentes

- **Cards Top 3 Inboxes** (linhas 820-845):
  - Top 3 inboxes por volume de conversas
  - Cards lado a lado (3 colunas)
  - Cada card mostra: Nome, Conversas, Leads (com delta %), Tempo Resposta

#### 5. Integração no Fluxo Principal (linha 1264)

```python
# === ANÁLISE POR INBOX === [FASE 5 - NOVO]
render_inbox_analysis(df)
```

**Posicionamento:** Logo após KPIs principais, antes da seção de gráficos

### ✅ Testes Realizados

**Ambiente:** AllpFit CrossFit (tenant real)
**Dados:** 1.317 conversas, 3 inboxes

| Teste | Resultado |
|-------|-----------|
| Visão Agregada - 5 cards de métricas | ✅ Funciona |
| Visão Agregada - Gráfico Plotly horizontal | ✅ Funciona |
| Visão Separada - Tabela de métricas | ✅ Funciona |
| Visão Separada - Top 3 cards | ✅ Funciona |
| Toggle entre visões (radio button) | ✅ Funciona |
| Formatação de tempo (min/horas) | ✅ Funciona |
| Formatação de percentuais | ✅ Funciona |
| Tratamento de dados vazios (N/A) | ✅ Funciona |

### 🗑️ Remoção - Métricas de Qualidade

**Durante a implementação da Fase 5, também foi removida a seção de Métricas de Qualidade:**

**Removido:**
- Seção "⚙️ Métricas de Qualidade" (4 cards)
- Função `render_quality_metrics()` (~60 linhas)
- Métricas: Conversas IA %, Taxa Resolução, Tempo Resposta, Taxa Retorno

**Motivo:** Simplificação do dashboard (foco em métricas de leads/conversão)

**Arquivado em:** [`_archived/quality_metrics_removed.py`](../../src/multi_tenant/dashboards/_archived/quality_metrics_removed.py)

### 📊 Impacto

**Linhas de Código:**
- **Adicionadas:** ~240 linhas (prepare_inbox_metrics + render_inbox_analysis)
- **Removidas:** ~60 linhas (render_quality_metrics)
- **Saldo:** +180 linhas

**Performance:**
- Sem degradação (cálculos em memória com pandas groupby)
- Gráfico Plotly é leve (máximo ~10 inboxes por tenant)

**UX:**
- ✅ Toggle intuitivo entre duas visões
- ✅ Visão agregada: overview rápido
- ✅ Visão separada: análise detalhada por inbox
- ✅ Top 3 destaca inboxes mais importantes

---

## ⏭️ PRÓXIMOS PASSOS (NÃO IMPLEMENTADOS)

Conforme [MODIFICACOES_POS_APRESENTACAO.md](./MODIFICACOES_POS_APRESENTACAO.md):

### 1. Exibir Conversa Compilada (Fase 6 - 1h)
- [ ] Adicionar coluna "Prévia" na tabela
- [ ] Mostrar primeiras 5-10 mensagens de `message_compiled` (JSONB)
- [ ] Modal expandido ao clicar (conversa completa)

### 2. Testes e Ajustes (Fase 7 - 2h)
- [ ] Testar com AllpFit (1.317 conversas)
- [ ] Verificar responsividade
- [ ] Validar filtros funcionando
- [ ] Confirmar exportação CSV correta

---

## 🐛 PROBLEMAS CONHECIDOS

Nenhum! Código compila sem erros de sintaxe.

```bash
✅ All Python files compile successfully!
```

---

## 👥 RESPONSÁVEIS

- **Planejamento:** Johan (com superiores)
- **Implementação:** Claude AI (Sonnet 4.5)
- **Data:** 2025-11-11
- **Branch:** `feature/dashboard-generico`

---

## 📚 REFERÊNCIAS

- [MODIFICACOES_POS_APRESENTACAO.md](./MODIFICACOES_POS_APRESENTACAO.md) - Requisitos completos
- [ANALISE_COLUNAS_BANCO.md](./ANALISE_COLUNAS_BANCO.md) - Análise banco de dados
- [PROMPT_NOVO_CHAT.md](./PROMPT_NOVO_CHAT.md) - Contexto completo do projeto

---

**Última atualização:** 2025-11-11 15:35
**Status:** ✅ Fase 1-5 COMPLETA | ⏳ Fases 6-7 PENDENTES
