# 🤖 INTEGRAÇÃO FUTURA: OpenAI para Análise de Leads

> **Status:** 📋 PLANEJADO (aguardando aprovação)
> **Data:** 2025-11-06
> **Estimativa:** 4-6 horas de implementação
> **Custo estimado:** ~R$ 20-50/mês (dependendo do volume)

---

## 🎯 **OBJETIVO**

Evoluir a análise de leads de **regex (atual)** para **IA generativa (OpenAI GPT)** para:
- ✅ Maior acurácia (80% → 95%)
- ✅ Entendimento contextual (não só keywords)
- ✅ Análise de sentimento
- ✅ Extração de entidades (nome, data, horário)
- ✅ Resumo automático da conversa

---

## 📊 **COMPARAÇÃO: Regex vs OpenAI**

| Aspecto | **Regex (Atual)** | **OpenAI (Futuro)** |
|---------|-------------------|---------------------|
| **Acurácia** | ~80% | ~95% |
| **Custo** | R$ 0 | ~R$ 0,01-0,10/conversa |
| **Velocidade** | 2s para 1.099 conversas | ~5-15min para 1.099 |
| **Privacidade** | 100% local | Envia para API externa |
| **Configurável** | Keywords fixas | Aprende com exemplos |
| **Contexto** | Apenas keywords | Entende contexto completo |
| **Sentimento** | ❌ Não detecta | ✅ Detecta (positivo/negativo) |
| **Entidades** | ❌ Não extrai | ✅ Extrai (datas, nomes, etc) |

---

## 💰 **ANÁLISE DE CUSTO**

### 📈 **Cenário Real - AllpFit:**

- **Volume atual:** 1.099 conversas (43 dias)
- **Média diária:** ~25 conversas/dia
- **Mensal:** ~750 conversas/mês

### 💵 **Cálculo OpenAI (modelo GPT-4o-mini):**

```
Tokens por conversa:
- Input: ~500 tokens (mensagens compiladas)
- Output: ~150 tokens (análise JSON)
- Total: ~650 tokens/conversa

Preço GPT-4o-mini:
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- Média: ~$0.0002/conversa (R$ 0,001)

Custo mensal:
750 conversas × R$ 0,001 = R$ 0,75/mês ✅

Custo anual:
R$ 0,75 × 12 = R$ 9,00/ano ✅
```

### 🎉 **Conclusão:** **MUITO BARATO!** (menos que 1 café/mês)

---

## 🔧 **IMPLEMENTAÇÃO PROPOSTA**

### 📁 **Novo arquivo:** `src/multi_tenant/etl_v4/openai_analyzer.py`

