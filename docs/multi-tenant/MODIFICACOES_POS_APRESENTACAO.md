# MODIFICAÇÕES PÓS-APRESENTAÇÃO SUPERIORES

> **Data:** 2025-11-11
> **Contexto:** Feedback da reunião com superiores após apresentação do sistema
> **Status:** 📋 Em Planejamento

---

## 📋 CONTEXTO

Após apresentação do sistema multi-tenant com integração OpenAI para superiores, foram solicitadas modificações para tornar o sistema mais genérico e aplicável a diferentes contextos de negócio (não apenas academias como AllpFit).

### Problema Identificado
A análise OpenAI atual foi desenvolvida especificamente para o contexto AllpFit:
- Campos específicos: `condicao_fisica`, `objetivo`, `analise_ia`, `sugestao_disparo`
- Não se aplica a outros clientes (CDT, InvestBem, etc)
- Difícil manter múltiplas análises diferentes por contexto

### Solução Proposta
1. **Remover campos específicos** do dashboard/tabela principal
2. **Manter apenas campos genéricos** aplicáveis a qualquer negócio
3. **Criar sistema futuro** onde cada cliente escolhe análise customizada (implementação: Johan + Superior)

---

## 📝 ANOTAÇÕES DA REUNIÃO (Bruto)

```
TODAS AS CONVERSAS DE TODAS AS INBOXES E AS METRICAS DISSO
INBOXES COM ATENDIMENTO HUMANO E OUTRAS COM IA
ANALISAR OS FILTROS PARA INBOXES ESPECIFICAS
NOME DA INBOX QUE ATENDEU CADA MENSAGEM E NOME DA IA
DATA DO PRIMEIRO CONTATO DATA DA PRIMEIRA CONVERSA
TIRAR CONDIÇÃO FISICA E OBJETIVO
SUGESTÃO DE DISPARO NA TABELA MESMO
NOME MAPEADO PELA IA
CONVERSA COMPILADA
ANÁLISE DA IA ESCOLHIDA PELO CLIENTE NO PRÓPRIO DASHBOARD
O DISPARO DE IA DEVE SER PADRÃO PARA UM TEMPLATE, QUE MUDA ALGUMAS VARIÁVEIS,
TEM QUE MANTER O TEMPLATE PADRÃO DE DISPARO. A IA MONTA EM CIMA DO TEMPLATE PADRÃO
FAZER FILTROS RÁPIDOS PARECIDO COM O DO SINGLE-TENANT NA TABELA
FILTROS PARA TODAS AS COLUNAS
```

### 🔍 Interpretação das Anotações:

1. **"TODAS AS CONVERSAS DE TODAS AS INBOXES E AS METRICAS DISSO"**
   - Dashboard deve mostrar TODAS as conversas, independente da inbox
   - ⚠️ **IMPORTANTE:** Mostrar métricas de DUAS formas:
     - **Agregadas:** Todas as inboxes juntas (visão geral)
     - **Separadas:** Métricas individuais por cada inbox (visão detalhada)
   - Não filtrar/ocultar nenhuma inbox por padrão
   - Cliente precisa ver performance tanto consolidada quanto por canal

2. **"INBOXES COM ATENDIMENTO HUMANO E OUTRAS COM IA"**
   - Diferenciar inboxes atendidas por humanos vs IA/bot
   - Adicionar coluna indicando tipo de atendimento
   - Métricas separadas para cada tipo

3. **"ANALISAR OS FILTROS PARA INBOXES ESPECIFICAS"**
   - Permitir filtrar por inbox específica
   - Análise detalhada quando filtrado por uma inbox
   - Ver métricas apenas daquela inbox

4. **"NOME DA INBOX QUE ATENDEU CADA MENSAGEM E NOME DA IA"**
   - Coluna: `inbox_name` (ex: "Suporte", "Recepção", "WhatsApp")
   - Coluna: `bot_name` ou `ai_name` (nome da IA que atendeu, se houver)

5. **"DATA DO PRIMEIRO CONTATO DATA DA PRIMEIRA CONVERSA"**
   - Adicionar coluna: `data_primeiro_contato` (primeira mensagem do lead)
   - Diferenciar de `created_at` (criação da conversa no sistema)

6. **"TIRAR CONDIÇÃO FISICA E OBJETIVO"**
   - ✅ Confirma: remover `condicao_fisica` e `objetivo` da tabela

