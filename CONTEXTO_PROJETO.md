# 📊 AllpFit Analytics - Contexto do Projeto

**Data última atualização:** 22/10/2025
**Desenvolvido com:** Claude Code
**Branch principal:** `feature/dashboard-analytics-ai`

---

## 🎯 OBJETIVO DO PROJETO

Dashboard analytics para acompanhar performance do bot de WhatsApp da academia AllpFit, com análise de IA para qualificação de leads e integração com CRM.

---

## 📁 ESTRUTURA DO PROJETO

```
allpfit-analytics/
├── src/
│   ├── app/                          # Dashboard Streamlit
│   │   ├── dashboard.py              # Dashboard principal
│   │   ├── config.py                 # Configurações e temas
│   │   └── utils/
│   │       ├── db_connector.py       # Conexão PostgreSQL
│   │       └── metrics.py            # Cálculo de KPIs
│   │
│   ├── features/                     # Features de análise
│   │   ├── rule_based_analyzer.py    # Análise baseada em regras
│   │   ├── rule_based_initial_load.py # Carga inicial de análises
│   │   └── ai_analyzer.py            # (Futuro) Análise com OpenAI
│   │
│   └── integrations/                 # Integrações externas
│       ├── __init__.py
│       └── evo_crm.py                # Cliente API EVO CRM
│
├── scripts/                          # Scripts utilitários
│   └── restart_dashboard.sh          # Restart do dashboard
│
├── match_leads_crm.py                # Script sincronização CRM (via API)
├── crossmatch_excel_crm.py           # Script crossmatch Excel → Bot
└── CONTEXTO_PROJETO.md               # Este arquivo
```

---

## 🗄️ BANCO DE DADOS

### PostgreSQL AllpFit

**Conexão:**
- Host: localhost
- Port: 5432
- Database: allpfit
- User: isaac
- Password: AllpFit2024@Analytics

### Principais Tabelas/Views:

#### 1. `conversas_analytics` (View principal)
```sql
-- Dados agregados de conversas do bot
- conversation_id
- contact_name
- contact_phone
- conversation_date
- last_activity_at
- t_messages (total mensagens)
- contact_messages_count (mensagens do lead)
- bot_messages_count
- has_human_intervention
- message_compiled (JSONB com todas as mensagens)
- status_label_pt
- conversation_period (Manhã/Tarde/Noite/Madrugada)
```

#### 2. `conversas_analytics_ai` (Análises de IA)
```sql
-- Análises geradas pelo rule-based analyzer
- conversation_id (FK para conversas_analytics)
- analise_ia (TEXT) - Análise detalhada em 3 tópicos
- probabilidade_conversao (1-5) - Score de qualificação
- sugestao_disparo (TEXT) - Sugestão de abordagem
```

**Total de conversas analisadas:** 482

**Distribuição por probabilidade:**
- 5/5 (Alta): 184 leads (38%)
- 4/5 (Boa): 77 leads (16%)
- 3/5 (Média): 17 leads (3.5%)
- 2/5 (Baixa): 68 leads (14%)
- 1/5 (Muito baixa): 136 leads (28%)

#### 3. `conversas_crm_match` (Conversões CRM via API)
```sql
-- Cruzamento entre leads do bot e membros do CRM (via API EVO)
- id (SERIAL)
- conversation_id (FK)
- bot_name, bot_phone
- conv_date
- evo_id_member (ID no EVO CRM)
- evo_name, evo_email
- evo_conversion_date
- created_at
```

#### 4. `conversas_crm_match_real` (Conversões Reais via Excel)
```sql
-- Cruzamento entre leads do bot e base Excel do CRM
-- Identifica leads que falaram com bot ANTES de entrar no CRM
- id (SERIAL)
- conversation_id (FK)
- nome_bot (nome no bot)
- nome_crm (nome no CRM)
- telefone (formato completo)
- telefone_8dig (normalizado para match)
- conversa_criada_em (primeira interação)
- cadastro_crm_em (data de entrada no CRM)
- dias_para_conversao (tempo entre bot e CRM)
- total_mensagens (engajamento)
- conversou_antes_crm (boolean)
- id_cliente_crm (ID no EVO)
- email_crm
- created_at
```

**Conversões reais identificadas:** 3 (1.5% de 198 clientes do CRM)

---

## 🤖 ANÁLISE DE IA (Rule-Based)

### Sistema de Pontuação

O `rule_based_analyzer.py` implementa um sistema de scoring 0-10+ baseado em:

