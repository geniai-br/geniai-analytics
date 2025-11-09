# Análise Comparativa: Dashboard Single-Tenant vs Multi-Tenant
## Recomendações de Melhorias para o Dashboard Multi-Tenant

**Data da Análise:** 2025-11-07  
**Status:** v1.0 - Priorizado por Value-Add

---

## 1. COMPARAÇÃO DE MÉTRICAS ATUAIS

### Dashboard Single-Tenant (AllpFit - Dashboard Principal)
**Localização:** `/src/app/dashboard.py`

#### KPIs Principais (Seção 1)
| Métrica | Descrição | Campo BD |
|---------|-----------|----------|
| **Total Contatos** | Leads únicos que engajaram (≥1 msg) | `contact_messages_count > 0` |
| **Conversas IA** | 100% automático, sem humano | `has_human_intervention = FALSE` |
| **Conversas Humano** | Com intervenção da equipe | `has_human_intervention = TRUE` |
| **Visitas Agendadas** | Detectadas na conversa (GPT-4) | `visit_scheduled = TRUE` |
| **Vendas/Tráfego** | Leads bot → CRM (match real) | `crm_converted = TRUE` |
| **Vendas/Geral** | Total clientes CRM | Base EVO CRM |

#### Seção Daily (Resultado Diário)
| Métrica | Descrição | Campo BD |
|---------|-----------|----------|
| **Novos Leads** | 1º contato HOJE | `conversation_date = TODAY` |
| **Visitas Dia** | Agendadas para HOJE | Filtro temporal |
| **Vendas Dia** | Conversões HOJE | Filtro temporal |
| **Total Conversas Dia** | Novas + reabertas HOJE | `last_activity_at = TODAY` |
| **Novas Conversas** | 1º contato HOJE | `conversation_date = TODAY` |
| **Conversas Reabertas** | Retorno de leads antigos | `conversation_date < TODAY` AND `last_activity_at = TODAY` |

#### Gráficos & Visualizações
| Gráfico | Dados | Campo BD |
|---------|-------|----------|
| **Média Leads/Dia (30d)** | Barras + linha de média | `conversation_date` (agrupado) |
| **Distribuição Período Dia** | Manhã/Tarde/Noite/Madrugada | `conversation_period` |

#### Análise GeniAI (Filtros Avançados)
| Coluna | Descrição |
|--------|-----------|
| Probabilidade (0-5) | Score de conversão |
| Condição Física | Sedentário/Iniciante/Avançado |
| Objetivo | Perda peso/Ganho massa/Saúde |
| Período | Data primeiro/última conversa |
| Análise IA | Insights automáticos |
| Sugestão Disparo | Recomendação de follow-up |

#### Conversões Reais (Bot → CRM)
| Campo | Descrição |
|-------|-----------|
| Conversões Identificadas | Links bot ↔ CRM |
| Taxa Conversão % | (Vendas Tráfego / Vendas Geral) * 100 |
| Detalhe Conversões | Tabela com data conversa/cadastro/dias |

---

### Dashboard Multi-Tenant (Client Dashboard)
**Localização:** `/src/multi_tenant/dashboards/client_dashboard.py`

#### KPIs Implementados (Seção Atual)
| Métrica | Descrição | Campo BD |
|---------|-----------|----------|
| **Total Contatos** | Todas as conversas | `len(df)` |
| **Leads** | Identificados como leads | `is_lead = TRUE` |
| **Visitas Agendadas** | Agendamentos confirmados | `visit_scheduled = TRUE` |
| **Conversões CRM** | Convertidos no CRM | `crm_converted = TRUE` |
| **Taxa Conversão** | (Leads / Total Contatos) % | Cálculo simples |

#### Funil de Conversão (Visual)
| Etapa | Descrição | Cálculo |
|-------|-----------|---------|
| Leads Gerados | Total leads | `count(is_lead=TRUE)` |
| Visitas Agendadas | % de leads com visita | `(visit_scheduled / leads) * 100` |
| Conversões CRM | % de visitas convertidas | `(crm_converted / visits) * 100` |

#### Gráficos
| Gráfico | Dados |
|---------|-------|
| **Leads por Dia** | Barras simples |
| **Leads por Inbox** | Barras por inbox |
| **Distribuição Score IA** | Barras com resumo |

#### Tabela de Leads
| Coluna | Dados |
|--------|-------|
| ID Conversa | `conversation_display_id` |
| Nome / Telefone | Contato |
| Data | `conversation_date` |
| Lead / Visita / CRM | Flags booleanas (✅/❌) |
| Classificação IA | Alto/Médio/Baixo/N/A |
| Score IA % | `ai_probability_score` |

