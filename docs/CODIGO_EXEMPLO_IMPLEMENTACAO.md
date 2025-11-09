# Código de Exemplo: Implementação FASE 2.1

**Objetivo:** Mostrar exatamente o que adicionar ao `client_dashboard.py`

---

## 1. ESTENDER `calculate_metrics()` 

### Arquivo: `/src/multi_tenant/dashboards/client_dashboard.py`

**Localização Atual (linha ~182):**
```python
def calculate_metrics(df):
    """Calcula métricas principais do dashboard"""
    if df.empty:
        return {
            'total_contacts': 0,
            'ai_conversations': 0,
            'leads': 0,
            'visits_scheduled': 0,
            'crm_converted': 0,
        }

    metrics = {
        'total_contacts': len(df),
        'ai_conversations': len(df[df['bot_messages'] > 0]),
        'leads': len(df[df['is_lead'] == True]),
        'visits_scheduled': len(df[df['visit_scheduled'] == True]),
        'crm_converted': len(df[df['crm_converted'] == True]),
    }

    return metrics
```

**Substituir por:**
```python
def calculate_metrics(df):
    """
    Calcula métricas principais do dashboard
    
    Agora inclui:
    - Métricas de qualidade (IA%, Resolução, etc)
    - Performance (tempo resposta)
    """
    if df.empty:
        return {
            'total_contacts': 0,
            'ai_conversations': 0,
            'human_conversations': 0,
            'leads': 0,
            'visits_scheduled': 0,
            'crm_converted': 0,
            'resolution_rate': 0.0,
            'avg_response_time': 0.0,
        }

    total = len(df)
    
    # Métricas Existentes
    metrics = {
        'total_contacts': total,
        'ai_conversations': len(df[df['has_human_intervention'] == False]),
        'human_conversations': len(df[df['has_human_intervention'] == True]),
        'leads': len(df[df['is_lead'] == True]),
        'visits_scheduled': len(df[df['visit_scheduled'] == True]),
        'crm_converted': len(df[df['crm_converted'] == True]),
    }
    
    # NOVAS - Métricas de Qualidade [FASE 2.1]
    resolved_count = len(df[df['is_resolved'] == True]) if 'is_resolved' in df.columns else 0
    metrics['resolution_rate'] = (resolved_count / total * 100) if total > 0 else 0.0
    
    # Tempo resposta médio (em minutos)
    if 'first_response_time_minutes' in df.columns:
        valid_times = df[df['first_response_time_minutes'].notna()]['first_response_time_minutes']
        metrics['avg_response_time'] = valid_times.mean() if len(valid_times) > 0 else 0.0
    else:
        metrics['avg_response_time'] = 0.0

    return metrics
```

---

## 2. NOVA FUNÇÃO: Distribuição por Período

### Adicionar Após `prepare_score_distribution()`:

```python
def prepare_period_distribution(df):
    """
    Prepara dados de distribuição de conversas por período do dia
    
    Args:
        df: DataFrame com conversas
    
    Returns:
        pd.DataFrame: Distribuição por período (Manhã/Tarde/Noite/Madrugada)
    """
    if df.empty or 'conversation_period' not in df.columns:
        return pd.DataFrame(columns=['Período', 'Quantidade'])
    
    # Agrupar por período
    period_dist = df.groupby('conversation_period').size().reset_index(name='Quantidade')
    period_dist.rename(columns={'conversation_period': 'Período'}, inplace=True)
    
    # Ordenar por ordem lógica dos períodos
    period_order = {'Manhã': 1, 'Tarde': 2, 'Noite': 3, 'Madrugada': 4}
    period_dist['_order'] = period_dist['Período'].map(period_order)
    period_dist = period_dist.sort_values('_order').drop('_order', axis=1)
    
    return period_dist
```

---

## 3. NOVA FUNÇÃO: Render KPIs de Qualidade

### Adicionar Após `render_kpis()`:

```python
def render_quality_metrics(metrics, df):
    """
    Renderiza métrica de qualidade (IA%, Resolução%, Tempo Resposta)
    
    Args:
        metrics: Dict com métricas calculadas
        df: DataFrame com conversas
    """
    st.divider()
    st.subheader("⚙️ Métricas de Qualidade")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(df) if not df.empty else 1
    
    with col1:
        pct_ai = (metrics['ai_conversations'] / total * 100) if total > 0 else 0
        st.metric(
            "Conversas IA %",
            f"{pct_ai:.1f}%",
            help="Percentual de conversas 100% automáticas (sem intervenção humana)"
        )
    
    with col2:
        st.metric(
            "Taxa Resolução",
            f"{metrics['resolution_rate']:.1f}%",
            help="Percentual de conversas resolvidas"
        )
    
    with col3:
        st.metric(
            "Tempo Resposta",
            f"{metrics['avg_response_time']:.0f} min",
            help="Tempo médio da primeira resposta"
        )
    
    with col4:
        pct_engagement = (metrics['total_contacts'] / total * 100) if total > 0 else 0
        st.metric(
            "Engagement %",
            f"{pct_engagement:.1f}%",
            help="Percentual de contatos que enviaram mensagens"
        )
```

---

## 4. NOVO GRÁFICO: Distribuição por Período

### Adicionar Após `render_score_distribution_chart()`:

```python
def render_period_distribution_chart(period_dist):
    """
    Renderiza gráfico de distribuição por período do dia
    
    Args:
        period_dist: DataFrame com distribuição de períodos
    """
    if period_dist.empty:
        st.info("ℹ️ Nenhum dado para exibir")
        return
    
    st.subheader("🕐 Distribuição por Período do Dia")
    
    # Gráfico de barras
    st.bar_chart(period_dist.set_index('Período')['Quantidade'], use_container_width=True)
    
    # Resumo em colunas
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    
    for idx, (_, row) in enumerate(period_dist.iterrows()):
        if idx < 4:
            with cols[idx]:
                st.metric(row['Período'], f"{row['Quantidade']} leads")
```

---

## 5. INTEGRAR NO `show_client_dashboard()`

### Localização: Linha ~758 (após carregar dados)

**Adicionar após a seção "ANÁLISE DE LEADS":**

```python
    # === GRÁFICOS === (linhas ~759-777)
    st.subheader("📊 Análise de Leads")

    # Linha 1: Leads por dia (largura completa)
    leads_by_day = prepare_leads_by_day(df)
    render_leads_chart(leads_by_day)

    st.divider()

    # Linha 2: Leads por inbox + Distribuição de Score (lado a lado)
    col1, col2 = st.columns(2)

    with col1:
        leads_by_inbox = prepare_leads_by_inbox(df)
        render_leads_by_inbox_chart(leads_by_inbox)

    with col2:
        score_dist = prepare_score_distribution(df)
        render_score_distribution_chart(score_dist)

    st.divider()
    
    # [NOVO] Linha 3: Distribuição por Período + Qualidade
    # Adicionar AQUI:
    
    render_quality_metrics(metrics, df)  # [NOVO]
    
    st.divider()
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        period_dist = prepare_period_distribution(df)
        render_period_distribution_chart(period_dist)  # [NOVO]
    
    with col2:
        st.subheader("📋 Resumo Qualidade")
        st.write(f"""
        - **IA Automáticas:** {metrics['ai_conversations']} conversas
        - **Com Humano:** {metrics['human_conversations']} conversas
        - **Taxa Resolução:** {metrics['resolution_rate']:.1f}%
        - **Tempo Resposta:** {metrics['avg_response_time']:.0f}min
        """)

    st.divider()

    # === TABELA DE LEADS === (linhas ~780-782, permanece igual)
    render_leads_table(df, tenant_name, date_start, date_end)
```

---

## 6. IMPORTS NECESSÁRIOS

### Verificar No Topo do Arquivo

Ja estão presentes, mas confirmar:

```python
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
```

---

## 7. ANTES E DEPOIS (Visual)

### ANTES (Current)
```
┌─────────────────────┐
│ KPIs (5 cards)      │
│ Total|Leads|...     │
├─────────────────────┤
│ Funil (3 cards)     │
│ Leads→Visitas→CRM   │
├─────────────────────┤
│ Gráficos (2x2)      │
│ [Leads/Dia][Inbox]  │
│ [Score]             │
├─────────────────────┤
│ Tabela              │
└─────────────────────┘
```