**Pontos Positivos:**
- Agendamento mencionado: +3
- Perguntou valor + ≥5 mensagens: +2
- Perguntou valor: +1
- Perguntou horário: +1
- Perguntou planos: +1
- Palavras positivas (quero, gostaria): +1
- Urgência (hoje, agora): +2
- Engajamento alto (≥4): +2
- Engajamento médio (≥3): +1

**Pontos Negativos:**
- Palavras negativas (caro, longe): -2
- Apenas 1 mensagem: -1

### Estrutura da Análise

Cada conversa recebe análise em **3 tópicos**:

1. **Sinais de Interesse**
   - Detecção de agendamento, valor, horário, planos
   - Análise de engajamento (mensagens trocadas)
   - Identificação de urgência e palavras-chave positivas

2. **Balanço da Conversa**
   - Qualidade do engajamento
   - Detecção de dúvidas vs. objeções
   - Avaliação da intenção de compra

3. **Recomendação (com Score)**
   - Score 6+: 🎯 LEAD QUENTE - Prioridade MÁXIMA
   - Score 4-5: ⭐ LEAD BOM - Prioridade ALTA
   - Score 2-3: 💡 LEAD MORNO - Prioridade MÉDIA
   - Score 0-1: 📊 LEAD FRIO - Prioridade BAIXA

**Propósito:** Esta análise serve como BASE/CONTEXTO para futura integração com OpenAI refinar as análises.

---

## 📊 DASHBOARD STREAMLIT

### Acesso
```bash
# URL: https://analytcs.geniai.online
cd /home/isaac/projects/allpfit-analytics
streamlit run src/app/dashboard.py --server.port 8503
```

### Cabeçalho

- **Título:** ANALYTICS GENIAI - OVERVIEW
- **Contador:** Bot rodando há X dias (desde 25/09/2025)
  - Calculado dinamicamente desde primeira conversa

### KPIs Principais (Seção 1)

1. **Total Contatos:** Leads que engajaram (≥1 mensagem)
2. **Total Conversas Agente AI:** 100% bot (sem humano)
3. **Humano:** Conversas com intervenção humana
4. **Visitas Agendadas:** 42 (confirmadas pelo bot)
5. **Vendas/Tráfego:** 3 conversões reais (leads que viraram clientes - 1.5%)
6. **Vendas/Geral:** 198 (total de clientes no CRM)

### Métricas Diárias (Seção 2)

- Novos Leads
- Visitas Dia
- Vendas Dia
- Total Conversas Dia (novas + reabertas)
- Novas Conversas
- Conversas Reabertas

### Gráficos (Seção 3)

- Média Leads por Dia (últimos 30 dias)
- Distribuição por Período do Dia

### Conversões Reais (Seção 4)

**🎯 Conversões Reais: Leads do Bot que viraram Clientes**

Exibido quando `vendas_trafego > 0`:
- 3 cartões métricos: Conversões | Taxa | Total CRM
- Tabela com detalhes:
  - Nome (Bot)
  - Nome (CRM)
  - Telefone
  - Data Conversa
  - Data CRM
  - Dias para Converter
  - Total Mensagens
- Insight: "💡 Estes leads conversaram com o bot ANTES de se cadastrarem no CRM. Tempo médio: 3-10 dias."

### Tabela de Leads (Seção 5)

**Leads não convertidos com análise de IA**
- Top 50 leads priorizados por probabilidade
- Visualização formatada da conversa (estilo chat)
- Análise completa em 3 tópicos
- Sugestão de disparo personalizada

### Filtros

- Data Início
- Data Fim
- Botão limpar filtros

---

## 🔌 INTEGRAÇÃO EVO CRM

### API EVO

**Documentação:** https://evo-abc.readme.io/reference

**Autenticação:** Basic Auth
- DNS: allpfit
- Token: AF61C223-2C8D-4619-94E3-0A5A37D1CD8D

**Base URL:** https://evo-integracao-api.w12app.com.br

**Rate Limits:**
- 40 requisições/minuto (por IP)
- 10.000 requisições/hora (por API key)
- 20.000 requisições/hora (por DNS)

### Endpoints Utilizados

```python
# Buscar membros ativos
GET /api/v2/members
    ?status=1                    # Apenas ativos
    &showMemberships=true        # Incluir dados de membership
    &take=50                     # Paginação
    &skip=0

# Buscar membro por ID
GET /api/v2/members/{idMember}

# Buscar vendas (futuro)
GET /api/v2/sales
    ?idMember=123
    &dateSaleStart=2025-09-15
    &dateSaleEnd=2025-10-21
```

