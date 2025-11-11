# 🤖 PROMPT PARA NOVO CHAT - MODIFICAÇÕES PÓS-APRESENTAÇÃO

> **Use este prompt para continuar a implementação das modificações solicitadas pelos superiores**
> **Última atualização:** 2025-11-11
> **Status:** 📋 FASE DE IMPLEMENTAÇÃO | Análises completas, pronto para codar

---

## 📊 CONTEXTO DO PROJETO

**Nome:** GeniAI Analytics (multi-tenant SaaS)
**Clientes:** AllpFit (academia), CDT Mossoró, CDT JP Sul e outros
**Objetivo:** Analytics de conversas do Chatwoot com análise IA contextual por cliente

### 🏗️ Arquitetura Atual:

```
BANCO REMOTO (Chatwoot)          BANCO LOCAL (geniai_analytics)          DASHBOARDS
178.156.206.184                   localhost                               localhost:8504
─────────────────                ─────────────────────────               ──────────────
vw_conversations_final    ETL    conversations_analytics    RLS          Client + Admin
(118 colunas)            ───>    (133 colunas) ────────────────>        (Streamlit)
2.077+ conversas                 + análise OpenAI (AllpFit)
```

### 📈 Status Atual (2025-11-11):

**Sistema:**
- ✅ Multi-tenant funcionando (12 tenants cadastrados)
- ✅ ETL automatizado (Systemd timer a cada 2h)
- ✅ Row-Level Security (RLS) implementado
- ✅ OpenAI integrado (GPT-4o-mini) para AllpFit
- ✅ Dashboards Client + Admin funcionais

**Dados AllpFit (Tenant 1):**
- 1.317 conversas totais
- 742 conversas analisadas com OpenAI (56%)
- 556 conversas com nome mapeado (42%)
- R$ 29.55 gastos em análise OpenAI
- 100% das conversas com inbox_name e datas

---

## 🎯 SITUAÇÃO ATUAL - POR QUE ESTAMOS AQUI

### O Problema Identificado:

Após apresentação do sistema para superiores, identificaram que:

1. **Análise OpenAI é específica demais** - Campos como `condicao_fisica`, `objetivo`, `analise_ia` foram criados especificamente para AllpFit (academia), não servem para CDT (educação), InvestBem (finanças), etc.

2. **Dashboard pouco focado em inboxes** - Clientes têm múltiplas inboxes (Suporte, Recepção, WhatsApp, Instagram) mas não conseguem ver métricas separadas por canal.

3. **Faltam filtros rápidos** - Tabela de conversas tem poucos filtros, dificulta análise exploratória.

4. **Métricas irrelevantes** - Funil de conversão e métricas de qualidade não agregam valor real.

### A Solução Proposta:

1. **Genericizar o dashboard** - Remover campos específicos AllpFit, manter apenas colunas universais
2. **Fortalecer análise por inbox** - Métricas agregadas E separadas por canal
3. **Implementar filtros completos** - Toda coluna filtrável, estilo dashboard single-tenant
4. **Arquivar código obsoleto** - Mover métricas irrelevantes para `_archived/` (não deletar)
5. **Sistema de análise futuro** - Johan + Superior vão criar sistema onde CADA cliente escolhe análise customizada no próprio dashboard

---

## 📝 MUDANÇAS SOLICITADAS (Detalhamento)

### 1. SIMPLIFICAR COLUNAS DA TABELA

#### ❌ **REMOVER do Dashboard (ocultar, não deletar do banco):**
- `condicao_fisica` - Específico academia
- `objetivo` - Específico academia
- `analise_ia` - Específica AllpFit
- `sugestao_disparo` - Será re-implementada com templates genéricos
- `probabilidade_conversao` - Score específico AllpFit

**Motivo:** Não aplicáveis a outros contextos (educação, finanças, etc)

#### ✅ **ADICIONAR/MANTER Colunas GENÉRICAS:**

