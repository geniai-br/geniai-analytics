# 📊 Dashboard AllpFit Analytics - KPIs Completos

## 🎯 Estrutura do Dashboard: Do Macro ao Detalhamento

```
NÍVEL 1: Visão Executiva (Overview Macro)
    ↓
NÍVEL 2: Análise Operacional (Performance)
    ↓
NÍVEL 3: Análise de Qualidade (CSAT & IA)
    ↓
NÍVEL 4: Análise por Segmento (Canais, Agentes, Times)
    ↓
NÍVEL 5: Análise Temporal (Tendências)
    ↓
NÍVEL 6: Drill-Down Individual (Conversas Específicas)
```

---

# 📈 NÍVEL 1: VISÃO EXECUTIVA (Overview Macro)

## **🎯 Objetivo**: Responder "Como está o atendimento de forma geral?"

### **KPIs Principais (Cards no Topo)**

#### **1.1. Volume Geral**
```python
📊 Total de Conversas
- Valor: COUNT(conversation_id)
- Período: Último mês / Hoje / Esta semana
- Comparação: vs período anterior (+15% ↗️)
- Cor: Azul

📊 Conversas Ativas
- Valor: COUNT(*) WHERE status IN ('open', 'pending')
- Cor: Laranja
- Alerta: >100 conversas (vermelho)

📊 Conversas Resolvidas
- Valor: COUNT(*) WHERE is_resolved = true
- Período: Hoje / Esta semana
- Cor: Verde

📊 Clientes Únicos Atendidos
- Valor: COUNT(DISTINCT contact_id)
- Período: Último mês
- Comparação: vs mês anterior
- Cor: Roxo
```

#### **1.2. Performance Geral**
```python
⏱️ Tempo Médio de Primeira Resposta
- Valor: AVG(first_response_time_seconds) / 60  # em minutos
- Meta: <5 minutos
- Cor: Verde (<5min), Amarelo (5-10min), Vermelho (>10min)
- Fórmula: ROUND(AVG(first_response_time_seconds) / 60, 1)

⏱️ Tempo Médio de Resolução
- Valor: AVG(conversation_duration_seconds) / 3600  # em horas
- Meta: <2 horas
- Fórmula: ROUND(AVG(conversation_duration_seconds) / 3600, 1)

📊 Taxa de Resolução
- Valor: (COUNT(*) WHERE is_resolved) / COUNT(*) * 100
- Meta: >80%
- Formato: 85.4%
- Cor: Verde (>80%), Amarelo (60-80%), Vermelho (<60%)
```

#### **1.3. Satisfação Geral**
```python
⭐ CSAT Médio (Rating)
- Valor: AVG(csat_rating)
- Escala: 1-5 estrelas
- Meta: >4.0
- Formato: 4.3 ⭐⭐⭐⭐
- Cor: Verde (>4), Amarelo (3-4), Vermelho (<3)

📊 Taxa de Resposta CSAT
- Valor: (COUNT(*) WHERE has_csat) / COUNT(*) * 100
- Meta: >30%
- Formato: 35.2%

😊 Sentimento Médio
- Valor: AVG(avg_sentiment_score)
- Escala: -1 a +1
- Formato: 0.65 (Positivo)
- Indicador: 😊 Positivo, 😐 Neutro, 😞 Negativo
```

#### **1.4. Eficiência da IA**
```python
🤖 Taxa de Resolução Automática (Bot)
- Valor: (COUNT(*) WHERE is_bot_resolved) / COUNT(*) * 100
- Meta: >40%
- Formato: 42.5%
- Cor: Verde (>40%), Amarelo (20-40%), Vermelho (<20%)

👤 Taxa de Intervenção Humana
- Valor: (COUNT(*) WHERE has_human_intervention) / COUNT(*) * 100
- Formato: 57.5%
- Complementar ao Bot

🔄 Taxa de Escalação
- Valor: (COUNT(*) WHERE has_human_intervention AND NOT is_bot_resolved) / COUNT(*) * 100
- Formato: 35.0%
```

---

### **Gráficos Macro (Visão Geral)**

#### **1. Linha do Tempo - Volume de Conversas**
```python
Tipo: Line Chart (Gráfico de Linha)
Eixo X: Data (conversation_date)
Eixo Y: COUNT(conversation_id)
Segmentação: Por status (Open, Pending, Resolved)
Período: Últimos 30 dias
Interatividade: Hover mostra detalhes por dia

SQL:
SELECT
    conversation_date,
    status,
    COUNT(*) as total
FROM vw_conversas_analytics
WHERE conversation_date >= CURRENT_DATE - 30
GROUP BY conversation_date, status
ORDER BY conversation_date
```