7. **"SUGESTÃO DE DISPARO NA TABELA MESMO"**
   - ✅ **REMOVER** `sugestao_disparo` da tabela por enquanto
   - Feature será re-implementada DEPOIS no sistema de templates
   - Anotação serve apenas para documentar feature futura
   - Primeiro: padronizar sistema para TODOS os clientes
   - Depois: Johan + Superior implementam sistema de IA com templates

8. **"NOME MAPEADO PELA IA"**
   - ✅ Adicionar coluna: `nome_mapeado_bot` (nome extraído pela IA)

9. **"CONVERSA COMPILADA"**
   - Adicionar coluna: `conversa_compilada` ou `resumo_conversa`
   - Primeiras 5-10 mensagens OU resumo gerado
   - Para dar contexto rápido sem abrir conversa inteira

10. **"ANÁLISE DA IA ESCOLHIDA PELO CLIENTE NO PRÓPRIO DASHBOARD"**
    - Feature FUTURA: cliente escolhe tipo de análise no dashboard
    - Sistema gera análise customizada on-demand
    - Não implementar agora (Johan + Superior farão depois)

11. **"O DISPARO DE IA DEVE SER PADRÃO PARA UM TEMPLATE..."**
    - Sistema de templates para mensagens de disparo
    - Template tem variáveis: `{nome}`, `{objetivo}`, `{data_visita}`, etc
    - IA preenche variáveis do template
    - Manter padrão de formato/estrutura
    - **Exemplo:**
      ```
      Template: "Olá {nome}! Vi que você tem interesse em {objetivo}.
                 Que tal agendarmos para {data_sugerida}?"

      IA preenche:
      - {nome} = "João Silva"
      - {objetivo} = "perder peso"
      - {data_sugerida} = "quinta-feira às 18h"
      ```

12. **"FAZER FILTROS RÁPIDOS PARECIDO COM O DO SINGLE-TENANT NA TABELA"**
    - Referência: ver dashboard em `src/app/dashboard.py` (porta 8503)
    - Implementar sistema de filtros similar
    - Filtros rápidos acima da tabela (não apenas na sidebar)

13. **"FILTROS PARA TODAS AS COLUNAS"**
    - TODA coluna da tabela deve ser filtrável
    - Texto: busca parcial
    - Números: range (min-max)
    - Datas: range de datas
    - Booleanos: checkbox
    - Categorias: multi-select dropdown

---

## 🎯 MUDANÇAS SOLICITADAS

### 1. SIMPLIFICAR COLUNAS DA TABELA (Remover Campos Específicos)

#### ❌ Remover da Tabela/Dashboard:
- [ ] `condicao_fisica` (Sedentário | Iniciante | Intermediário | Avançado)
- [ ] `objetivo` (Perda de peso | Ganho de massa | etc)
- [ ] `analise_ia` (análise detalhada em 3-5 parágrafos)
- [ ] `sugestao_disparo` (mensagem personalizada sugerida) - será re-implementado depois
- [ ] `probabilidade_conversao` (score 0-100)

**Motivo:** Campos específicos para contexto de academia (AllpFit), não aplicáveis a outros negócios.

**Ação:**
- Ocultar colunas no dashboard (não deletar do banco ainda - preservar dados existentes)
- Comentar código relacionado
- Documentar como "feature específica AllpFit - aguardando sistema genérico de templates"

#### ✅ Manter Colunas GENÉRICAS:

**Já existentes:**
- [x] `conversation_id` - ID único
- [x] `contact_name` - Nome do contato
- [x] `contact_phone` - Telefone
- [x] `status` - open | resolved | pending
- [x] `is_lead` - Boolean (é lead?)
- [x] `total_mensagens` - Quantidade de mensagens
- [x] `created_at` - Data criação conversa
- [x] `updated_at` - Última atualização

**A adicionar (verificar se já existem):**
- [ ] `nome_mapeado_bot` - Nome completo extraído pelo bot (GERAL)
- [ ] `inbox_name` - Nome da inbox que atendeu
- [ ] `inbox_id` - ID da inbox
- [ ] `primeiro_contato` - Data/hora do primeiro contato
- [ ] `ultimo_contato` - Data/hora do último contato
- [ ] `amostra_conversa` - Primeiras 3-5 mensagens da conversa (para contexto)
- [ ] `tags` - Tags aplicadas na conversa (se houver)

**Observação:** Verificar dashboard single-tenant (porta 8503) para ver colunas úteis já implementadas.