### Script de Sincronização

**Arquivo:** `match_leads_crm.py`

**Funcionamento:**
1. Busca TODOS os membros ativos do EVO (2.685 membros)
2. Extrai telefones de cada membro
3. Busca leads do bot no PostgreSQL (481 leads)
4. Cruza telefones (match pelos últimos 11 dígitos)
5. Salva conversões na tabela `conversas_crm_match`

**Resultado Atual:**
- 2 conversões identificadas (0.4%)
- ⚠️ Ambas são de membro que já estava cadastrado ANTES da conversa
- Taxa real de conversão pós-bot: 0%

**Possíveis causas da baixa taxa:**
- Leads ainda não se matricularam
- Telefones diferentes entre WhatsApp e CRM
- Bot conversando com curiosos que não convertem

### Script de Crossmatch Excel

**Arquivo:** `crossmatch_excel_crm.py`

**Funcionamento:**
1. Carrega base Excel do CRM (`base_evo.xlsx` com 198 clientes)
2. Normaliza telefones para 8 dígitos (remove DDI 55, DDD 83, e 9 adicional)
   - Exemplo: "55 83988439500" → "88439500"
   - Exemplo: "55 (83) 99886-9874" → "98869874"
3. Busca conversas do bot no PostgreSQL (480 conversas)
4. Normaliza telefones do bot para 8 dígitos
5. Cruza por telefone de 8 dígitos
6. Valida se conversa foi ANTES do cadastro no CRM
7. Salva conversões reais na tabela `conversas_crm_match_real`

**Resultado Atual:**
- **3 conversões reais identificadas** (1.5% de 198 clientes)
- Todas conversaram com bot ANTES de entrar no CRM
- Tempo médio de conversão: 3-10 dias

**Conversões Encontradas:**
1. **JOSÉ VINICIUS DE SOUZA FILHO** (Vih) - 93255303
   - Conversa: 14/10/2025 → CRM: 20/10/2025 (6 dias)
   - 23 mensagens trocadas

2. **Rossana medeiro matias** (RossanaMedeiros) - 87776252
   - Conversa: 25/09/2025 → CRM: 13/10/2025 (18 dias)
   - 11 mensagens trocadas

3. **MORONI RODRIGUES DINIZ** (Moroni Diniz) - 91257974
   - Conversa: 01/10/2025 → CRM: 10/10/2025 (9 dias)
   - 14 mensagens trocadas

---

## 🎯 ANÁLISE DE VISITAS AGENDADAS

### Metodologia

Busca por confirmações do bot nas mensagens:
- "visita agendada"
- "agendamento confirmado"
- "já agendei"
- "te espero"

### Resultados Detalhados

**Total de visitas:** 42 (confirmadas pelo bot)

**Distribuição:**
- Lead pediu + Bot confirmou: 20 visitas (100% confiança)
- Bot confirmou sem pedido explícito: 22 visitas (95% confiança)
- Lead pediu mas sem confirmação: 29 conversas (precisam follow-up)

**Comparação com Google Calendar:**
- Sistema detectou: 42 visitas
- Controle manual (Isaac): 54 visitas
- Diferença: 12 visitas (possivelmente agendadas por humano/telefone)

---

## 🚀 TECNOLOGIAS UTILIZADAS

### Backend
- **Python 3.11**
- **PostgreSQL** (banco de dados)
- **psycopg2** (conexão PostgreSQL)
- **SQLAlchemy** (ORM e queries)

### Dashboard
- **Streamlit** (framework web)
- **Plotly** (gráficos interativos)
- **Pandas** (manipulação de dados)

### Integrações
- **requests** (HTTP client)
- **EVO CRM API** (sistema CRM da academia)

### Deploy
- **Nginx** (reverse proxy)
- **Systemd** (serviço Linux)
- **Domain:** analytcs.geniai.online

---

## 📝 HISTÓRICO DE DESENVOLVIMENTO

### Fase 1: Setup Inicial
- ✅ Configuração do banco PostgreSQL
- ✅ Criação de views analíticas
- ✅ Setup Streamlit dashboard
- ✅ Deploy em analytcs.geniai.online

### Fase 2: Dashboard Base
- ✅ KPIs principais (contatos, conversas AI/humano)
- ✅ Métricas diárias com comparação D-1
- ✅ Gráficos de tendência
- ✅ Filtros por data
- ✅ Formatação em português