#### **2. Pizza - Distribuição por Canal**
```python
Tipo: Pie Chart (Pizza)
Valores: COUNT(conversation_id) por inbox_name
Labels: inbox_name (WhatsApp, Instagram, Email, etc)
Cores: Diferentes por canal
Percentual: Mostrar %

SQL:
SELECT
    inbox_name,
    inbox_channel_type,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentual
FROM vw_conversas_analytics
GROUP BY inbox_name, inbox_channel_type
ORDER BY total DESC
```

#### **3. Barra Horizontal - Status das Conversas**
```python
Tipo: Horizontal Bar Chart
Eixo X: COUNT(*)
Eixo Y: Status (Open, Pending, Resolved, Closed)
Cores: Verde (Resolved), Amarelo (Pending), Laranja (Open)

SQL:
SELECT
    status,
    COUNT(*) as total
FROM vw_conversas_analytics
GROUP BY status
ORDER BY total DESC
```

#### **4. Funil de Conversão**
```python
Tipo: Funnel Chart
Etapas:
  1. Conversas Iniciadas: 100%
  2. Primeira Resposta: 95%
  3. Com Atendente: 60%
  4. Resolvidas: 80%
  5. Avaliadas (CSAT): 35%

SQL:
SELECT
    COUNT(*) as iniciadas,
    COUNT(*) FILTER (WHERE first_response_time_seconds IS NOT NULL) as com_resposta,
    COUNT(*) FILTER (WHERE has_human_intervention) as com_atendente,
    COUNT(*) FILTER (WHERE is_resolved) as resolvidas,
    COUNT(*) FILTER (WHERE has_csat) as avaliadas
FROM vw_conversas_analytics
```

---

# 📊 NÍVEL 2: ANÁLISE OPERACIONAL (Performance)

## **🎯 Objetivo**: "Onde estão os gargalos operacionais?"

### **KPIs Operacionais**

#### **2.1. Filas e Espera**
```python
⏰ Conversas Aguardando Resposta
- Valor: COUNT(*) WHERE status = 'pending' AND waiting_since IS NOT NULL
- Ordenar: Por tempo de espera (DESC)
- Alerta: >50 conversas ou espera >2h

⏱️ Tempo Médio de Espera
- Valor: AVG(CURRENT_TIMESTAMP - waiting_since)
- Filtro: WHERE status = 'pending'
- Formato: "2h 35min"

📊 Conversas Sem Atribuição
- Valor: COUNT(*) WHERE NOT is_assigned AND status IN ('open', 'pending')
- Alerta: >20 conversas
```

#### **2.2. Mensagens e Interações**
```python
💬 Total de Mensagens
- Valor: SUM(total_messages)
- Período: Hoje / Esta semana

💬 Média de Mensagens por Conversa
- Valor: AVG(total_messages)
- Benchmark: 5-10 mensagens = ideal

📝 Distribuição de Mensagens
- Agente: AVG(user_messages_count)
- Cliente: AVG(contact_messages_count)
- Ratio: user_messages / contact_messages (ideal: ~1.0)
```

#### **2.3. Produtividade**
```python
👤 Conversas por Agente (Média)
- Valor: COUNT(*) / COUNT(DISTINCT assignee_id)
- Período: Hoje / Esta semana

⚡ Velocidade Média de Resposta
- Valor: PERCENTILE(first_response_time_seconds, 0.5) / 60  # mediana
- Formato: "3.2 min"

🎯 Taxa de Primeira Resolução (FCR)
- Valor: COUNT(*) WHERE total_messages <= 5 AND is_resolved / COUNT(*)
- Meta: >60%
```

---

### **Gráficos Operacionais**

#### **1. Heatmap - Volume por Dia/Hora**
```python
Tipo: Heatmap
Eixo X: Hora do dia (0-23)
Eixo Y: Dia da semana (Segunda-Domingo)
Cor: Intensidade = volume de conversas
Objetivo: Identificar picos de demanda

SQL:
SELECT
    conversation_day_name,
    conversation_hour,
    COUNT(*) as volume
FROM vw_conversas_analytics
GROUP BY conversation_day_name, conversation_day_of_week, conversation_hour
ORDER BY conversation_day_of_week, conversation_hour
```

#### **2. Box Plot - Tempo de Resposta**
```python
Tipo: Box Plot (Caixa com Whiskers)
Eixo X: Canal (inbox_name)
Eixo Y: first_response_time_seconds / 60
Mostra: Min, Q1, Mediana, Q3, Max, Outliers
Objetivo: Ver distribuição e outliers

SQL:
SELECT
    inbox_name,
    first_response_time_seconds / 60.0 as response_minutes
FROM vw_conversas_analytics
WHERE first_response_time_seconds IS NOT NULL
```

