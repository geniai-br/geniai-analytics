# FASE 8: Sistema de Análise Inteligente com OpenAI (Multi-Tenant)

**Data:** 13/Novembro/2025
**Versão:** 2.0 (Definitiva)
**Autores:** Isaac (Dev Lead), Hyago (Product Owner)
**Status:** 📋 Aprovado para Implementação
**Prioridade:** 🔥 Alta

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Regra de Negócio: 24h de Inatividade](#regra-de-negócio-24h-de-inatividade)
3. [Objetivos e Requisitos](#objetivos-e-requisitos)
4. [Arquitetura Técnica](#arquitetura-técnica)
5. [Análise de Contexto e Tipos de Remarketing](#análise-de-contexto-e-tipos-de-remarketing)
6. [Sistema de Templates](#sistema-de-templates)
7. [Integração com ETL](#integração-com-etl)
8. [Interface do Dashboard](#interface-do-dashboard)
9. [Modelo de Dados](#modelo-de-dados)
10. [Custos e Performance](#custos-e-performance)
11. [Cronograma de Implementação](#cronograma-de-implementação)
12. [Riscos e Mitigações](#riscos-e-mitigações)

---

## 🎯 VISÃO GERAL

### **Problema Atual**

O dashboard multi-tenant exibe conversas compiladas, mas não fornece:
- ❌ Análise inteligente do contexto da conversa
- ❌ Classificação automática do tipo de conversa (venda, suporte, etc.)
- ❌ Sugestões personalizadas de **remarketing** para leads inativos
- ❌ Priorização de leads por potencial de conversão
- ❌ Diferenciação entre follow-up (0-24h) e remarketing (24h+)

### **Solução Proposta**

Sistema de análise inteligente que:
- ✅ Analisa automaticamente conversas de leads **após 24h de inatividade**
- ✅ Classifica o contexto e intenção da conversa
- ✅ Gera análise detalhada com insights acionáveis
- ✅ Cria sugestões de **remarketing** personalizadas baseadas em templates
- ✅ Permite análise sob demanda para casos urgentes (botão no dashboard)

---

## ⏰ REGRA DE NEGÓCIO: 24h DE INATIVIDADE

### **Decisão Estratégica (Hyago - Product Owner)**

> **"A análise de IA deve acontecer quando a última mensagem da conversa tenha passado de mais de 24 horas. Isso marca a transição da janela de follow-up para a janela de remarketing."**

### **Fundamento da Regra:**

| Janela | Período | Responsabilidade | Ação | Custo |
|--------|---------|------------------|------|-------|
| **Follow-up** | 0-24h | Atendente humano | Manual, imediato | R$ 0 (tempo humano) |
| **Remarketing** | 24h+ | IA + Automação | Análise + sugestão | R$ 0.002/lead |

### **Por que 24h é o Ponto de Corte Ideal:**

✅ **Fundamento de Negócio:**
- Follow-up manual (0-24h): Atendente responde enquanto conversa está "quente"
- Remarketing automático (24h+): Lead esfriou, precisa de abordagem planejada

✅ **Fundamento Técnico:**
- 24h garante conversa completa (não é só pausa de almoço)
- Taxa de reabertura < 5% após 24h (evita re-análises)
- Tempo suficiente para o lead refletir sobre a oferta

✅ **Fundamento Econômico:**
- Custo zero com análises prematuras de conversas incompletas
- Zero desperdício com re-análises (conversa já está finalizada)

---

## 📊 OBJETIVOS E REQUISITOS

### **Objetivos de Negócio**

| # | Objetivo | Métrica de Sucesso |
|---|----------|-------------------|
| 1 | Aumentar taxa de conversão de leads inativos | +20% conversão (remarketing) em 3 meses |
| 2 | Automatizar remarketing de leads frios | 100% leads 24h+ com sugestão |
| 3 | Padronizar mensagens de remarketing | Template consistency > 95% |
| 4 | Reduzir custo de remarketing manual | -80% tempo humano em remarketing |

### **Requisitos Funcionais**

#### **RF1: Análise Automática de Leads Inativos (24h+)**

```gherkin
DADO que uma conversa é identificada como lead
  E a última mensagem foi há mais de 24 horas
  E a conversa tem pelo menos 3 mensagens do cliente
QUANDO o Worker IA executar
ENTÃO o sistema deve:
  - Analisar o contexto completo da conversa
  - Identificar tipo de remarketing (RECENTE, MEDIO, FRIO)
  - Extrair dados estruturados (objetivo, interesse, objeções)
  - Gerar análise textual com insights
  - Calcular score de prioridade (0-5)
  - Criar sugestão de remarketing personalizada
```

#### **RF2: Geração de Sugestão de Remarketing**

```gherkin
DADO que uma conversa inativa foi analisada
QUANDO o sistema gera a sugestão de remarketing
ENTÃO deve:
  - Usar template específico baseado no tempo de inatividade
    * 24-48h: REMARKETING_RECENTE (tom casual)
    * 48h-7d: REMARKETING_MEDIO (tom direto + oferta)
    * 7d+: REMARKETING_FRIO (tom formal + resgate)
  - Personalizar com dados extraídos (nome, interesse, contexto)
  - Seguir tom de voz configurado por tenant
  - Incluir call-to-action claro
  - Limitar a 3-5 frases (200-300 caracteres)
```

#### **RF3: Detecção de Reabertura e Reset de Análise**

```gherkin
DADO que um lead tinha análise de remarketing salva
  E o cliente respondeu (reabertura da conversa)
QUANDO o ETL detectar nova mensagem
ENTÃO deve:
  - Invalidar análise antiga (status = 'resetado')
  - Limpar sugestão de remarketing
  - Aguardar novo período de 24h para re-análise
```

#### **RF4: Análise Sob Demanda (Dashboard)**

```gherkin
DADO que um usuário visualiza o dashboard
  E há leads inativos 24h+ sem análise
QUANDO o usuário clicar em "Analisar Pendentes Agora"
ENTÃO deve:
  - Exibir contador de leads pendentes (24h+)
  - Processar em background (máx 50 leads por vez)
  - Atualizar dashboard automaticamente ao concluir
  - Exibir progresso e status em tempo real
```

#### **RF5: Visualização no Dashboard**

```gherkin
DADO que um lead inativo tem análise disponível
QUANDO o usuário visualiza a tabela
ENTÃO deve exibir:
  - Status: ✅ Analisado | ⏳ Aguardando 24h | 🔄 Ativo (<24h)
  - Tempo de inatividade (ex: "26h inativo")
  - Tipo de remarketing (badge colorido)
  - Score de prioridade (0-5 estrelas)
  - Expander com análise completa + sugestão
  - Botão "Copiar Sugestão" para WhatsApp
```

### **Requisitos Não-Funcionais**

| ID | Requisito | Especificação |
|----|-----------|---------------|
| RNF1 | Performance | Max 15s por análise (GPT-4o-mini) |
| RNF2 | Custo | Max R$ 0.003/lead (target: R$ 0.002) |
| RNF3 | Disponibilidade | 99% uptime (tolera falhas temporárias OpenAI) |
| RNF4 | Escalabilidade | Suportar 1000+ leads/dia por tenant |
| RNF5 | Multi-tenancy | Isolamento total de dados por tenant |
| RNF6 | Auditoria | Log completo de todas as análises (custo, tokens, modelo) |
| RNF7 | Precisão | Taxa de reabertura < 5% (valida 24h como gatilho) |

---

## 🏗️ ARQUITETURA TÉCNICA

### **Fluxo Completo (Simplificado):**

```
┌─────────────────────────────────────────────────────────────────┐
│  1. ETL (A cada 30 min) - "O Coletor"                          │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Extrai novas conversas do Chatwoot                          │
│  ✅ Atualiza campo 'ultimo_contato' (última mensagem)           │
│  ✅ Identifica is_lead = true                                   │
│  ✅ Detecta REABERTURA (nova msg após análise) e reseta         │
│  ❌ NÃO analisa com IA (não é responsabilidade do ETL)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Worker IA (Integrado no ETL ou separado)                   │
├─────────────────────────────────────────────────────────────────┤
│  Query inteligente:                                             │
│    WHERE is_lead = true                                         │
│      AND analise_ia IS NULL                                     │
│      AND ultimo_contato < NOW() - INTERVAL '24 hours'  ← CHAVE │
│      AND contact_messages_count >= 3                            │
│                                                                 │
│  ✅ Processa APENAS leads inativos há 24h+                      │
│  ✅ Classifica tipo de remarketing (tempo inativo)              │
│  ✅ Chama OpenAI GPT-4o-mini para análise                       │
│  ✅ Salva resultado no banco                                    │
│  ✅ Marca como 'concluido'                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Dashboard (Streamlit) - "A Visualização"                   │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Exibe análises de leads inativos (24h+)                     │
│  ✅ Mostra tempo de inatividade (26h, 3d, 2w)                   │
│  ✅ Badge de tipo de remarketing (RECENTE/MEDIO/FRIO)           │
│  ✅ Botão "Analisar Pendentes" (manual, leads 24-48h)           │
│  ✅ Status: ✅ Analisado | ⏳ Aguardando 24h | 🔄 Ativo        │
└─────────────────────────────────────────────────────────────────┘
```

### **Componentes do Sistema**

#### **1. OpenAILeadAnalyzer (Core)**

```
src/multi_tenant/etl_v4/analyzers/openai_lead_analyzer.py

Responsabilidades:
- Construir prompt contextual baseado em tenant config
- Incluir tempo de inatividade no contexto (remarketing recente/médio/frio)
- Chamar OpenAI API (GPT-4o-mini)
- Parsear resposta JSON
- Validar dados retornados
- Aplicar template de remarketing apropriado
- Retry em caso de falha (3x)
- Log de tokens e custo
```

#### **2. TemplateManager (Templates de Remarketing)**

```
src/multi_tenant/utils/template_manager.py

Responsabilidades:
- Gerenciar templates de remarketing por tempo de inatividade
- Suportar variáveis dinâmicas: {nome}, {interesse}, {tempo_inativo}
- Permitir customização por tenant (futuro)
- Validar template antes de aplicar
- Fallback para template genérico
```

#### **3. ETL Integration (Pipeline + Reset)**

```
src/multi_tenant/etl_v4/pipeline.py (MODIFICAÇÃO)

Adiciona FASE 3.5: RESET REOPENED CONVERSATIONS (após LOAD)
- Detecta conversas reabertas (ultima_mensagem > analisado_em)
- Reseta análise antiga (status = 'resetado')
- Log de IDs resetados para auditoria

Adiciona FASE 4: ANALYZE INACTIVE LEADS (após RESET)
- Busca leads inativos 24h+ sem análise
- Processa em batch (10-50 por vez)
- Atualiza estatísticas (tokens, custo, tempo)
- Loga erros sem interromper ETL
```

#### **4. Dashboard Integration**

```
src/multi_tenant/dashboards/client_dashboard.py (MODIFICAÇÃO)

Adiciona seção "Análise de Remarketing":
- Card: X analisados | Y pendentes (24h+) | Z ativos (<24h)
- Botão "Analisar Pendentes (24h+)"
- Coluna "Status Análise" + "Tempo Inativo"
- Coluna "Tipo Remarketing" (badge: RECENTE/MEDIO/FRIO)
- Expander "Análise Completa" por lead
- Botão "Copiar Sugestão" (clipboard.js)
```

---

## 🔍 ANÁLISE DE CONTEXTO E TIPOS DE REMARKETING

### **Tipos de Remarketing (Baseado em Tempo de Inatividade)**

| Tipo | Tempo Inativo | Estratégia | Tom | Urgência | Template |
|------|---------------|------------|-----|----------|----------|
| **REMARKETING_RECENTE** | 24h - 48h | Lembrete suave | 😊 Casual | Baixa | "Vi que você perguntou ontem..." |
| **REMARKETING_MEDIO** | 48h - 7 dias | Oferta direta | 💼 Profissional | Média | "Ainda tem interesse? Temos oferta..." |
| **REMARKETING_FRIO** | 7+ dias | Resgate agressivo | 🎯 Formal | Alta | "Notamos seu interesse semanas atrás..." |

### **Dados Extraídos por Análise**

```json
{
  "tipo_conversa": "REMARKETING_RECENTE",
  "tipo_remarketing": "REMARKETING_RECENTE",
  "tempo_inativo_horas": 26.5,
  "analise_ia": "Lead João demonstrou interesse em CrossFit há 26 horas...",
  "sugestao_disparo": "Oi João! Vi que você demonstrou interesse em CrossFit ontem...",
  "score_prioridade": 4,
  "dados_extraidos": {
    "objetivo": "Perda de peso",
    "condicao_fisica": "Sedentário",
    "objecoes": ["Preço", "Distância"],
    "urgencia": "Média",
    "contexto_adicional": "Mencionou ter disponibilidade às 18h"
  },
  "metadados": {
    "modelo": "gpt-4o-mini-2024-07-18",
    "tokens_prompt": 450,
    "tokens_completion": 280,
    "tokens_total": 730,
    "custo_brl": 0.002,
    "tempo_segundos": 12.3,
    "analisado_em": "2025-11-13T10:30:00Z"
  }
}
```

### **Lógica de Classificação:**

```python
def get_remarketing_type(tempo_inativo_horas: float) -> str:
    """
    Classifica tipo de remarketing baseado em tempo de inatividade

    Regra de Negócio (Hyago):
    - 24-48h: RECENTE (lead ainda "morno", tom casual)
    - 48h-7d: MEDIO (lead esfriando, oferta direta)
    - 7d+: FRIO (lead frio, resgate agressivo)

    Args:
        tempo_inativo_horas: Horas desde última mensagem

    Returns:
        Tipo de remarketing (RECENTE, MEDIO, FRIO)
    """
    if 24 <= tempo_inativo_horas < 48:
        return 'REMARKETING_RECENTE'
    elif 48 <= tempo_inativo_horas < 168:  # 7 dias
        return 'REMARKETING_MEDIO'
    else:  # 7+ dias
        return 'REMARKETING_FRIO'
```

---

## 📝 SISTEMA DE TEMPLATES

### **Estrutura de Templates por Tipo de Remarketing**

Templates são definidos por **tempo de inatividade** e suportam **variáveis dinâmicas**.

#### **Variáveis Disponíveis**

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `{nome}` | Nome do lead (ou "você" se não identificado) | "João" |
| `{nome_mapeado}` | Nome extraído pelo bot na conversa | "João Silva" |
| `{objetivo}` | Objetivo mencionado na conversa | "perda de peso" |
| `{inbox}` | Nome do inbox/canal | "WhatsApp AllpFit" |
| `{interesse}` | Interesse específico extraído | "CrossFit" |
| `{tempo_inativo}` | Tempo desde última mensagem | "2 dias", "1 semana" |
| `{objecao}` | Principal objeção identificada | "preço" |

#### **Template: REMARKETING_RECENTE (24-48h)**

```python
TEMPLATE_REMARKETING_RECENTE = """
Oi {nome}! 😊

Vi que você demonstrou interesse em {interesse} ontem. Ficou com alguma dúvida?

Temos horários disponíveis essa semana e a primeira aula é por nossa conta! 🎉

Me avisa se quiser saber mais!

{inbox}
"""
```

#### **Template: REMARKETING_MEDIO (48h-7d)**

```python
TEMPLATE_REMARKETING_MEDIO = """
Oi {nome}!

Vi que você perguntou sobre {interesse} há alguns dias. Ainda tem interesse?

Estamos com uma promoção especial esta semana: **primeira semana grátis** para novos alunos! 💪

Posso te enviar mais detalhes?

{inbox}
"""
```

#### **Template: REMARKETING_FRIO (7d+)**

```python
TEMPLATE_REMARKETING_FRIO = """
Olá {nome},

Notamos seu interesse em {interesse} há {tempo_inativo}.

Gostaríamos de oferecer uma oportunidade especial: **aula experimental gratuita + avaliação física**.

Temos disponibilidade nos próximos dias. Gostaria de agendar?

Aguardamos seu retorno.

Atenciosamente,
{inbox}
"""
```

#### **Template Genérico (Fallback)**

```python
TEMPLATE_GENERICO_REMARKETING = """
Oi {nome}!

Vi sua conversa conosco há {tempo_inativo} e gostaria de saber se ainda tem interesse.

Estou à disposição para tirar qualquer dúvida! 😊

{inbox}
"""
```

### **Customização por Tenant (FASE 9 - Futura)**

```python
# Estrutura para permitir templates customizados
tenant_templates = {
    "tenant_id": 1,
    "templates_remarketing": {
        "REMARKETING_RECENTE": "Template customizado AllpFit (24-48h)...",
        "REMARKETING_MEDIO": "Template customizado AllpFit (48h-7d)...",
        "REMARKETING_FRIO": "Template customizado AllpFit (7d+)..."
    },
    "variaveis_customizadas": {
        "assinatura": "Equipe AllpFit 💪",
        "cta_padrao": "Agende sua aula experimental gratuita!"
    }
}
```

---

## 🔄 INTEGRAÇÃO COM ETL

### **Modificações no Pipeline**

#### **1. Banco de Dados: Nenhuma Coluna Nova Necessária**

O campo `ultimo_contato` já existe e é suficiente. Apenas adicionar colunas de análise:

```sql
-- Adicionar colunas de análise IA (se não existirem)
ALTER TABLE multi_tenant.conversations
ADD COLUMN IF NOT EXISTS tipo_conversa VARCHAR(50),
ADD COLUMN IF NOT EXISTS analise_ia TEXT,
ADD COLUMN IF NOT EXISTS sugestao_disparo TEXT,
ADD COLUMN IF NOT EXISTS score_prioridade INTEGER CHECK (score_prioridade BETWEEN 0 AND 5),
ADD COLUMN IF NOT EXISTS dados_extraidos_ia JSONB,
ADD COLUMN IF NOT EXISTS metadados_analise_ia JSONB,
ADD COLUMN IF NOT EXISTS analisado_em TIMESTAMP;

-- Índice para query do Worker IA (buscar leads inativos 24h+)
CREATE INDEX IF NOT EXISTS idx_conversations_inactive_leads_analysis
ON multi_tenant.conversations(tenant_id, is_lead, ultimo_contato)
WHERE is_lead = true AND analise_ia IS NULL;

-- Índice para detectar reabertura no ETL
CREATE INDEX IF NOT EXISTS idx_conversations_reopened
ON multi_tenant.conversations(tenant_id, ultimo_contato, analisado_em)
WHERE analise_ia IS NOT NULL;
```

#### **2. ETL FASE 3.5: Detectar e Resetar Conversas Reabertas**

```python
# src/multi_tenant/etl_v4/pipeline.py

def detect_and_reset_reopened_conversations(local_engine, tenant_id):
    """
    Detecta conversas que foram reabertas (nova mensagem após análise)
    e reseta análise antiga.

    Regra:
    - Se ultimo_contato > analisado_em (nova mensagem depois da análise)
    - E ultimo_contato < NOW() - 24h (mensagem recente, conversa reativou)
    - Então: limpar análise (será re-analisada após novo período de 24h)
    """
    query = text("""
        UPDATE multi_tenant.conversations
        SET
            analise_ia = NULL,
            sugestao_disparo = NULL,
            tipo_conversa = NULL,
            score_prioridade = NULL,
            dados_extraidos_ia = NULL,
            analisado_em = NULL,
            metadados_analise_ia = jsonb_set(
                COALESCE(metadados_analise_ia, '{}'::jsonb),
                '{resetado_em}',
                to_jsonb(NOW())
            )
        WHERE
            tenant_id = :tenant_id
            AND analise_ia IS NOT NULL                        -- Tinha análise
            AND ultimo_contato > analisado_em                 -- Nova msg após análise
            AND ultimo_contato > NOW() - INTERVAL '24 hours'  -- Msg recente (<24h)
        RETURNING conversation_id
    """)

    with local_engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id})
        resetados = result.fetchall()

        if resetados:
            logger.info(
                f"🔄 {len(resetados)} conversas reabertas detectadas. "
                f"Análises invalidadas."
            )
            ids = [row[0] for row in resetados]
            logger.debug(f"IDs resetados: {ids}")

        conn.commit()
```

#### **3. ETL FASE 4: Analisar Leads Inativos (24h+)**

```python
# src/multi_tenant/etl_v4/pipeline.py

# Após FASE 3 (LOAD) e FASE 3.5 (RESET)

if analyze_leads_enabled:
    logger.info("FASE 4: ANALYZE INACTIVE LEADS (24h+)")
    logger.info("-" * 80)

    # Buscar leads inativos 24h+ sem análise
    query = text("""
        SELECT
            conversation_id,
            conversation_display_id,
            conversa_compilada,
            contact_name,
            inbox_name,
            contact_messages_count,
            ultimo_contato,
            EXTRACT(EPOCH FROM (NOW() - ultimo_contato)) / 3600 AS horas_inativo
        FROM multi_tenant.conversations
        WHERE
            tenant_id = :tenant_id
            AND is_lead = true
            AND analise_ia IS NULL
            AND ultimo_contato < NOW() - INTERVAL '24 hours'  -- REGRA: 24h+
            AND contact_messages_count >= 3
            AND conversa_compilada IS NOT NULL
        ORDER BY ultimo_contato ASC
        LIMIT :limit
    """)

    with self.local_engine.connect() as conn:
        result = conn.execute(query, {
            'tenant_id': tenant_id,
            'limit': 10  # Limite para não atrasar ETL
        })
        leads = [dict(row._mapping) for row in result]

    if not leads:
        logger.info("Nenhum lead inativo (24h+) para analisar")
    else:
        logger.info(f"Encontrados {len(leads)} leads inativos para análise")

        # Inicializar analisador
        analyzer = OpenAILeadAnalyzer(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            tenant_id=tenant_id,
            model="gpt-4o-mini-2024-07-18"
        )

        analyzed_count = 0
        failed_count = 0
        total_tokens = 0
        total_cost_brl = 0.0

        for lead in leads:
            try:
                # Classificar tipo de remarketing
                tipo_remarketing = analyzer.get_remarketing_type(
                    lead['horas_inativo']
                )

                # Analisar lead
                resultado = analyzer.analyze_lead(
                    conversation_id=lead['conversation_id'],
                    conversa_compilada=lead['conversa_compilada'],
                    contact_name=lead['contact_name'],
                    inbox_name=lead['inbox_name'],
                    tipo_remarketing=tipo_remarketing,
                    tempo_inativo_horas=lead['horas_inativo']
                )

                # Salvar no banco
                save_analysis_to_db(
                    local_engine=self.local_engine,
                    conversation_id=lead['conversation_id'],
                    resultado=resultado
                )

                analyzed_count += 1
                total_tokens += resultado['metadados']['tokens_total']
                total_cost_brl += resultado['metadados']['custo_brl']

                logger.info(
                    f"✅ Lead {lead['conversation_display_id']} analisado: "
                    f"{resultado['tipo_conversa']} ({lead['horas_inativo']:.1f}h inativo)"
                )

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Erro ao analisar {lead['conversation_id']}: {e}")

        # Log estatísticas
        logger.info(
            f"ANÁLISE CONCLUÍDA: {analyzed_count} sucesso, {failed_count} falhas | "
            f"Tokens: {total_tokens} | Custo: R$ {total_cost_brl:.4f}"
        )

        # Salvar stats no etl_control
        update_etl_stats(
            execution_id=execution_id,
            ai_analyzed=analyzed_count,
            ai_tokens=total_tokens,
            ai_cost_brl=total_cost_brl
        )
```

### **Controle de Custo**

```python
# Configurações de limite de custo (env vars)
ANALYZE_LEADS_ENABLED = os.getenv('ANALYZE_LEADS_ENABLED', 'true').lower() == 'true'
ANALYZE_LEADS_LIMIT = int(os.getenv('ANALYZE_LEADS_LIMIT', '10'))  # Por ETL run
ANALYZE_LEADS_MAX_COST_BRL = float(os.getenv('ANALYZE_LEADS_MAX_COST_BRL', '0.10'))

# Lógica de controle no loop de análise
if total_cost_brl >= ANALYZE_LEADS_MAX_COST_BRL:
    logger.warning(
        f"⚠️ Custo máximo atingido (R$ {total_cost_brl:.4f}). "
        f"Parando análise (restam {len(leads) - analyzed_count} leads)"
    )
    break
```

---

## 🖥️ INTERFACE DO DASHBOARD

### **Seção: Análise de Remarketing (NOVA)**

#### **Layout Proposto:**

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 ANÁLISE DE REMARKETING (Leads Inativos 24h+)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ ✅ 47       │  │ ⏳ 12       │  │ 🔄  8        │            │
│  │ Analisados  │  │ Aguardando  │  │ Ativos      │            │
│  │ (24h+)      │  │ 24h         │  │ (<24h)      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  [🤖 Analisar 12 Pendentes (24h+)]  [📥 Baixar Sugestões]     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TABELA DE LEADS (Com Tempo de Inatividade)                    │
├─────────────────────────────────────────────────────────────────┤
│  Status | Tipo        | Nome      | Inatividade | Score | Ações│
│  ✅     | RECENTE     | João Silva| 26h         | ⭐⭐⭐⭐  | [Ver][📋]│
│  ✅     | MEDIO       | Maria S.  | 3d 5h       | ⭐⭐⭐   | [Ver][📋]│
│  ⏳     | -           | Pedro O.  | 15h         | -      | [Em 9h]│
│  🔄     | -           | Ana Costa | 8h          | -      | -      │
└─────────────────────────────────────────────────────────────────┘
```

#### **Código Streamlit:**

```python
def show_remarketing_analysis_section(df: pd.DataFrame, tenant_id: int):
    """
    Seção de análise de remarketing no dashboard
    """
    st.markdown("### 📊 Análise de Remarketing (Leads Inativos 24h+)")

    # Calcular tempo de inatividade
    now = datetime.now()
    df['horas_inativo'] = (now - df['ultimo_contato']).dt.total_seconds() / 3600

    # Classificar leads
    analisados = len(df[df['analise_ia'].notna()])
    aguardando_24h = len(df[(df['horas_inativo'] >= 24) & (df['analise_ia'].isna())])
    ativos = len(df[df['horas_inativo'] < 24])

    # Cards de resumo
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("✅ Analisados", analisados, help="Leads inativos 24h+ com análise")

    with col2:
        st.metric("⏳ Aguardando 24h", aguardando_24h, help="Leads inativos 24h+ sem análise")

    with col3:
        st.metric("🔄 Ativos", ativos, help="Leads com última msg < 24h")

    # Botão analisar pendentes
    col_btn, col_download = st.columns([2, 1])

    with col_btn:
        if aguardando_24h > 0:
            if st.button(f"🤖 Analisar {aguardando_24h} Pendentes (24h+)"):
                with st.spinner(f"Analisando {aguardando_24h} leads..."):
                    analyze_pending_inactive_leads(tenant_id, limit=aguardando_24h)
                    st.success(f"✅ {aguardando_24h} leads analisados!")
                    st.rerun()
        else:
            st.success("✅ Todos os leads inativos (24h+) foram analisados!")

    with col_download:
        if analisados > 0:
            csv = export_remarketing_suggestions_csv(df[df['analise_ia'].notna()])
            st.download_button(
                label="📥 Baixar Sugestões",
                data=csv,
                file_name=f"sugestoes_remarketing_{datetime.now():%Y%m%d}.csv",
                mime="text/csv"
            )

    st.divider()

    # Tabela com leads
    display_leads_table_with_inactivity(df)

    # Expanders com análises
    show_remarketing_analysis_expanders(df[df['analise_ia'].notna()])


def display_leads_table_with_inactivity(df: pd.DataFrame):
    """
    Tabela de leads com tempo de inatividade e status
    """
    # Adicionar coluna de status
    df['status_badge'] = df.apply(get_lead_status_badge_with_inactivity, axis=1)

    # Adicionar badge de tipo de remarketing
    df['tipo_badge'] = df['tipo_conversa'].apply(format_tipo_remarketing_badge)

    # Adicionar tempo de inatividade formatado
    df['inatividade_formatada'] = df['horas_inativo'].apply(format_tempo_inatividade)

    # Adicionar score visual
    df['score_visual'] = df['score_prioridade'].apply(format_score_stars)

    # Selecionar colunas
    display_df = df[[
        'status_badge',
        'tipo_badge',
        'contact_name',
        'inatividade_formatada',
        'score_visual'
    ]].copy()

    display_df.columns = ['Status', 'Tipo Remarketing', 'Nome', 'Inatividade', 'Score']

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def get_lead_status_badge_with_inactivity(row):
    """
    Retorna badge de status baseado em tempo de inatividade
    """
    horas = row['horas_inativo']

    # Lead com análise completa
    if pd.notna(row['analise_ia']):
        return '✅ Analisado'

    # Lead inativo 24h+ (aguardando análise)
    if horas >= 24:
        return '⏳ Aguardando Análise'

    # Lead ativo (<24h)
    horas_restantes = int(24 - horas)
    return f'🔄 Ativo (análise em {horas_restantes}h)'


def format_tempo_inatividade(horas: float) -> str:
    """
    Formata tempo de inatividade de forma legível
    """
    if pd.isna(horas):
        return "-"

    if horas < 24:
        return f"{int(horas)}h"
    elif horas < 168:  # < 7 dias
        dias = int(horas // 24)
        horas_rest = int(horas % 24)
        return f"{dias}d {horas_rest}h"
    else:  # 7+ dias
        semanas = int(horas // 168)
        return f"{semanas}sem"


def format_tipo_remarketing_badge(tipo: str) -> str:
    """Formata tipo de remarketing como badge colorido"""
    badges = {
        'REMARKETING_RECENTE': '🟢 Recente (24-48h)',
        'REMARKETING_MEDIO': '🟡 Médio (48h-7d)',
        'REMARKETING_FRIO': '🔴 Frio (7d+)',
    }
    return badges.get(tipo, '-')
```

---

## 💾 MODELO DE DADOS

### **Tabela: multi_tenant.conversations (Modificações)**

```sql
-- Colunas adicionadas (FASE 8)
tipo_conversa VARCHAR(50)           -- REMARKETING_RECENTE, MEDIO, FRIO
analise_ia TEXT                     -- Análise textual gerada pela IA
sugestao_disparo TEXT               -- Sugestão de mensagem de remarketing
score_prioridade INTEGER            -- 0-5 (prioridade de follow-up)
dados_extraidos_ia JSONB            -- JSON com dados estruturados
metadados_analise_ia JSONB          -- Metadados (tokens, custo, modelo, tempo)
analisado_em TIMESTAMP              -- Quando foi analisado

-- Coluna JÁ EXISTENTE (usada como gatilho):
ultimo_contato TIMESTAMP            -- Última mensagem da conversa (já existe!)

-- Query para análise (CHAVE):
-- WHERE ultimo_contato < NOW() - INTERVAL '24 hours'
```

### **Exemplo de `dados_extraidos_ia`:**

```json
{
  "objetivo": "Perda de peso",
  "condicao_fisica": "Sedentário",
  "objecoes": ["Preço", "Distância"],
  "urgencia": "Média",
  "horarios_mencionados": ["18h"],
  "interesses": ["CrossFit", "Musculação"],
  "tempo_inativo_horas": 26.5,
  "tipo_remarketing": "REMARKETING_RECENTE"
}
```

### **Exemplo de `metadados_analise_ia`:**

```json
{
  "modelo": "gpt-4o-mini-2024-07-18",
  "tokens_prompt": 450,
  "tokens_completion": 280,
  "tokens_total": 730,
  "custo_brl": 0.002,
  "tempo_segundos": 12.3,
  "versao_prompt": "1.0",
  "template_usado": "REMARKETING_RECENTE_v1",
  "resetado_em": null
}
```

---

## 💰 CUSTOS E PERFORMANCE

### **Estimativa de Custos (OpenAI GPT-4o-mini)**

#### **Modelo: GPT-4o-mini (Recomendado)**

| Métrica | Valor |
|---------|-------|
| **Custo por 1M tokens (input)** | $0.150 USD |
| **Custo por 1M tokens (output)** | $0.600 USD |
| **Taxa USD→BRL** | R$ 5.50 |

#### **Cálculo por Lead:**

```
Conversa típica: ~400 tokens (input)
Prompt sistema: ~150 tokens (input)
Resposta IA: ~300 tokens (output)

Total: 550 tokens input + 300 tokens output

Custo = (550 * 0.150 + 300 * 0.600) / 1,000,000 * 5.50
Custo = (82.5 + 180) / 1,000,000 * 5.50
Custo = 262.5 / 1,000,000 * 5.50
Custo = R$ 0.00144 por lead

Arredondado: ~R$ 0.002 por lead
```

#### **Cenário Real: AllpFit**

```
50 conversas/dia
30% são leads = 15 leads/dia
70% leads ficam inativos 24h+ = 10 leads elegíveis/dia

Custo diário:
- 10 análises/dia × R$ 0.002 = R$ 0.02/dia

Custo mensal:
- R$ 0.02/dia × 30 dias = R$ 0.60/mês

Re-análises (após reabertura):
- 5% reabrem após 24h = 0.5 leads/dia
- 0.5 × R$ 0.002 × 30 = R$ 0.03/mês

TOTAL: R$ 0.63/mês por tenant (MUITO BARATO!)
```

#### **Cenários de Custo Mensal (Escalabilidade):**

| Cenário | Leads Inativos/Dia | Leads/Mês | Custo/Mês |
|---------|-------------------|-----------|-----------|
| **Baixo** | 5 leads | 150 leads | R$ 0.30 |
| **Médio (AllpFit)** | 10 leads | 300 leads | R$ 0.60 |
| **Alto** | 50 leads | 1,500 leads | R$ 3.00 |
| **Muito Alto** | 200 leads | 6,000 leads | R$ 12.00 |

**Conclusão:** Custo extremamente baixo, mesmo para alto volume.

### **Performance Esperada:**

| Operação | Tempo | Notas |
|----------|-------|-------|
| **Análise individual** | 5-15s | Depende de latência OpenAI |
| **Batch 10 leads (ETL)** | 1-2 min | Sequencial (API rate limit) |
| **Batch 50 leads (manual)** | 5-8 min | Para botão "Analisar Pendentes" |
| **Dashboard carregamento** | <500ms | Dados já salvos no banco |
| **Query leads inativos 24h+** | <100ms | Índice otimizado |

---

## 📅 CRONOGRAMA DE IMPLEMENTAÇÃO

### **Fase 8.1: Foundation (Semana 1 - 2 dias)**

| # | Tarefa | Tempo | Responsável |
|---|--------|-------|-------------|
| 1 | Adicionar colunas no banco (migrations) | 1h | Isaac |
| 2 | Criar `OpenAILeadAnalyzer` (com remarketing types) | 3h | Isaac |
| 3 | Criar `TemplateManager` (3 templates remarketing) | 2h | Isaac |
| 4 | Testes unitários (analyzer + templates) | 2h | Isaac |
| 5 | Documentar API do analyzer | 1h | Isaac |

**Entregável:** Classes testadas e documentadas (9h)

---

### **Fase 8.2: ETL Integration (Semana 1-2 - 3 dias)**

| # | Tarefa | Tempo | Responsável |
|---|--------|-------|-------------|
| 1 | Implementar FASE 3.5 (reset reabertura) | 2h | Isaac |
| 2 | Implementar FASE 4 (analyze inactive leads) | 3h | Isaac |
| 3 | Adicionar controle de custo/limite | 1h | Isaac |
| 4 | Logging e estatísticas de análise | 1h | Isaac |
| 5 | Testar ETL com análise (ambiente dev) | 2h | Isaac |
| 6 | Deploy e teste em produção (1 tenant) | 2h | Isaac + Hyago |

**Entregável:** ETL funcionando com análise automática de leads inativos (11h)

---

### **Fase 8.3: Dashboard UI (Semana 2 - 2 dias)**

| # | Tarefa | Tempo | Responsável |
|---|--------|-------|-------------|
| 1 | Seção "Análise de Remarketing" (cards) | 2h | Isaac |
| 2 | Tabela com status/tipo/inatividade/score | 2h | Isaac |
| 3 | Expanders com análise completa | 2h | Isaac |
| 4 | Botão "Analisar Pendentes (24h+)" | 2h | Isaac |
| 5 | Botão "Copiar Sugestão" (clipboard) | 1h | Isaac |
| 6 | Download CSV de sugestões | 1h | Isaac |

**Entregável:** Dashboard completo e funcional (10h)

---

### **Fase 8.4: Testing & Refinement (Semana 2 - 2 dias)**

| # | Tarefa | Tempo | Responsável |
|---|--------|-------|-------------|
| 1 | Testes end-to-end (ETL + Dashboard) | 3h | Isaac |
| 2 | Ajustes de templates (feedback Hyago) | 2h | Isaac + Hyago |
| 3 | Otimização de prompts (reduzir tokens) | 2h | Isaac |
| 4 | Documentação de usuário (manual) | 2h | Hyago |
| 5 | Deploy final em todos os tenants | 1h | Isaac |

**Entregável:** Sistema em produção e documentado (10h)

---

### **Resumo do Cronograma:**

| Fase | Duração | Horas | Início | Fim |
|------|---------|-------|--------|-----|
| 8.1 Foundation | 2 dias | 9h | 14/Nov | 15/Nov |
| 8.2 ETL Integration | 3 dias | 11h | 15/Nov | 19/Nov |
| 8.3 Dashboard UI | 2 dias | 10h | 19/Nov | 21/Nov |
| 8.4 Testing | 2 dias | 10h | 21/Nov | 22/Nov |
| **TOTAL** | **9 dias úteis** | **40h** | 14/Nov | 22/Nov |

---

## ⚠️ RISCOS E MITIGAÇÕES

### **Riscos Técnicos:**

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **OpenAI API instável** | Média | Alto | Retry (3x), queue para retry offline |
| **Custo maior que estimado** | Baixa | Médio | Limite hard-coded (10 leads/ETL) + alertas |
| **Latência alta (>30s)** | Baixa | Médio | Timeout de 30s, análise assíncrona |
| **Qualidade de análise ruim** | Média | Alto | Validação humana inicial, iteração de prompts |
| **Taxa de reabertura > 5%** | Baixa | Baixo | Monitorar % de resets, ajustar 24h se necessário |

### **Riscos de Negócio:**

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **Templates genéricos demais** | Alta | Médio | Permitir customização por tenant (FASE 9) |
| **Usuários não usarem sugestões** | Média | Alto | Treinamento, medir taxa de uso, iterar |
| **24h é tempo demais (lead esfria)** | Baixa | Médio | A/B test com 12h/24h/48h, medir conversão |
| **Privacidade de dados (LGPD)** | Baixa | Alto | Anonimização em logs, OpenAI sem treino |

### **Plano de Rollback:**

```python
# Em caso de falha crítica, desabilitar análise
import os
os.environ['ANALYZE_LEADS_ENABLED'] = 'false'

# Ou via banco (se implementado config table)
UPDATE multi_tenant.system_config
SET value = 'false'
WHERE key = 'analyze_leads_enabled';
```

---

## 📚 PRÓXIMAS FASES (ROADMAP)

### **FASE 9: Customização por Tenant**
- Templates personalizados por tenant
- Tom de voz configurável
- Variáveis customizadas
- A/B testing de templates

### **FASE 10: Análise Avançada**
- Sentiment analysis (positivo/negativo/neutro)
- Predição de probabilidade de resposta
- Recomendação de melhor horário para contato
- Análise de objeções com contra-argumentos

### **FASE 11: Automação de Disparo**
- Integração com WhatsApp Business API
- Disparo automático de follow-ups
- Agendamento inteligente
- Workflow de aprovação

---

## ✅ CRITÉRIOS DE ACEITE

### **Funcional:**

- [ ] ETL analisa automaticamente leads inativos 24h+
- [ ] ETL detecta reabertura e reseta análise antiga
- [ ] Análise salva no banco com todos os campos preenchidos
- [ ] Dashboard exibe tempo de inatividade (26h, 3d, 2w)
- [ ] Dashboard mostra tipo de remarketing e score
- [ ] Botão "Analisar Pendentes (24h+)" funciona e atualiza dashboard
- [ ] Sugestão usa template correto (RECENTE/MEDIO/FRIO)
- [ ] Botão "Copiar Sugestão" copia texto para clipboard
- [ ] Download CSV de sugestões funciona

### **Performance:**

- [ ] Análise individual: < 15s
- [ ] Batch 10 leads (ETL): < 2 min
- [ ] Dashboard carrega: < 500ms
- [ ] Query leads inativos 24h+: < 100ms
- [ ] Custo por lead: < R$ 0.003

### **Qualidade:**

- [ ] Cobertura de testes: > 80%
- [ ] Taxa de erro OpenAI: < 5%
- [ ] Taxa de reabertura: < 5% (valida 24h)
- [ ] Análises com qualidade validada por Hyago
- [ ] Templates aprovados por Hyago

### **Documentação:**

- [ ] Código documentado (docstrings)
- [ ] README atualizado
- [ ] Manual de usuário criado
- [ ] Runbook de troubleshooting

---

## 📞 CONTATOS E APROVAÇÕES

| Papel | Nome | Responsabilidade | Aprovação |
|-------|------|------------------|-----------|
| **Product Owner** | Hyago | Requisitos, templates, regra 24h | ✅ **APROVADO** |
| **Tech Lead** | Isaac | Arquitetura, implementação | ✅ **APROVADO** |
| **DevOps** | Isaac | Deploy, monitoramento | ⏳ Pendente |

---

## 📝 HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 13/Nov/2025 | Isaac | Documento inicial completo |
| 2.0 | 13/Nov/2025 | Isaac + Hyago | **Versão definitiva:** Regra de 24h de inatividade aprovada. Removida lógica de status Chatwoot. Foco em remarketing (não follow-up). |

---

**FIM DO DOCUMENTO - FASE 8: Sistema de Análise Inteligente com OpenAI (v2.0 Definitiva)**

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ **Documentação aprovada** por Hyago e Isaac
2. ✅ **Regra de 24h** confirmada como gatilho
3. ⏳ **Kick-off:** Início da Fase 8.1 (Foundation) - 14/Nov
4. ⏳ **Check-ins:** Daily sync para acompanhar progresso
5. ⏳ **Deadline:** 22/Nov (9 dias úteis)

**Status:** ✅ Aprovado para início da implementação (14/Nov/2025)