### Fase 3: Análise de IA
- ✅ Sistema de pontuação (rule-based)
- ✅ Análise em 3 tópicos aprofundados
- ✅ Classificação por probabilidade (1-5)
- ✅ Sugestões de disparo personalizadas
- ✅ Processamento de 482 conversas
- ✅ Criação da view `vw_leads_nao_convertidos_com_ia`

### Fase 4: Contagem de Visitas
- ✅ Detecção de agendamentos pelo bot
- ✅ Query SQL otimizada com JSONB
- ✅ Análise detalhada (42 visitas confirmadas)
- ✅ Comparação com controle manual (54 no Google Calendar)
- ⚠️ Tentativa de integração Google Calendar (cancelada por complexidade OAuth)

### Fase 5: Integração CRM
- ✅ Cliente API EVO CRM com rate limiting
- ✅ Busca de 2.685 membros ativos
- ✅ Extração de telefones e normalização
- ✅ Cruzamento com 481 leads do bot
- ✅ Criação tabela `conversas_crm_match`
- ✅ Script `match_leads_crm.py` para sincronização
- ⚠️ Taxa de conversão baixa (0.4%) - investigar

---

## 🔧 CONFIGURAÇÕES E CREDENCIAIS

### PostgreSQL
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=allpfit
DB_USER=isaac
DB_PASSWORD=AllpFit2024@Analytics
```

### EVO CRM API
```bash
EVO_DNS=allpfit
EVO_API_TOKEN=AF61C223-2C8D-4619-94E3-0A5A37D1CD8D
```

### Streamlit
```bash
PORT=8503
URL=https://analytcs.geniai.online
```

---

## 📈 PRÓXIMOS PASSOS

### Curto Prazo
- [ ] Atualizar dashboard com KPI "Vendas/Tráfego" (2 conversões)
- [ ] Investigar baixa taxa de conversão (0.4%)
- [ ] Automatizar sincronização CRM (cron diário)
- [ ] Adicionar filtro por probabilidade no dashboard

### Médio Prazo
- [ ] Integração OpenAI para análise mais sofisticada
- [ ] Usar análise rule-based como contexto para GPT
- [ ] Sistema de notificação para leads quentes
- [ ] Exportação de relatórios em PDF

### Longo Prazo
- [ ] Integração com Google Calendar (visitas)
- [ ] Webhook do Evolution API para análise em tempo real
- [ ] Dashboard de performance do bot (taxa de resposta, tempo médio)
- [ ] A/B testing de mensagens do bot

---

## 🐛 PROBLEMAS CONHECIDOS

1. **Taxa de Conversão Baixa (0.4%)**
   - Apenas 2 de 481 leads viraram membros
   - Ambos já eram membros antes da conversa
   - Possível problema: telefones diferentes entre WhatsApp e CRM

2. **Visitas Agendadas vs Google Calendar**
   - Sistema: 42 visitas
   - Manual: 54 visitas
   - Diferença de 12 (possivelmente agendamentos manuais)

3. **Tentativa de Google Calendar API**
   - Complexidade OAuth em servidor sem GUI
   - Requer autenticação manual no browser
   - Cancelado por hora, pode retomar depois

---

## 📚 APRENDIZADOS

### O que funcionou bem:
✅ Rule-based analyzer com 3 tópicos aprofundados
✅ Sistema de pontuação simples e efetivo
✅ Dashboard intuitivo em português
✅ Integração EVO CRM com rate limiting
✅ Normalização de telefones (últimos 11 dígitos)

### O que pode melhorar:
⚠️ Taxa de conversão muito baixa - investigar causas
⚠️ Formato de telefone inconsistente (bot vs CRM)
⚠️ Falta integração em tempo real (webhook)
⚠️ Dependência de sincronização manual

---

## 🤝 COLABORADORES

- **Isaac** (Cliente/Product Owner)
- **Claude Code** (Desenvolvimento/IA)

---

## 📞 CONTATOS

- **Academia:** AllpFit - João Pessoa, PB
- **Dashboard:** https://analytcs.geniai.online
- **Repositório:** github.com/geniai-br/allpfit-analytics
- **Branch ativa:** feature/dashboard-analytics-ai

---

**Última sincronização CRM:** 21/10/2025 23:15
**Próxima sincronização sugerida:** Diária (madrugada)

---

_Documento gerado automaticamente por Claude Code_
_Para dúvidas ou atualizações, consulte este arquivo antes de começar novas features_