---

## 2. MÉTRICAS SUGERIDAS PARA IMPLEMENTAR

### PRIORIDADE 1: High Value + Fácil Implementação

#### 2.1 - Métricas de Qualidade de Conversa
**Justificativa:** Diferenciam leads de qualidade. Dados 100% disponíveis.

| Métrica | Descrição | Campo BD | Impacto |
|---------|-----------|----------|---------|
| **Conversas com IA (%)** | % de conversas 100% automáticas | `has_human_intervention` | ✅ ROI: Reduz custo operacional |
| **Conversas com Humano (%)** | % com intervenção humana | `has_human_intervention = TRUE` | ✅ Indica engajamento complexo |
| **Tempo Resposta Média** | 1º resposta em minutos | `first_response_time_minutes` | ✅ KPI de SLA |
| **Taxa Resolução (%)** | % conversas resolvidas | `is_resolved` | ✅ Indicador de eficiência |

**Dados Disponíveis em `conversations_analytics`:**
```sql
- has_human_intervention (boolean)
- first_response_time_minutes (int)
- is_resolved (boolean)
```

**Local de Implementação:** Adicionar em `calculate_metrics()` do multi-tenant
```python
def calculate_metrics(df):
    # Existentes...
    metrics['ai_conversations'] = len(df[df['has_human_intervention'] == False])
    metrics['human_conversations'] = len(df[df['has_human_intervention'] == True])
    metrics['avg_response_time'] = df['first_response_time_minutes'].mean()
    metrics['resolution_rate'] = (len(df[df['is_resolved'] == True]) / len(df)) * 100
```

---

#### 2.2 - Distribuição por Período do Dia
**Justificativa:** Otimização de horários de atendimento. Impacto em planejamento de equipe.

| Métrica | Descrição | Campo BD | 
|---------|-----------|----------|
| **Leads Manhã (%)** | 6h-12h | `conversation_period = 'Manhã'` |
| **Leads Tarde (%)** | 12h-18h | `conversation_period = 'Tarde'` |
| **Leads Noite (%)** | 18h-24h | `conversation_period = 'Noite'` |
| **Leads Madrugada (%)** | 0h-6h | `conversation_period = 'Madrugada'` |

**Dados Disponíveis:** `conversation_period` já vem do SQL
**Local:** Novo gráfico em `render_leads_chart()` - lado do existente "Leads por Dia"

---

#### 2.3 - Métricas Diárias (Comparação D-1)
**Justificativa:** Rastrear tendência de curto prazo. Essencial para decisões operacionais.

| Métrica | Descrição | Campo BD | Impacto |
|---------|-----------|----------|---------|
| **Novos Leads Hoje vs Ontem** | Variação % | `conversation_date = TODAY` | ✅ Tendência |
| **Conversas Ativas Hoje vs Ontem** | Total com atividade | `last_activity_at = TODAY` | ✅ Throughput |
| **Conversas Reabertas** | Leads voltando | `conversation_date < TODAY` AND `last_activity_at = TODAY` | ✅ Reengajamento |

**Local:** Nova seção "Resultado Diário" semelhante ao single-tenant
- Implementar na função `show_client_dashboard()`
- Usar filtro temporal para comparação D-1

---

### PRIORIDADE 2: Value Médio + Melhor UX

#### 2.4 - Estatísticas de Mensagens
**Justificativa:** Indicadores de engagement. Dados disponíveis em `message_stats_complete`.

| Métrica | Descrição | Campo BD | Uso |
|---------|-----------|----------|-----|
| **Total Mensagens (Média)** | Msg por conversa | `t_messages` / `count(conversations)` | Qualidade |
| **Taxa Resposta (%)** | Leads que responderam | `contact_messages_count > 0` | Engagement |
| **Tempo Médio Conversa** | Segundos | `conversation_duration_seconds` | Qualidade |
| **Mensagem Média (Caracteres)** | Tamanho msg | `avg_message_length` | Profundidade |

**Local:** Card adicional em `render_kpis()` ou expander colapsável

---

#### 2.5 - Satisfaction & Feedback (CSAT)
**Justificativa:** Multi-tenant pode querer acompanhar satisfação. Dados em `vw_csat_base`.

| Métrica | Descrição | Campo BD | 
|---------|-----------|----------|
| **CSAT Médio** | Rating 1-5 | `csat_rating` |
| **% Com Feedback** | Conversas com comentário | `has_written_feedback` |
| **Sentiment Geral** | Positivo/Neutro/Negativo | `csat_sentiment_category` |
| **NPS Category** | Promoters/Passives/Detractors | `csat_nps_category` |