**Já existem no banco (só precisa exibir):**
- ✅ `inbox_name` - Nome da inbox (1.317/1.317 = 100%)
- ✅ `inbox_id` - ID da inbox
- ✅ `mc_first_message_at` - Primeiro contato (99.9%)
- ✅ `mc_last_message_at` - Último contato (99.9%)
- ✅ `message_compiled` - JSONB com conversa completa (99.9%)
- ✅ `nome_mapeado_bot` - Nome extraído pela IA (556 registros)

**Colunas já visíveis (manter):**
- ✅ `conversation_id`, `contact_name`, `contact_phone`
- ✅ `status`, `is_lead`, `t_messages`
- ✅ `conversation_created_at`

### 2. MELHORAR ANÁLISE POR INBOX

**Adicionar seção dedicada no dashboard:**

```
┌─────────────────────────────────────────────────────────┐
│ 📊 VISÃO GERAL (Todas as Inboxes)                      │
│   Total: 1.317 conversas | 387 leads (29.4%)           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 📥 ANÁLISE POR INBOX                                    │
├─────────────────────────────────────────────────────────┤
│ Inbox: allpfitjpsulcloud1                               │
│   📊 710 conversas | 275 leads (38.7%) | Avg: 12 msgs  │
│                                                          │
│ Inbox: allpfitrecepcao                                  │
│   📊 456 conversas | 89 leads (19.5%) | Avg: 8 msgs    │
│                                                          │
│ Inbox: allpfitwhatsapp                                  │
│   📊 151 conversas | 23 leads (15.2%) | Avg: 6 msgs    │
└─────────────────────────────────────────────────────────┘
```

**Métricas por inbox:**
- Total de conversas
- Taxa de leads (% is_lead)
- Média de mensagens
- Tipo de atendimento (Bot vs Humano)

### 3. IMPLEMENTAR FILTROS RÁPIDOS

**Referência:** Dashboard single-tenant (porta 8503) - linha 465-524

**Layout:** Linha horizontal com 6 colunas acima da tabela

```python
st.markdown("#### 🔍 Filtros Rápidos")

col1, col2, col3, col4, col5, col6 = st.columns(6)

# Col 1: Nome
filter_nome = st.text_input("🔍 Nome", placeholder="Digite...")

# Col 2: Inbox
filter_inbox = st.multiselect("📥 Inbox", options=df['inbox_name'].unique())

# Col 3: Status
filter_status = st.multiselect("📊 Status", options=['open', 'resolved', 'pending'])

# Col 4: É Lead?
filter_lead = st.radio("🎯 Lead?", ["Todos", "Sim", "Não"])

# Col 5: Período
filter_periodo = st.selectbox("📅 Período",
    ["Todos", "Hoje", "Últimos 7 dias", "Últimos 30 dias", "Personalizado"])

# Col 6: Total Mensagens
filter_msgs = st.slider("💬 Mensagens", 0, 100, (0, 100))
```

**Filtros devem:**
- Usar `st.session_state` para persistir valores
- Resetar paginação ao aplicar filtro
- Combinar múltiplos filtros (AND logic)
- Ter botão "Limpar Filtros"

### 4. ARQUIVAR MÉTRICAS OBSOLETAS

**Criar estrutura:**
```
src/multi_tenant/dashboards/
├── _archived/                    # NOVA pasta
│   ├── README.md                 # Explicação
│   ├── funil_conversao.py       # Código do funil
│   └── metricas_qualidade.py    # Código de qualidade
├── client_dashboard.py           # Dashboard ativo (simplificado)
├── admin_dashboard.py
└── app.py
```

**Métricas a arquivar:**
- Gráfico de funil de conversão
- Taxa de engajamento
- Tempo médio de resposta
- Score de qualidade de atendimento

**IMPORTANTE:** NÃO deletar código, apenas mover para `_archived/`

---

## 🗄️ ANÁLISE DO BANCO DE DADOS (Já Feita)

### Descoberta Importante: QUASE TUDO JÁ EXISTE!

**Documento:** [docs/multi-tenant/ANALISE_COLUNAS_BANCO.md](ANALISE_COLUNAS_BANCO.md)

#### Colunas que JÁ EXISTEM (não precisa adicionar):
- ✅ `inbox_name`, `inbox_id` (100% dos registros)
- ✅ `mc_first_message_at` (primeiro contato) - 99.9%
- ✅ `mc_last_message_at` (último contato) - 99.9%
- ✅ `message_compiled` (JSONB com conversa completa) - 99.9%
- ✅ `nome_mapeado_bot` (556 conversas = 42%)