---

### 2. MELHORAR ORGANIZAÇÃO POR INBOX

#### Problema Atual:
- Clientes têm múltiplos inboxes (Suporte, Recepção, Vendas, WhatsApp, Instagram, etc)
- Dashboard atual não separa claramente análises por inbox
- Difícil entender performance de cada canal

#### Solução:
- [ ] Criar seção dedicada "Análise por Inbox" no dashboard
- [ ] Mostrar métricas separadas por inbox:
  - Total de conversas por inbox
  - Taxa de conversão por inbox
  - Leads por inbox
  - Tempo médio de resposta por inbox
- [ ] Adicionar filtro global para selecionar inbox específica
- [ ] Visualização: cards ou tabela comparativa entre inboxes

**Exemplo de visualização:**
```
┌─────────────────────────────────────────────────┐
│ ANÁLISE POR INBOX                              │
├─────────────────────────────────────────────────┤
│ Inbox: Suporte                                 │
│   📊 127 conversas | 23 leads (18%) | Avg: 8h  │
│                                                 │
│ Inbox: Recepção                                │
│   📊 456 conversas | 89 leads (19%) | Avg: 2h  │
│                                                 │
│ Inbox: WhatsApp                                │
│   📊 710 conversas | 275 leads (38%) | Avg: 1h │
└─────────────────────────────────────────────────┘
```

---

### 3. ADICIONAR FILTROS NA TABELA DE CONVERSAS

#### Filtros a Implementar:
- [ ] **Data Primeiro Contato** (range de datas)
- [ ] **Data Último Contato** (range de datas)
- [ ] **Inbox** (dropdown multi-select)
- [ ] **Status** (open | resolved | pending)
- [ ] **É Lead?** (Sim/Não)
- [ ] **Nome** (busca texto)
- [ ] **Telefone** (busca texto)
- [ ] **Total Mensagens** (range numérico: min-max)
- [ ] **Tags** (se existir)

#### Implementação Técnica:
- Usar `st.multiselect`, `st.date_input`, `st.text_input`
- Aplicar filtros combinados no DataFrame antes de exibir
- Manter filtros persistentes na sessão do Streamlit
- Adicionar botão "Limpar Filtros"

**Exemplo de código:**
```python
# Filtros na sidebar
with st.sidebar:
    st.header("🔍 Filtros")

    # Filtro de datas
    col1, col2 = st.columns(2)
    data_inicio = col1.date_input("Data Início")
    data_fim = col2.date_input("Data Fim")

    # Filtro inbox
    inboxes_selecionadas = st.multiselect(
        "Inboxes",
        options=df['inbox_name'].unique()
    )

    # Filtro status
    status_selecionado = st.multiselect(
        "Status",
        options=['open', 'resolved', 'pending']
    )

    # Filtro é lead
    filtro_lead = st.radio("É Lead?", ["Todos", "Sim", "Não"])
```

---

### 4. ARQUIVAR MÉTRICAS IRRELEVANTES (Não Deletar!)

#### ❌ Métricas a Remover do Dashboard Ativo:

**Funil de Conversão:**
- [ ] Gráfico de funil (stages: Contato → Lead → Visita → Matrícula)
- [ ] Código relacionado em `client_dashboard.py`

**Métricas de Qualidade:**
- [ ] Taxa de engajamento
- [ ] Tempo médio de resposta
- [ ] Satisfação do cliente (se houver)
- [ ] Score de qualidade de atendimento

**Outros (a confirmar):**
- [ ] Listar após análise do código atual

#### ✅ Onde Arquivar:

Criar estrutura:
```
src/multi_tenant/dashboards/
├── _archived/                    # NOVA pasta
│   ├── README.md                 # Explicação do que está aqui
│   ├── funil_conversao.py       # Código do funil
│   ├── metricas_qualidade.py    # Código de qualidade
│   └── components/               # Componentes visuais antigos
├── client_dashboard.py           # Dashboard ativo (simplificado)
├── admin_dashboard.py
└── app.py
```

**Conteúdo do README.md na pasta _archived:**
```markdown
# Dashboards e Componentes Arquivados

Esta pasta contém código de dashboards e métricas que foram
removidos da versão ativa após reunião com superiores em 2025-11-11.

O código foi preservado para:
- Referência futura
- Possível reuso em contextos específicos
- Histórico de features implementadas

## Arquivos:
- funil_conversao.py: Gráficos de funil de vendas
- metricas_qualidade.py: Métricas de qualidade de atendimento

Não deletar! Apenas não está em uso no dashboard principal.
```