#### **3. Barra Empilhada - Mensagens por Tipo**
```python
Tipo: Stacked Bar Chart
Eixo X: Data
Eixo Y: COUNT(*)
Segmentos: user_messages_count, contact_messages_count
Cores: Azul (Agente), Verde (Cliente)

SQL:
SELECT
    conversation_date,
    SUM(user_messages_count) as msgs_agente,
    SUM(contact_messages_count) as msgs_cliente,
    SUM(total_messages) as msgs_total
FROM vw_conversas_analytics
GROUP BY conversation_date
ORDER BY conversation_date
```

---

# ⭐ NÍVEL 3: ANÁLISE DE QUALIDADE (CSAT & IA)

## **🎯 Objetivo**: "A qualidade do atendimento está boa?"

### **KPIs de Qualidade**

#### **3.1. CSAT Detalhado**
```python
⭐ Distribuição de Ratings
- 5 estrelas: COUNT(*) WHERE csat_rating = 5
- 4 estrelas: COUNT(*) WHERE csat_rating = 4
- 3 estrelas: COUNT(*) WHERE csat_rating = 3
- 2 estrelas: COUNT(*) WHERE csat_rating = 2
- 1 estrela: COUNT(*) WHERE csat_rating = 1
- Gráfico: Barra horizontal

📊 NPS (Net Promoter Score)
- Promotores: (rating 5) / total * 100
- Neutros: (rating 3-4) / total * 100
- Detratores: (rating 1-2) / total * 100
- NPS = % Promotores - % Detratores

😊 Sentimento por Rating
- Correlação: csat_rating vs avg_sentiment_score
- Gráfico: Scatter plot
```

#### **3.2. Análise de Feedbacks**
```python
💬 Total de Feedbacks Escritos
- Valor: COUNT(*) WHERE csat_feedback IS NOT NULL AND csat_feedback != ''
- Taxa: (com feedback / total_csat) * 100

🔝 Palavras Mais Mencionadas (Positivas)
- Fonte: csat_feedback
- Filtro: WHERE csat_rating >= 4
- Processamento: NLP / Word frequency
- Visualização: Word Cloud

⚠️ Palavras Mais Mencionadas (Negativas)
- Fonte: csat_feedback
- Filtro: WHERE csat_rating <= 2
- Visualização: Word Cloud (vermelho)
```

#### **3.3. Performance da IA**
```python
🤖 Conversas Resolvidas por Bot
- Valor: COUNT(*) WHERE is_bot_resolved
- Taxa: / COUNT(*) * 100
- Trend: Últimos 30 dias

👥 Taxa de Handoff (Bot → Humano)
- Valor: COUNT(*) WHERE has_human_intervention AND has_bot_messages
- Momento: Em que mensagem acontece o handoff?

⏱️ Tempo Médio Bot vs Humano
- Bot: AVG(duration) WHERE is_bot_resolved
- Humano: AVG(duration) WHERE has_human_intervention
- Comparação: Gráfico de barras lado a lado
```

---

### **Gráficos de Qualidade**

#### **1. Gauge - CSAT Score**
```python
Tipo: Gauge (Velocímetro)
Valor: AVG(csat_rating)
Escala: 1 a 5
Zonas:
  - 1-2: Vermelho (Ruim)
  - 2-3: Laranja (Regular)
  - 3-4: Amarelo (Bom)
  - 4-5: Verde (Excelente)
Meta: 4.0+
```

#### **2. Linha - Evolução CSAT**
```python
Tipo: Line Chart
Eixo X: Semana/Mês
Eixo Y: AVG(csat_rating)
Linha adicional: Número de avaliações
Objetivo: Ver tendência de satisfação

SQL:
SELECT
    DATE_TRUNC('week', csat_created_at) as semana,
    AVG(csat_rating) as rating_medio,
    COUNT(*) as total_avaliacoes
FROM vw_conversas_analytics
WHERE has_csat = true
GROUP BY semana
ORDER BY semana
```

#### **3. Word Cloud - Feedbacks**
```python
Tipo: Word Cloud (Nuvem de Palavras)
Fonte: csat_feedback
Tamanho: Frequência da palavra
Cor: Por sentimento (verde=positivo, vermelho=negativo)
Filtros: Por rating, por período
```

---

# 👥 NÍVEL 4: ANÁLISE POR SEGMENTO

## **🎯 Objetivo**: "Qual canal/agente/time está melhor?"

### **4.1. Análise por Canal (Inbox)**