#### Estrutura do `message_compiled` (JSONB):
```json
[
  {
    "text": "Ola",
    "sender": "Contact",
    "sent_at": "2025-09-25T01:52:07.951889",
    "message_type": 0
  },
  {
    "text": "Como funciona?",
    "sender": "Contact",
    "sent_at": "2025-09-25T01:57:59.179351",
    "message_type": 0
  },
  {
    "text": "Oi! Aqui é a Gabi...",
    "sender": "AgentBot",
    "sent_at": "2025-09-25T01:58:23.159729",
    "message_type": 1
  }
]
```

#### Tipo de Atendimento (inferir com colunas existentes):
```python
def get_atendimento_tipo(row):
    if row['is_bot_resolved'] and not row['has_human_intervention']:
        return 'Bot'
    elif row['has_human_intervention']:
        return 'Humano' if row['assignee_id'] else 'Misto'
    else:
        return 'Bot'
```

---

## 📂 DOCUMENTAÇÃO CRIADA (Análise Completa)

### Documentos Disponíveis:

1. **[MODIFICACOES_POS_APRESENTACAO.md](MODIFICACOES_POS_APRESENTACAO.md)** (425 linhas)
   - Planejamento completo das mudanças
   - Anotações da reunião com superiores
   - Interpretação detalhada de cada requisito
   - Checklist de validação

2. **[ANALISE_COLUNAS_BANCO.md](ANALISE_COLUNAS_BANCO.md)** (200+ linhas)
   - Análise técnica do banco de dados
   - Colunas existentes vs necessárias
   - Estrutura do JSONB `message_compiled`
   - Recomendações de implementação

3. **[ESTADO_ATUAL_PROJETO.md](ESTADO_ATUAL_PROJETO.md)** (1.027 linhas)
   - Estado completo do projeto antes das mudanças
   - Métricas de produção (AllpFit)
   - ROI comprovado (2.400% - 10.600%)
   - Pronto para apresentação

---

## 🔧 CREDENCIAIS E ACESSO

### Banco Local (geniai_analytics):
```bash
Host: localhost
Database: geniai_analytics
User: johan_geniai (owner, bypassa RLS)
Password: vlVMVM6UNz2yYSBlzodPjQvZh
```

### Dashboards:
```bash
Multi-Tenant (Client + Admin): http://localhost:8504
Single-Tenant (referência filtros): http://localhost:8503
```

### Arquivos Principais:
```bash
# Dashboard multi-tenant (modificar)
src/multi_tenant/dashboards/client_dashboard.py

# Dashboard single-tenant (referência de filtros)
src/app/dashboard.py (linha 465-524)

# Configuração
.env (credenciais)
src/shared/config.py
```

---

## 🚀 PLANO DE IMPLEMENTAÇÃO (Passo a Passo)

### ✅ FASE 1: PREPARAÇÃO (Concluída)
- [x] Analisar banco de dados
- [x] Analisar dashboard single-tenant
- [x] Documentar mudanças necessárias
- [x] Validar entendimento com Johan

### 🎯 FASE 2: IMPLEMENTAÇÃO (Próxima)

#### Passo 1: Criar Estrutura de Arquivamento (15min)
```bash
# Criar pasta _archived/
mkdir -p src/multi_tenant/dashboards/_archived

# Criar README explicativo
touch src/multi_tenant/dashboards/_archived/README.md
```

#### Passo 2: Identificar Código a Arquivar (30min)
- Ler `client_dashboard.py` completo
- Identificar seções de:
  - Funil de conversão
  - Métricas de qualidade
  - Gráficos específicos AllpFit
- Documentar linhas a mover

#### Passo 3: Modificar Tabela de Conversas (2h)
- **Remover colunas específicas AllpFit:**
  - Comentar código que exibe `condicao_fisica`, `objetivo`, etc
  - Adicionar comentário: `# REMOVIDO: Específico AllpFit - aguardando sistema genérico`