---

## 🔍 ANÁLISE NECESSÁRIA

### 1. Verificar Dashboard Single-Tenant (Porta 8503)
- [ ] Analisar arquivo: `src/app/dashboard.py`
- [ ] Identificar colunas úteis que podem ser migradas
- [ ] Verificar se `primeiro_contato`, `ultimo_contato`, `amostra_conversa` já existem
- [ ] Documentar diferenças entre single-tenant e multi-tenant

### 2. Verificar Colunas no Banco de Dados
```sql
-- Verificar colunas existentes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'conversations_analytics'
ORDER BY ordinal_position;
```

**Colunas a verificar:**
- [ ] `nome_mapeado_bot` (já existe?)
- [ ] `inbox_name` / `inbox_id` (já existe?)
- [ ] `primeiro_contato` (ou usar `created_at`?)
- [ ] `ultimo_contato` (ou usar `updated_at`?)
- [ ] `amostra_conversa` (existe?)

### 3. Analisar Código de Métricas Atual
- [ ] Listar todas as métricas em `client_dashboard.py`
- [ ] Identificar quais são "funil de conversão"
- [ ] Identificar quais são "métricas de qualidade"
- [ ] Separar o que vai para `_archived/`

---

## 📝 IMPLEMENTAÇÃO FUTURA (Johan + Superior)

### Sistema de Análise Customizável por Cliente

**Objetivo:** Cada cliente escolhe qual análise quer que IA faça em seus dados.

**Conceito:**
```python
# Template base de análise
class BaseAnalysisTemplate:
    def __init__(self, client_context):
        self.context = client_context

    def generate_prompt(self, conversation):
        # Template genérico + contexto específico do cliente
        pass

# Cliente AllpFit escolhe:
allpfit_analysis = {
    "campos": ["condicao_fisica", "objetivo", "sugestao_disparo"],
    "prompt_template": "analise_academia.txt",
    "model": "gpt-4o-mini"
}

# Cliente CDT Mossoró escolhe:
cdt_analysis = {
    "campos": ["interesse_curso", "nivel_escolaridade", "disponibilidade"],
    "prompt_template": "analise_educacao.txt",
    "model": "gpt-4o-mini"
}
```

**Implementação será feita em fase futura.**

---

## ✅ CHECKLIST DE VALIDAÇÃO (Antes de Implementar)

- [ ] Johan revisou documento e confirmou entendimento
- [ ] Anotações da reunião foram anexadas/revisadas
- [ ] Prioridades foram definidas (o que fazer primeiro)
- [ ] Estrutura de pastas `_archived/` foi aprovada
- [ ] Lista de colunas a adicionar foi validada
- [ ] Lista de métricas a arquivar foi validada
- [ ] Plano de implementação foi definido

---

## 📊 IMPACTO DAS MUDANÇAS

### Código Afetado:
- `src/multi_tenant/dashboards/client_dashboard.py` (modificação grande)
- `src/multi_tenant/etl_v4/analyzers/openai_analyzer.py` (comentar campos específicos)
- Banco de dados (adicionar colunas novas se necessário)

### Tempo Estimado:
- Análise e documentação: **2-3h** ✅ (em andamento)
- Implementação das mudanças: **6-8h**
- Testes e ajustes: **2-3h**
- **Total: 10-14h (~2 dias)**

### Compatibilidade:
- ✅ Dados existentes no banco permanecem intactos
- ✅ Código antigo preservado em `_archived/`
- ✅ Possibilidade de reverter mudanças facilmente

---

## 🚀 PRÓXIMOS PASSOS

1. **Agora:**
   - [x] Criar este documento de planejamento
   - [ ] Johan revisar e validar entendimento
   - [ ] Adicionar anotações da reunião ao documento

2. **Depois da validação:**
   - [ ] Analisar dashboard single-tenant (8503)
   - [ ] Analisar colunas do banco atual
   - [ ] Criar estrutura `_archived/`
   - [ ] Implementar mudanças (em ordem de prioridade)

3. **Por último:**
   - [ ] Testar com dados reais
   - [ ] Validar com superiores
   - [ ] Commitar mudanças
   - [ ] Atualizar documentação geral

---

**Última atualização:** 2025-11-11
**Responsável:** Johan + Claude
**Aprovação necessária:** Superiores (após implementação)