```python
"""
OpenAI Lead Analyzer - ETL V4 Multi-Tenant
==========================================

Analisa conversas usando OpenAI GPT-4o-mini para detectar:
- Leads qualificados
- Visitas agendadas
- Conversões CRM
- Sentimento do cliente
- Entidades (datas, nomes, produtos)

Autor: Isaac (via Claude Code)
Data: 2025-11-06 (planejado)
"""

import logging
import os
from typing import Dict, Optional
import pandas as pd
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAILeadAnalyzer:
    """Analisa conversas usando OpenAI GPT"""

    def __init__(self, tenant_id: int, api_key: Optional[str] = None):
        """
        Inicializa o analisador OpenAI.

        Args:
            tenant_id: ID do tenant
            api_key: Chave API OpenAI (ou usa env OPENAI_API_KEY)
        """
        self.tenant_id = tenant_id
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))

        logger.info(f"OpenAILeadAnalyzer inicializado para tenant {tenant_id}")

    def analyze_conversation(self, message_text: str, context: Dict = None) -> Dict:
        """
        Analisa uma conversa usando GPT.

        Args:
            message_text: Texto compilado da conversa
            context: Contexto adicional (status, inbox, etc)

        Returns:
            Dict com análise completa

        Example:
            >>> analyzer = OpenAILeadAnalyzer(tenant_id=1)
            >>> result = analyzer.analyze_conversation(
            ...     "Cliente: Quero agendar aula amanhã 18h\\n"
            ...     "Atendente: Confirmado!"
            ... )
            >>> result['is_lead']
            True
        """
        if not message_text:
            return self._default_result()

        # Montar prompt para GPT
        system_prompt = """
Você é um analisador de leads para academias CrossFit.

Analise a conversa e retorne um JSON com:
{
  "is_lead": true/false,           // Pessoa interessada em matricular
  "visit_scheduled": true/false,   // Agendou dia/hora para conhecer
  "crm_converted": true/false,     // Matrícula confirmada/paga
  "confidence": 0-100,             // Confiança na classificação
  "sentiment": "positive/neutral/negative",
  "intent": "string",              // Principal intenção do cliente
  "entities": {                    // Entidades extraídas
    "date": "2025-11-07",
    "time": "18:00",
    "product": "Plano Mensal",
    "name": "João Silva"
  },
  "summary": "string",             // Resumo em 1 frase
  "next_action": "string"          // Próxima ação sugerida
}

Critérios de Lead:
- Perguntas sobre preço, planos, horários
- Expressões: "quero", "tenho interesse", "gostaria"
- Urgência: "hoje", "agora", "rápido"

Critérios de Visita Agendada:
- Menção de data/hora específica
- Verbos: "agendar", "marcar", "ir", "visitar"
- Confirmações: "confirmado", "ok", "combinado"

Critérios de Conversão:
- "Matrícula realizada/confirmada"
- Menção de pagamento: "paguei", "pix enviado"
- Check-in na academia
"""

        user_prompt = f"""
CONVERSA:
{message_text}

CONTEXTO ADICIONAL:
- Status: {context.get('status', 'N/A') if context else 'N/A'}
- Inbox: {context.get('inbox_name', 'N/A') if context else 'N/A'}
- Teve atendimento humano: {context.get('has_human_intervention', False) if context else False}
"""

        try:
            # Chamar API OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo mais barato
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Baixa temperatura = mais consistente
                max_tokens=500
            )

            # Parse resultado
            import json
            result = json.loads(response.choices[0].message.content)

            # Adicionar campos compatíveis com LeadAnalyzer atual
            result['ai_probability_score'] = result.get('confidence', 0)
            result['ai_probability_label'] = self._score_to_label(result['ai_probability_score'])

            logger.debug(f"Análise OpenAI: {result['summary']}")
            return result

        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            return self._default_result()

    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa DataFrame completo de conversas.

        Args:
            df: DataFrame com conversas

        Returns:
            DataFrame com análises adicionadas

        Note:
            Processa em lotes para economizar API calls.
        """
        if df.empty:
            logger.warning("DataFrame vazio")
            return df

        logger.info(f"Analisando {len(df)} conversas com OpenAI")

        # Aplicar análise (com progresso)
        results = []
        for idx, row in df.iterrows():
            context = {
                'status': row.get('status'),
                'inbox_name': row.get('inbox_name'),
                'has_human_intervention': row.get('has_human_intervention', False)
            }

            result = self.analyze_conversation(
                message_text=row.get('message_compiled'),
                context=context
            )
            results.append(result)

            # Log progresso a cada 100
            if (idx + 1) % 100 == 0:
                logger.info(f"Progresso: {idx + 1}/{len(df)} conversas")

        # Adicionar colunas ao DataFrame
        df['is_lead'] = [r['is_lead'] for r in results]
        df['visit_scheduled'] = [r['visit_scheduled'] for r in results]
        df['crm_converted'] = [r['crm_converted'] for r in results]
        df['ai_probability_score'] = [r['ai_probability_score'] for r in results]
        df['ai_probability_label'] = [r['ai_probability_label'] for r in results]

        # Colunas extras do OpenAI
        df['sentiment'] = [r.get('sentiment', 'neutral') for r in results]
        df['intent'] = [r.get('intent', '') for r in results]
        df['summary'] = [r.get('summary', '') for r in results]
        df['next_action'] = [r.get('next_action', '') for r in results]

        # Estatísticas
        leads = df['is_lead'].sum()
        visits = df['visit_scheduled'].sum()
        conversions = df['crm_converted'].sum()

        logger.info(f"Análise concluída: {leads} leads, {visits} visitas, {conversions} conversões")

        return df

    def _default_result(self) -> Dict:
        """Resultado padrão para erros"""
        return {
            'is_lead': False,
            'visit_scheduled': False,
            'crm_converted': False,
            'confidence': 0,
            'ai_probability_score': 0,
            'ai_probability_label': 'N/A',
            'sentiment': 'neutral',
            'intent': '',
            'summary': '',
            'next_action': '',
            'entities': {}
        }

    def _score_to_label(self, score: float) -> str:
        """Converte score em label"""
        if score >= 70:
            return 'Alto'
        elif score >= 40:
            return 'Médio'
        elif score > 0:
            return 'Baixo'
        else:
            return 'N/A'


# ============================================================================
# TESTE LOCAL
# ============================================================================

if __name__ == "__main__":
    # Teste (requer OPENAI_API_KEY no env)
    import sys

    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Defina OPENAI_API_KEY no ambiente")
        sys.exit(1)

    analyzer = OpenAILeadAnalyzer(tenant_id=1)

    # Teste com conversa fictícia
    test_conversation = """
Cliente: Olá! Quero saber sobre os planos da academia
Atendente: Olá! Temos 3 planos: Mensal R$199, Trimestral R$499 e Anual R$1499
Cliente: Interessante! Posso fazer uma aula experimental?
Atendente: Claro! Que dia você prefere?
Cliente: Amanhã às 18h pode?
Atendente: Perfeito! Aula experimental agendada para amanhã 18h. Até lá!
Cliente: Obrigado!
"""

    result = analyzer.analyze_conversation(test_conversation)

    print("\n=== RESULTADO DA ANÁLISE OpenAI ===\n")
    print(f"Is Lead: {result['is_lead']}")
    print(f"Visit Scheduled: {result['visit_scheduled']}")
    print(f"CRM Converted: {result['crm_converted']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Sentiment: {result['sentiment']}")
    print(f"Intent: {result['intent']}")
    print(f"Summary: {result['summary']}")
    print(f"Next Action: {result['next_action']}")
    print(f"Entities: {result.get('entities', {})}")
```