- **Adicionar colunas genéricas:**
  - `inbox_name` (já existe no DB)
  - `mc_first_message_at` como "Primeiro Contato"
  - `mc_last_message_at` como "Último Contato"
  - `nome_mapeado_bot` como "Nome (IA)"
  - Primeiras 3-5 mensagens de `message_compiled` como "Conversa"

#### Passo 4: Implementar Filtros Rápidos (2h)
- Criar seção "🔍 Filtros Rápidos" acima da tabela
- Layout 6 colunas horizontais (st.columns(6))
- Filtros:
  1. Nome (text_input)
  2. Inbox (multiselect)
  3. Status (multiselect)
  4. É Lead (radio)
  5. Período (selectbox + date_input condicional)
  6. Total Mensagens (slider ou number_input range)
- Usar `st.session_state` para persistência
- Reset de paginação ao filtrar
- Botão "Limpar Filtros"

#### Passo 5: Adicionar Seção Análise por Inbox (2h)
- Criar seção "📥 Análise por Inbox"
- Agrupar conversas por `inbox_name`
- Calcular para cada inbox:
  - Total conversas
  - Total leads (% is_lead)
  - Média de mensagens
  - Tipo de atendimento (inferir com `has_human_intervention`)
- Visualizar em cards ou tabela expandable
- Adicionar gráfico de barras (opcional)

#### Passo 6: Mover Código Obsoleto (1h)
- Criar arquivos em `_archived/`:
  - `funil_conversao.py` (código do funil)
  - `metricas_qualidade.py` (código de métricas)
- Adicionar imports comentados em `client_dashboard.py`
- Criar `_archived/README.md` explicativo

#### Passo 7: Testar com Dados Reais (1h)
- Logar como `isaac@allpfit.com.br`
- Testar todos os filtros
- Validar métricas por inbox
- Verificar performance (tempo de carregamento)
- Testar em diferentes tenants

#### Passo 8: Documentar Mudanças (30min)
- Atualizar `ESTADO_ATUAL_PROJETO.md`
- Criar `CHANGELOG.md` com mudanças
- Atualizar `00_CRONOGRAMA_MASTER.md`

#### Passo 9: Commit (15min)
```bash
git add .
git commit -m "refactor(dashboard): genericizar para multi-contexto

Mudanças pós-apresentação para superiores:

REMOVIDO (oculto, não deletado):
- Campos específicos AllpFit: condicao_fisica, objetivo,
  analise_ia, sugestao_disparo, probabilidade_conversao
- Métricas irrelevantes: funil conversão, métricas qualidade

ADICIONADO:
- Colunas genéricas: inbox_name, primeiro/último contato,
  nome_mapeado_bot, amostra conversa
- Seção 'Análise por Inbox' (métricas por canal)
- Filtros rápidos (6 colunas: nome, inbox, status, lead, período, msgs)
- Pasta _archived/ com código preservado

MELHORADO:
- Foco em inboxes (múltiplos canais)
- Filtros completos (toda coluna filtrável)
- Dashboard genérico (serve qualquer contexto)

Arquivos modificados:
- src/multi_tenant/dashboards/client_dashboard.py (refactor completo)
- src/multi_tenant/dashboards/_archived/ (código preservado)

Sistema agora serve academia, educação, finanças, etc.
Análise customizada será implementada futuramente (Johan + Superior).

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 📊 ESTIMATIVAS

### Tempo Total: **8-10 horas** (~1-2 dias)
- Preparação: 45min ✅ (concluído)
- Implementação: 8h (próximo)
- Testes: 1h
- Documentação: 30min
- Commit: 15min

### Complexidade:
- **Baixa:** Criar `_archived/`, documentar
- **Média:** Modificar tabela, adicionar colunas
- **Alta:** Implementar filtros completos, análise por inbox

### Riscos:
- ⚠️ Performance com muitos filtros ativos
- ⚠️ Quebrar funcionalidades existentes
- ⚠️ Remover campos que ainda são usados

**Mitigação:** Testar cada mudança, preservar código antigo, commits granulares

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

Antes de começar a codar, confirmar:
- [x] Análise do banco completa ([ANALISE_COLUNAS_BANCO.md](ANALISE_COLUNAS_BANCO.md))
- [x] Dashboard single-tenant analisado (referência filtros)
- [x] Planejamento validado com Johan
- [x] Documentos criados e atualizados
- [ ] Backup do `client_dashboard.py` atual
- [ ] Branch criado (`git checkout -b feature/dashboard-generico`)

---

## 🎯 OBJETIVOS FINAIS

### O que teremos depois:

1. **Dashboard Genérico** - Serve academias, CDTs, finanças, qualquer negócio
2. **Foco em Inboxes** - Métricas consolidadas E separadas por canal
3. **Filtros Completos** - Toda coluna filtrável, análise exploratória fácil
4. **Código Preservado** - Nada deletado, tudo em `_archived/`
5. **Base para Futuro** - Sistema de análise customizável (Johan + Superior)

### O que NÃO faremos agora:

- ❌ Sistema de análise customizável (futuro com Johan + Superior)
- ❌ Templates de disparo genéricos (futuro)
- ❌ Alterações no banco de dados (já tem tudo)
- ❌ Modificações no ETL (só dashboard)

---

## 🚨 PONTOS DE ATENÇÃO

### Durante Implementação:

1. **NÃO deletar código** - Sempre mover para `_archived/`
2. **NÃO modificar banco** - Usar colunas existentes
3. **Testar constantemente** - Cada mudança, testar imediatamente
4. **Commits granulares** - Não fazer tudo de uma vez
5. **Preservar RLS** - Não quebrar isolamento de tenants

### Padrões de Código:

```python
# BOM: Comentar código removido
# REMOVIDO 2025-11-11: Campo específico AllpFit
# Aguardando sistema genérico de análise customizável
# if 'condicao_fisica' in df.columns:
#     st.dataframe(df[['nome', 'condicao_fisica']])