#### **KPIs por Canal**
```python
📱 Volume por Canal
- WhatsApp: COUNT(*) WHERE inbox_channel_type = 'whatsapp'
- Instagram: COUNT(*) WHERE inbox_channel_type = 'instagram'
- Email: COUNT(*) WHERE inbox_channel_type = 'email'
- Web: COUNT(*) WHERE inbox_channel_type = 'web'

⏱️ Performance por Canal
- Tempo médio de resposta: AVG(first_response_time_seconds) GROUP BY inbox_name
- Taxa de resolução: % resolvidas por canal
- CSAT médio: AVG(csat_rating) GROUP BY inbox_name

🤖 Automação por Canal
- Taxa de bot: % is_bot_resolved por canal
- Identificar: Qual canal tem mais bot vs humano?
```

#### **Gráficos por Canal**
```python
1. Barra Agrupada - Comparação de Canais
   Eixo X: Canais
   Eixo Y1: Volume (barras)
   Eixo Y2: CSAT (linha)

2. Tabela Comparativa
   Colunas: Canal | Volume | CSAT | Tempo Resp | Taxa Bot
   Ordenar por: Volume DESC
   Destaque: Melhor e pior em cada métrica
```

---

### **4.2. Análise por Agente**

#### **KPIs por Agente**
```python
👤 Ranking de Agentes
- Critérios:
  1. Volume de conversas
  2. CSAT médio
  3. Tempo médio de resposta
  4. Taxa de resolução

⭐ Top 5 Agentes (Melhores)
- Por CSAT: WHERE csat_rating >= 4
- Por velocidade: Menor first_response_time
- Por volume: Mais conversas resolvidas

⚠️ Bottom 5 Agentes (Precisam melhoria)
- CSAT baixo
- Tempo de resposta alto
- Baixa taxa de resolução

📊 Distribuição de Carga
- Conversas por agente: COUNT(*) GROUP BY assignee_name
- Balanceamento: Desvio padrão da distribuição
- Alerta: Agentes com >2x a média
```

#### **Gráficos por Agente**
```python
1. Scatter Plot - Agentes (Volume vs CSAT)
   Eixo X: Volume de conversas
   Eixo Y: CSAT médio
   Tamanho bolha: Tempo médio de resposta
   Quadrantes:
     - Alto volume + Alto CSAT = ⭐ Star Performers
     - Alto volume + Baixo CSAT = ⚠️ Precisa treinamento
     - Baixo volume + Alto CSAT = 💎 Qualidade
     - Baixo volume + Baixo CSAT = 🚨 Atenção urgente

2. Tabela Detalhada de Agentes
   Colunas:
     - Nome | Foto
     - Conversas Atendidas
     - CSAT Médio
     - Tempo Resp Médio
     - Taxa Resolução
     - Disponibilidade
   Filtros: Por período, por canal
   Ações: Drill-down para conversas específicas
```

---

### **4.3. Análise por Time**

#### **KPIs por Time**
```python
👥 Performance por Time
- Volume: COUNT(*) GROUP BY team_name
- CSAT: AVG(csat_rating) GROUP BY team_name
- Velocidade: AVG(first_response_time_seconds) GROUP BY team_name

📊 Comparação entre Times
- Gráfico radar: Múltiplas métricas por time
- Métricas: Volume, CSAT, Velocidade, Taxa Resolução, Taxa Bot
```

---

# 📅 NÍVEL 5: ANÁLISE TEMPORAL (Tendências)

## **🎯 Objetivo**: "Como evoluímos ao longo do tempo?"

### **5.1. Tendências Gerais**

#### **KPIs de Tendência**
```python
📈 Crescimento Mensal
- Volume: % mudança mês a mês
- Fórmula: (mês_atual - mês_anterior) / mês_anterior * 100
- Visualização: Barra com % em cima

📉 Redução de Tempo de Resposta
- Tendência: Linear regression do first_response_time
- Meta: Reduzir 10% por mês
- Gráfico: Linha com trend line

⭐ Melhoria de CSAT
- Evolução: CSAT mês a mês
- Meta: Aumentar 0.1 ponto por mês
- Gráfico: Linha com target line
```

### **5.2. Sazonalidade e Padrões**

#### **KPIs Sazonais**
```python
📊 Dia da Semana Mais Movimentado
- Valor: Mode(conversation_day_name)
- Volume: COUNT(*) por dia da semana
- Gráfico: Barra por dia

⏰ Horário de Pico
- Pico: Horário com mais conversas
- Horário: conversation_hour
- Gráfico: Linha 24h

🗓️ Tendência Semanal
- Comparação: Esta semana vs semana passada
- Métricas: Volume, CSAT, Tempo resposta
- Formato: Sparklines com %
```