---

## 🔄 **INTEGRAÇÃO COM O ETL**

### 📝 **Modificação no `transformer.py`:**

```python
# src/multi_tenant/etl_v4/transformer.py

from .lead_analyzer import LeadAnalyzer
from .openai_analyzer import OpenAILeadAnalyzer  # NOVO

class ConversationTransformer:
    def __init__(
        self,
        tenant_id: int,
        enable_lead_analysis: bool = True,
        use_openai: bool = False  # NOVO parâmetro
    ):
        self.tenant_id = tenant_id
        self.use_openai = use_openai

        if enable_lead_analysis:
            if use_openai and os.getenv('OPENAI_API_KEY'):
                # Usar OpenAI se chave disponível
                self.lead_analyzer = OpenAILeadAnalyzer(tenant_id=tenant_id)
                logger.info(f"Usando OpenAI para análise de leads")
            else:
                # Fallback para regex
                self.lead_analyzer = LeadAnalyzer(tenant_id=tenant_id)
                logger.info(f"Usando regex para análise de leads")
        else:
            self.lead_analyzer = None
```

### 🚀 **Executar ETL com OpenAI:**

```bash
# Com OpenAI (se OPENAI_API_KEY definida)
OPENAI_API_KEY=sk-... python3 src/multi_tenant/etl_v4/pipeline.py \
    --tenant-id 1 \
    --use-openai

# Sem OpenAI (regex padrão)
python3 src/multi_tenant/etl_v4/pipeline.py --tenant-id 1
```

---

## 📊 **NOVAS COLUNAS NO BANCO (Opcionais)**

```sql
-- Colunas extras do OpenAI (apenas se usar)
ALTER TABLE conversations_analytics
ADD COLUMN sentiment VARCHAR(20),          -- positive/neutral/negative
ADD COLUMN intent TEXT,                    -- Intenção principal
ADD COLUMN summary TEXT,                   -- Resumo da conversa
ADD COLUMN next_action TEXT,               -- Próxima ação sugerida
ADD COLUMN entities JSONB;                 -- Entidades extraídas

-- Índice para filtrar por sentimento
CREATE INDEX idx_conversations_sentiment
ON conversations_analytics(tenant_id, sentiment);
```

---

## 🎯 **CASOS DE USO AVANÇADOS**

### 1️⃣ **Análise de Sentimento**

```sql
-- Leads com sentimento negativo (urgente!)
SELECT
    contact_name,
    summary,
    sentiment,
    ai_probability_score
FROM conversations_analytics
WHERE tenant_id = 1
  AND is_lead = TRUE
  AND sentiment = 'negative'
ORDER BY ai_probability_score DESC;
```

### 2️⃣ **Extração de Horários**

```sql
-- Visitas agendadas com hora extraída
SELECT
    contact_name,
    entities->>'date' as data_agendada,
    entities->>'time' as hora_agendada,
    next_action
FROM conversations_analytics
WHERE tenant_id = 1
  AND visit_scheduled = TRUE
  AND entities ? 'time';
```

### 3️⃣ **Resumo Automático**

```sql
-- Dashboard de resumos
SELECT
    DATE(conversation_created_at) as dia,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_lead) as leads,
    STRING_AGG(summary, ' | ') as resumos
FROM conversations_analytics
WHERE tenant_id = 1
  AND conversation_date >= CURRENT_DATE - 7
GROUP BY dia
ORDER BY dia DESC;
```