**Dados Disponíveis:** `vw_conversations_analytics_final` tem todos esses campos
**Local:** Seção "Satisfação" com cards + gráfico de distribuição

---

#### 2.6 - Comparação com Período Anterior
**Justificativa:** Contexto histórico essencial para stakeholders.

| Métrica | Descrição | Cálculo |
|---------|-----------|---------|
| **Leads vs 30d Atrás** | Variação período | `leads_atual / leads_30d_atrás` |
| **Visitas vs 30d Atrás** | Variação período | `visits_atual / visits_30d_atrás` |
| **Taxa Conversão vs 30d** | Evolução | Compare período selecionado com 30d antes |

---

### PRIORIDADE 3: Nice-to-Have (Requer Análise)

#### 2.7 - Previsão/Trend Line
**Dados Necessários:** Histórico ≥ 60 dias  
**Complexidade:** Média (require regressão simples)  
**Value:** Bom para forecast, mas aguardar Fase 4

#### 2.8 - Análise de Funnels Customizados
**Dados Necessários:** Campos adicionais no CRM  
**Complexidade:** Alta  
**Value:** Ótimo, mas depender de integração CRM

---

## 3. DADOS DISPONÍVEIS EM `conversations_analytics`

### Campos Confirmados (Testados)
```python
# Conversas
conversation_id
conversation_display_id
conversation_created_at
conversation_date
inbox_id, inbox_name

# Contato
contact_name
contact_phone
contact_email

# Mensagens
t_messages (total)
contact_messages_count
user_messages_count

# Status
is_lead (boolean)
visit_scheduled (boolean)
crm_converted (boolean)
status (0=Aberta, 1=Resolvida, 2=Pendente)

# IA
ai_probability_label (Alto/Médio/Baixo)
ai_probability_score (0-100%)

# Performance
has_human_intervention (boolean)
first_response_time_minutes (int)
is_resolved (boolean)
conversation_duration_seconds (int)
avg_message_length (int)

# Temporal
conversation_period (Manhã/Tarde/Noite/Madrugada)
is_weekday (boolean)
is_business_hours (boolean)
```

### ⚠️ Campos NÃO Disponíveis (evitar)
```
- CSAT/Satisfaction (não mapeado em multi-tenant ainda - Fase 4)
- Conversões CRM Real (requer integração com EVO CRM - Fase 3)
- Análise Customizada (requer mais campos no bot)
- Histórico de Re-aberturas (exige JOIN temporal complexo)
```

---

## 4. RECOMENDAÇÕES DE IMPLEMENTAÇÃO POR FASE

### FASE 2.1 (Próximo Sprint) - Quick Wins

**Implementar:**
1. ✅ **Conversas IA vs Humano (%)** - 2h
   - Adicionar em `calculate_metrics()`
   - Renderizar em card adicional ou row 2 do KPI

2. ✅ **Distribuição Período Dia** - 2h
   - Copiar função `calculate_distribution_by_period()` do single-tenant
   - Gráfico lado a lado com "Leads por Dia"

3. ✅ **Taxa Resolução (%)** - 1h
   - Adicionar em `calculate_metrics()` + card em KPI

4. ✅ **Tempo Resposta Média** - 1h
   - Adicionar em `calculate_metrics()` + card ou tooltip

**Arquivo a Modificar:**
- `/src/multi_tenant/dashboards/client_dashboard.py`
  - Função `calculate_metrics()`
  - Função `render_kpis()`
  - Adicionar função `prepare_period_distribution()`

**Esforço:** 6h | **ROI:** Alto | **Risco:** Mínimo

---

### FASE 2.2 (Sprint +1) - Daily Metrics

**Implementar:**
1. ✅ **Seção "Resultado Diário"** - 4h
   - Semelhante ao single-tenant
   - Novos Leads vs Ontem
   - Total Conversas Ativas vs Ontem
   - Conversas Reabertas

**Arquivo:** `/src/multi_tenant/dashboards/client_dashboard.py`
- Função `calculate_daily_metrics()`
- Nova seção entre Header e KPIs

**Esforço:** 4h | **ROI:** Alto | **Risco:** Baixo

---

### FASE 2.3 (Roadmap) - Histórico & Comparação

**Implementar:**
1. ✅ **Comparação com Período Anterior** - 3h
   - Card mostrando variação %
   - Válido para leads, visitas, conversões

2. ✅ **Estatísticas de Mensagens** - 2h
   - Expander com tabela de stats
   - Tempo médio conversa, taxa resposta, etc