---

### **Gráficos Temporais**

#### **1. Série Temporal Múltipla**
```python
Tipo: Multi-line Chart
Período: Últimos 90 dias
Linhas:
  - Volume total (linha azul)
  - CSAT médio * 100 (linha verde, eixo Y secundário)
  - Taxa de resolução (linha laranja)
Interatividade: Zoom, range selector
```

#### **2. Calendário Heatmap**
```python
Tipo: Calendar Heatmap
Formato: Tipo GitHub contributions
Período: Último ano
Cor: Intensidade = volume de conversas
Hover: Mostrar métricas do dia
```

---

# 🔍 NÍVEL 6: DRILL-DOWN INDIVIDUAL

## **🎯 Objetivo**: "Detalhes de conversas específicas"

### **6.1. Lista de Conversas**

#### **Tabela Interativa**
```python
Colunas:
  1. ID (#123)
  2. Status (badge colorido)
  3. Cliente (nome + foto)
  4. Canal (ícone)
  5. Agente
  6. Msgs (total)
  7. Duração
  8. CSAT (estrelas)
  9. Criada em
  10. Ações (🔍 Ver detalhes)

Filtros:
  - Status
  - Canal
  - Agente
  - Período
  - CSAT rating
  - Tem feedback?

Ordenação:
  - Por data (mais recente)
  - Por duração (mais longa)
  - Por CSAT (pior primeiro para review)

Paginação: 50 por página
```

### **6.2. Detalhes da Conversa**

#### **Modal/Página de Detalhes**
```python
Cabeçalho:
  - ID da conversa
  - Status
  - Cliente: nome, email, telefone
  - Canal
  - Agente atribuído
  - Time
  - Criada em / Atualizada em

Métricas:
  - Total de mensagens
  - Mensagens do agente
  - Mensagens do cliente
  - Duração total
  - Tempo de primeira resposta
  - CSAT rating
  - Feedback

Timeline de Mensagens:
  - Ordenado por created_at
  - Visualização tipo chat
  - Diferenciação: Cliente (esquerda) vs Agente (direita)
  - Timestamps
  - Indicador de bot vs humano

Labels/Tags:
  - Mostrar todas as labels
  - Cores diferentes

Atributos Customizados:
  - Mostrar custom_attributes
  - Formato key: value
```

---

# 📊 RESUMO: MATRIZ DE KPIS POR NÍVEL

| Nível | Qtd KPIs | Principais Métricas | Visualizações |
|-------|----------|---------------------|---------------|
| **1. Executivo** | 15 | Volume, CSAT, Taxa Bot, Tempo Resposta | Cards, Linha, Pizza, Funil |
| **2. Operacional** | 12 | Espera, Produtividade, Mensagens | Heatmap, Box Plot, Barra |
| **3. Qualidade** | 10 | CSAT, NPS, Feedback, Sentiment | Gauge, Word Cloud, Linha |
| **4. Segmento** | 15 | Por Canal, Agente, Time | Scatter, Tabela, Radar |
| **5. Temporal** | 8 | Tendências, Sazonalidade, Crescimento | Série Temporal, Calendar |
| **6. Individual** | N/A | Detalhes de conversas | Tabela, Modal, Timeline |

**TOTAL: 60+ KPIs principais**

---

# 🎨 LAYOUT SUGERIDO DO DASHBOARD

```
┌─────────────────────────────────────────────────────────────┐
│  🏠 AllpFit Analytics - Dashboard                          │
│  📅 Período: [Seletor]  🔄 Atualizado: 5 min atrás         │
├─────────────────────────────────────────────────────────────┤
│  NÍVEL 1: VISÃO EXECUTIVA                                   │
│  ┌────────┬────────┬────────┬────────┐                     │
│  │  📊    │  ⏱️    │  ⭐    │  🤖    │  Cards de KPIs      │
│  │ 4,073  │ 3.2min │  4.3   │ 42.5%  │                     │
│  └────────┴────────┴────────┴────────┘                     │
│  ┌──────────────────────┬──────────────────────┐           │
│  │ 📈 Volume no Tempo   │ 🥧 Dist. por Canal  │           │
│  └──────────────────────┴──────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  [TABS: Operacional | Qualidade | Segmentos | Tendências]  │
├─────────────────────────────────────────────────────────────┤
│  📋 CONVERSAS RECENTES                                      │
│  [Tabela interativa com filtros]                            │
└─────────────────────────────────────────────────────────────┘
```

---

Quer que eu crie agora as **views modulares completas** para suportar todos esses KPIs? 🚀