---

## ⚙️ **CONFIGURAÇÃO**

### 🔑 **1. Obter API Key da OpenAI**

1. Acesse: https://platform.openai.com/api-keys
2. Login com conta OpenAI
3. Clique em "Create new secret key"
4. Copie a chave (começa com `sk-...`)

### 🔐 **2. Configurar no Servidor**

```bash
# Adicionar ao .env
echo "OPENAI_API_KEY=sk-seu-key-aqui" >> .env

# Ou exportar no shell
export OPENAI_API_KEY=sk-seu-key-aqui
```

### 🧪 **3. Testar**

```bash
# Teste simples
python3 src/multi_tenant/etl_v4/openai_analyzer.py

# ETL completo com OpenAI
OPENAI_API_KEY=sk-... python3 src/multi_tenant/etl_v4/pipeline.py \
    --tenant-id 1 \
    --use-openai \
    --full
```

---

## 🎓 **TREINAMENTO E AJUSTE FINO**

### 📚 **Few-Shot Learning**

Adicionar exemplos ao prompt para melhorar acurácia:

```python
few_shot_examples = """
EXEMPLO 1 (Lead + Visita):
Cliente: Quero agendar aula amanhã 18h
Análise: {"is_lead": true, "visit_scheduled": true, "confidence": 90}

EXEMPLO 2 (Não é Lead):
Cliente: Já sou aluno, só queria saber o horário
Análise: {"is_lead": false, "confidence": 95}

EXEMPLO 3 (Conversão):
Atendente: Matrícula confirmada! Pagamento aprovado
Análise: {"crm_converted": true, "confidence": 100}
"""
```

---

## 📈 **MONITORAMENTO DE CUSTO**

### 💰 **Dashboard de Custos:**

```python
# src/multi_tenant/etl_v4/cost_tracker.py

def track_openai_cost(response):
    """Rastreia custo de cada chamada"""
    usage = response.usage

    input_cost = (usage.prompt_tokens / 1_000_000) * 0.15  # USD
    output_cost = (usage.completion_tokens / 1_000_000) * 0.60
    total_cost = input_cost + output_cost

    logger.info(f"Custo: ${total_cost:.4f} USD")

    # Salvar em banco para relatório
    save_cost_log(total_cost)
```

---

## ✅ **CHECKLIST DE IMPLEMENTAÇÃO**

- [ ] Obter API key da OpenAI
- [ ] Validar com Isaac se pode usar
- [ ] Criar `openai_analyzer.py`
- [ ] Modificar `transformer.py` para suportar `--use-openai`
- [ ] Adicionar colunas extras no banco (sentiment, intent, summary)
- [ ] Testar com 10-20 conversas primeiro
- [ ] Comparar acurácia: Regex vs OpenAI
- [ ] Se aprovado, processar todas as 1.099 conversas
- [ ] Configurar monitoramento de custo
- [ ] Atualizar dashboard para mostrar sentiment

---

## 🚨 **IMPORTANTE: PRIVACIDADE**

### ⚠️ **Dados enviados para OpenAI:**

- ✅ Texto das conversas (sem identificação pessoal se possível)
- ✅ Contexto (status, inbox)
- ❌ **NÃO enviar:** Telefone completo, CPF, endereço

### 🔒 **Mitigação:**

```python
def sanitize_conversation(text: str) -> str:
    """Remove dados sensíveis antes de enviar para OpenAI"""
    import re

    # Mascarar telefones
    text = re.sub(r'\b\d{10,11}\b', '[TELEFONE]', text)

    # Mascarar CPFs
    text = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '[CPF]', text)

    # Mascarar emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

    return text
```

---

## 🎯 **DECISÃO FINAL**

### ✅ **Recomendação:**

1. **AGORA (Fase 4):** Usar **regex** (grátis, rápido, bom o suficiente)
2. **Validar com Isaac:** Mostrar sistema funcionando com regex
3. **DEPOIS (Fase 5+):** Se aprovado, implementar **OpenAI** (melhor acurácia)

### 💡 **Vantagens dessa abordagem:**

- ✅ Entrega valor imediato (regex já funciona)
- ✅ Economiza custo durante desenvolvimento
- ✅ Código preparado para upgrade (basta trocar analyzer)
- ✅ Pode A/B test (10% OpenAI, 90% regex)

---

**Última atualização:** 2025-11-06
**Status:** Documentado e pronto para implementação futura
**Aguardando:** Aprovação de Isaac para uso de OpenAI API