# BOM: Usar colunas existentes
primeiro_contato = df['mc_first_message_at']
inbox = df['inbox_name']

# BOM: Mapear nomes amigáveis
df_display = df.rename(columns={
    'mc_first_message_at': 'Primeiro Contato',
    'mc_last_message_at': 'Último Contato',
    'nome_mapeado_bot': 'Nome (IA)'
})
```

---

## 📚 DOCUMENTAÇÃO RELACIONADA

**Leitura obrigatória antes de começar:**
1. 📋 [MODIFICACOES_POS_APRESENTACAO.md](MODIFICACOES_POS_APRESENTACAO.md) - Planejamento completo
2. 🗄️ [ANALISE_COLUNAS_BANCO.md](ANALISE_COLUNAS_BANCO.md) - Análise técnica do banco

**Referência durante implementação:**
3. 📊 [ESTADO_ATUAL_PROJETO.md](ESTADO_ATUAL_PROJETO.md) - Estado antes das mudanças
4. 🚀 `src/app/dashboard.py` (linha 465-524) - Referência de filtros rápidos
5. 🗄️ [DB_DOCUMENTATION.md](DB_DOCUMENTATION.md) - Estrutura do banco

---

## 🔗 COMANDOS RÁPIDOS

```bash
# Conectar banco
PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -h localhost -d geniai_analytics

# Ver colunas da tabela
\d conversations_analytics

# Testar dashboard
streamlit run src/multi_tenant/dashboards/app.py --server.port=8504

# Criar branch
git checkout -b feature/dashboard-generico

# Backup arquivo
cp src/multi_tenant/dashboards/client_dashboard.py src/multi_tenant/dashboards/client_dashboard.py.backup

# Ver diferenças
git diff src/multi_tenant/dashboards/client_dashboard.py
```

---

**Última atualização:** 2025-11-11 08:15
**Criado por:** Johan + Claude Code
**Status:** 📋 PRONTO PARA IMPLEMENTAÇÃO

**Próxima Tarefa:**
1. Criar branch `feature/dashboard-generico`
2. Fazer backup de `client_dashboard.py`
3. Criar estrutura `_archived/`
4. Começar implementação passo a passo

**Objetivo Final:** Dashboard genérico que serve QUALQUER contexto de negócio, com foco em análise por inbox e filtros completos! 🚀