### DEPOIS (Com FASE 2.1)
```
┌─────────────────────┐
│ KPIs (5 cards)      │
│ Total|Leads|...     │
├─────────────────────┤
│ QUALIDADE (4 cards) │ [NOVO]
│ IA%|Resolução|Resp  │
├─────────────────────┤
│ Funil (3 cards)     │
│ Leads→Visitas→CRM   │
├─────────────────────┤
│ Gráficos (2x2)      │
│ [Leads/Dia][Período]│ [Período é NOVO]
│ [Inbox][Score]      │
├─────────────────────┤
│ Tabela              │
└─────────────────────┘
```

---

## 8. TESTE UNITÁRIO

### Criar arquivo: `/tests/test_client_dashboard_metrics.py`

```python
import pandas as pd
import sys
from pathlib import Path

# Simular importação
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_calculate_metrics_with_quality():
    """Testa cálculo de métricas com novos campos"""
    
    # Mock data
    df = pd.DataFrame({
        'conversation_id': [1, 2, 3, 4, 5],
        'is_lead': [True, True, False, True, True],
        'visit_scheduled': [True, False, False, True, False],
        'crm_converted': [False, True, False, False, True],
        'has_human_intervention': [False, True, False, False, True],
        'is_resolved': [True, True, False, True, False],
        'first_response_time_minutes': [5, 10, 15, 3, 8],
    })
    
    # Simular função
    def calculate_metrics(df):
        total = len(df)
        resolved = len(df[df['is_resolved'] == True])
        
        return {
            'total_contacts': total,
            'leads': len(df[df['is_lead'] == True]),
            'ai_conversations': len(df[df['has_human_intervention'] == False]),
            'human_conversations': len(df[df['has_human_intervention'] == True]),
            'resolution_rate': (resolved / total * 100) if total > 0 else 0,
            'avg_response_time': df['first_response_time_minutes'].mean(),
        }
    
    metrics = calculate_metrics(df)
    
    # Asserts
    assert metrics['total_contacts'] == 5
    assert metrics['leads'] == 4
    assert metrics['ai_conversations'] == 3  # FALSE, FALSE, FALSE
    assert metrics['human_conversations'] == 2  # TRUE, TRUE
    assert metrics['resolution_rate'] == 60.0  # 3 de 5
    assert metrics['avg_response_time'] == 8.2  # (5+10+15+3+8)/5
    
    print("✅ Todos os testes passaram!")

if __name__ == "__main__":
    test_calculate_metrics_with_quality()
```

---

## 9. CHECKLIST DE IMPLEMENTAÇÃO

### Antes de Começar
- [ ] Confirmar dados do BD estão em `conversations_analytics`
- [ ] Verificar campos: `has_human_intervention`, `is_resolved`, `first_response_time_minutes`, `conversation_period`
- [ ] Fazer backup do arquivo original

### Implementação
- [ ] Estender função `calculate_metrics()`
- [ ] Adicionar função `prepare_period_distribution()`
- [ ] Adicionar função `render_quality_metrics()`
- [ ] Adicionar função `render_period_distribution_chart()`
- [ ] Integrar no fluxo do `show_client_dashboard()`
- [ ] Testar com dados reais do DB

### Validação
- [ ] Verificar se KPIs aparecem corretamente
- [ ] Testar com múltiplos tenants (RLS)
- [ ] Validar gráficos renderizam corretamente
- [ ] Testar responsividade mobile
- [ ] Verificar performance (cache)

### Deploy
- [ ] Criar PR com descrição clara
- [ ] Code review
- [ ] Merge para main/staging
- [ ] Deploy em produção

---

## 10. TROUBLESHOOTING

### Campo `conversation_period` não existe
**Solução:** Verificar se tabela `conversations_analytics` foi atualizada com view completa
```sql
SELECT DISTINCT conversation_period FROM conversations_analytics LIMIT 5;
```

### Valores NaN em `first_response_time_minutes`
**Solução:** Já tratado no código com `.notna()` e `.mean()`
```python
valid_times = df[df['first_response_time_minutes'].notna()]['first_response_time_minutes']
metrics['avg_response_time'] = valid_times.mean() if len(valid_times) > 0 else 0.0
```

### RLS não filtra corretamente
**Solução:** Confirmar que `set_rls_context()` foi chamado antes de `load_conversations()`

---

**Total de Linhas de Código:** ~80 linhas novas  
**Arquivo Principal:** `client_dashboard.py`  
**Tempo Estimado:** 2-3 horas (implementação + testes)  
**Complexidade:** Baixa (cópia + adaptação)