**Esforço:** 5h | **ROI:** Médio | **Risco:** Baixo

---

## 5. MÉTRICAS QUE NÃO DEVEM SER IMPLEMENTADAS

### ❌ Conversões CRM Real (Vendas/Tráfego)
**Motivo:** Requer integração com EVO CRM  
**Status:** Planejado para Fase 3 (ETL Multi-Tenant)  
**Impacto:** Crítico, mas aguardar pipeline dedicado  
**Alternativa Temporária:** Usar `crm_converted` flag da API

---

### ❌ Análise GeniAI com Filtros Avançados
**Motivo:** Requer tabela `vw_leads_nao_convertidos_com_ia` (single-tenant only)  
**Status:** Dados customizados por tenant  
**Complexidade:** Alta (requer normalização de análise entre tenants)  
**Timeline:** Fase 4+

---

### ❌ Score/Probabilidade Customizado por Tenant
**Motivo:** IA gera scores genéricos, não personalizados por academia  
**Status:** Requer retreinamento por tenant  
**ROI:** Baixo vs esforço  
**Alternativa:** Usar `ai_probability_label` existente

---

### ❌ Relatórios Automáticos via Email
**Motivo:** Requer sistema de alertas + integração email  
**Status:** Planejado para Fase 5  
**Prioridade:** Baixa (pode fazer via exportação CSV)

---

### ❌ Integração com WhatsApp Business API
**Motivo:** Fora do escopo de analytics  
**Status:** Arquitetura separada  
**Local:** Módulo de automação do bot

---

## 6. SUGESTÕES UX/UI PARA POSICIONAMENTO

### Layout Recomendado (Otimizado)

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Analytics - Cliente X                     👤 User 🚪  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Data] [Data] [Inbox ▼] [🔄 Atualizar]  ⏱ Próximo ETL  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ LINHA 1: KPIs PRINCIPAIS (5 cards)                      │
│  Total Contatos | Leads | Visitas | CRM | Taxa Conv    │
├─────────────────────────────────────────────────────────┤
│ LINHA 2: RESULTADO DIÁRIO (6 mini-cards) [NOVO]         │
│  Novos Hoje | Visitas Dia | Conversas Ativas | Reabertas│
├─────────────────────────────────────────────────────────┤
│ LINHA 3: KPIs DE QUALIDADE (4 cards) [NOVO]            │
│  IA % | Resolução % | Tempo Resposta | Engagement       │
├─────────────────────────────────────────────────────────┤
│ LINHA 4: FUNIL DE CONVERSÃO (3 cards, visual)           │
│  [Leads] → [Visitas (72%)] → [CRM (40%)]               │
├─────────────────────────────────────────────────────────┤
│ LINHA 5: GRÁFICOS (2 colunas)                           │
│  ┌─────────────────────┐  ┌──────────────────────┐      │
│  │ Leads por Dia       │  │ Distribuição Período │ [NOVO]│
│  │ (Barras + Média)    │  │ Manhã/Tarde/Noite    │      │
│  └─────────────────────┘  └──────────────────────┘      │
├─────────────────────────────────────────────────────────┤
│ LINHA 6: GRÁFICOS (2 colunas)                           │
│  ┌─────────────────────┐  ┌──────────────────────┐      │
│  │ Leads por Inbox     │  │ Score IA (Dist)      │      │
│  │ (Barras)            │  │ Alto/Médio/Baixo     │      │
│  └─────────────────────┘  └──────────────────────┘      │
├─────────────────────────────────────────────────────────┤
│ LINHA 7: TABELA DE LEADS                                │
│  [ID] [Nome] [Tel] [Data] [Lead] [Visita] [CRM] [Score] │
├─────────────────────────────────────────────────────────┤
│ ℹ️ Informações do Cliente (EXPANDER)                    │
│  Nome | Slug | Status | Plano | Inboxes | Período       │
└─────────────────────────────────────────────────────────┘
```

### Novas Seções Detalhadas

#### LINHA 2: Resultado Diário [NOVO - PRIORITY 2.2]
```python
st.markdown("### 📊 Resultado Diário")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Novos Leads", daily['novos_leads'], 
              delta=daily['novos_leads_perc'], help="1º contato hoje")

with col2:
    st.metric("Visitas Dia", daily['visitas_dia'], 
              help="Agendadas para hoje")

with col3:
    st.metric("Conversas Ativas", daily['total_conversas_dia'], 
              delta=daily['total_conversas_dia_perc'])

with col4:
    st.metric("Novas Conversas", daily['conversas_dia'], 
              delta=daily['conversas_dia_perc'], help="1º contato")

with col5:
    st.metric("Reabertas", daily['conversas_reabertas'], 
              delta=daily['conversas_reabertas_perc'], help="Retorno leads")

with col6:
    st.metric("Conversas/Lead", 
              f"{(daily['total_conversas_dia'] / max(daily['novos_leads'],1)):.1f}", 
              help="Engajamento médio")
```

#### LINHA 3: Qualidade [NOVO - PRIORITY 2.1]
```python
st.markdown("### ⚙️ Métricas de Qualidade")

col1, col2, col3, col4 = st.columns(4)

with col1:
    pct_ai = (metrics['ai_conversations'] / len(df)) * 100
    st.metric("Conversas IA %", f"{pct_ai:.1f}%", 
              help="100% automáticas, sem humano")

with col2:
    st.metric("Taxa Resolução", f"{metrics['resolution_rate']:.1f}%", 
              help="Conversas resolvidas")

with col3:
    st.metric("Tempo Resposta", f"{metrics['avg_response_time']:.0f}min", 
              help="Primeira resposta")

with col4:
    pct_engagement = (metrics['total_contacts'] / len(df)) * 100
    st.metric("Engagement %", f"{pct_engagement:.1f}%", 
              help="Contacts que responderam")
```

#### Gráfico de Período [NOVO - PRIORITY 2.1]
```python
def render_period_distribution(df):
    """Novo gráfico: distribuição por período do dia"""
    period_dist = df.groupby('conversation_period').size()
    
    st.bar_chart(period_dist, use_container_width=True)
    
    with st.columns(4)[1]:  # Resumo ao lado
        for period, count in period_dist.items():
            st.caption(f"{period}: {count} leads")
```

---

## 7. CHECKLIST DE IMPLEMENTAÇÃO

### FASE 2.1 (Próximo Sprint)
- [ ] Função `calculate_ai_conversation_rate()` em metrics
- [ ] Função `calculate_resolution_rate()` em metrics
- [ ] Função `prepare_period_distribution()` em metrics
- [ ] Adicionar 3 novos cards em `render_kpis()` (IA%, Resolução%, Período)
- [ ] Novo gráfico lado a lado com "Leads por Dia"
- [ ] Testes unitários para cálculos
- [ ] Atualizar documentação em `/docs/`

### FASE 2.2 (Sprint +1)
- [ ] Função `calculate_daily_metrics()` (copiar do single-tenant)
- [ ] Nova seção "Resultado Diário" com 6 cards
- [ ] Testes com dados multi-tenant
- [ ] Validar comparação D-1

### FASE 2.3 (Roadmap)
- [ ] Comparação período anterior (30d)
- [ ] Seção de estatísticas de mensagens (expander)
- [ ] Gráfico de evolução temporal

---

## 8. SUMMARY: Priorização

| Métrica | Prioridade | Esforço | ROI | Status |
|---------|-----------|---------|-----|--------|
| **Conversas IA %** | P1 | 1h | Alto | ✅ Quick Win |
| **Distribuição Período** | P1 | 2h | Alto | ✅ Quick Win |
| **Taxa Resolução** | P1 | 1h | Alto | ✅ Quick Win |
| **Tempo Resposta Média** | P1 | 1h | Médio | ✅ Quick Win |
| **Resultado Diário** | P2 | 4h | Alto | ⏳ Sprint +1 |
| **Comparação 30d** | P3 | 3h | Médio | 📅 Roadmap |
| **Estatísticas Msg** | P3 | 2h | Médio | 📅 Roadmap |
| **CSAT/Satisfaction** | P4 | 5h | Médio | ⚠️ Fase 4 |
| **Conversões CRM Real** | P4 | 8h | Crítico | ⚠️ Fase 3 |
| **Análise GeniAI** | P5 | 12h | Alto | ❌ Descontinuar |

---

## 9. CONCLUSÃO

### ✅ Recomendação Executiva

Implementar **FASE 2.1** (6h) nos próximos 2 sprints para:
- **+4 métricas de qualidade** que agregam value real
- **0 dependências externas** - dados já existem
- **ROI imediato** - melhor visibilidade de operação
- **Sem piora da UX** - extensão natural do layout

Aguardar **Fase 3 (ETL)** para conversões CRM real (critical mas dependência).

Descontinuar análise GeniAI personalizada no multi-tenant (use genérica com IA labels).

---

**Próximos Passos:**
1. Validar com Product Owner as prioridades
2. Criar tickets no backlog para FASE 2.1
3. Definir sprint de implementação
4. Coordenar com Fase 3 (ETL/CRM) para dependências

