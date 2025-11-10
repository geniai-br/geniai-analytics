"""
OpenAI Analyzer - ETL V4 Multi-Tenant
======================================

Responsável por analisar conversas usando OpenAI GPT-4o-mini para detectar:
- Leads qualificados (probabilidade 0-5)
- Visitas agendadas (confirmação explícita)
- Informações estruturadas (nome, condição física, objetivo)
- Análise detalhada e sugestão de mensagem

Usa GPT-4o-mini com prompt otimizado para CrossFit/AllpFit.

Fase: 5.6 - OpenAI Integration
Autor: Isaac (via Claude Code)
Data: 2025-11-09
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
from openai import OpenAI

from .base_analyzer import BaseAnalyzer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenAIAnalyzer(BaseAnalyzer):
    """
    Analisa conversas usando OpenAI GPT-4o-mini.

    Extrai informações estruturadas e gera análises detalhadas
    para leads de academias CrossFit.
    """

    # Modelo padrão (pode ser sobrescrito por tenant config)
    DEFAULT_MODEL = 'gpt-4o-mini'

    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos

    def __init__(self, tenant_id: int, api_key: str, model: Optional[str] = None):
        """
        Inicializa o OpenAI Analyzer.

        Args:
            tenant_id: ID do tenant
            api_key: OpenAI API key
            model: Modelo a usar (default: gpt-4o-mini)

        Raises:
            ValueError: Se api_key não fornecida
        """
        super().__init__(tenant_id)

        if not api_key:
            raise ValueError(f"OpenAI API key é obrigatória para tenant {tenant_id}")

        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.client = OpenAI(api_key=self.api_key)

        # Estatísticas de uso
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'fallback_to_default': 0,
        }

        logger.info(f"OpenAIAnalyzer inicializado - Modelo: {self.model}")

    def _get_analysis_prompt(self) -> str:
        """
        Retorna o prompt otimizado para análise de conversas da AllpFit.

        Returns:
            str: System prompt para OpenAI
        """
        return """Você é um analista especializado em conversas de leads de academias de crossfit (AllpFit).

Sua tarefa é analisar a conversa completa entre o lead e a academia e extrair as seguintes informações em formato JSON:

{
  "nome_mapeado_bot": "string - nome completo do lead que o bot descobriu durante a conversa (se mencionado)",
  "condicao_fisica": "string - opções: Sedentário | Iniciante | Intermediário | Avançado | Não mencionado",
  "objetivo": "string - opções: Perda de peso | Ganho de massa muscular | Condicionamento físico | Saúde geral | Estética/Definição | Não mencionado",
  "probabilidade_conversao": "number - de 0 a 5, onde:",
  "visita_agendada": "boolean - true se houve confirmação de agendamento de visita, false caso contrário",
  "analise_ia": "string - análise detalhada com 3-5 parágrafos explicando:",
  "sugestao_disparo": "string - sugestão específica de mensagem para enviar ao lead"
}

CRITÉRIOS DE PROBABILIDADE DE CONVERSÃO (0-5):

5 - ALTÍSSIMA: Lead agendou visita OU pediu para matricular OU perguntou sobre pagamento/contrato OU confirmou que vai começar
4 - ALTA: Lead perguntou valores E horários E demonstrou interesse claro ("quero", "vou pensar", "preciso ver minha agenda")
3 - MÉDIA: Lead fez múltiplas perguntas (valor, horário, planos) mas não demonstrou urgência ou comprometimento
2 - BAIXA: Lead fez poucas perguntas genéricas ou respondeu apenas com "ok", "entendi" sem aprofundar
1 - MUITO BAIXA: Lead demonstrou objeções (caro, longe, sem tempo) ou respostas muito curtas e secas
0 - NULA: Lead não respondeu adequadamente, mandou apenas "oi" ou mensagens sem sentido, ou claramente não está interessado

ESTRUTURA DA ANÁLISE IA (analise_ia):
Parágrafo 1: Resumo do perfil do lead (condição física, objetivo, contexto pessoal mencionado)
Parágrafo 2: Nível de engajamento e sinais de interesse (perguntas feitas, tom da conversa, urgência)
Parágrafo 3: Objeções ou barreiras identificadas (se houver)
Parágrafo 4: Oportunidades e pontos fortes para abordagem
Parágrafo 5: Recomendação de estratégia de conversão

SUGESTÃO DE DISPARO (sugestao_disparo):
- Deve ser uma mensagem PERSONALIZADA baseada no perfil e interesse do lead
- Mencionar especificamente o objetivo do lead e condição física
- Incluir call-to-action claro (agendar visita, tirar dúvidas, etc)
- Usar tom humanizado e empático
- Máximo 3-4 frases

NOME MAPEADO BOT (nome_mapeado_bot):
- Extrair o NOME COMPLETO que o bot perguntou e o lead respondeu durante a conversa
- Procurar por perguntas do tipo: "Qual é o seu nome?", "Como você se chama?", "Me diz seu nome"
- O nome deve ser EXATAMENTE como o lead forneceu (primeiro e último nome se possível)
- Se o lead NÃO forneceu seu nome durante a conversa, retornar string vazia ""
- Não usar o nome do contato do sistema, apenas o que foi dito na conversa

DETECÇÃO DE VISITA AGENDADA (visita_agendada):
- Marcar TRUE se houver CONFIRMAÇÃO EXPLÍCITA de agendamento na conversa
- Palavras-chave para TRUE: "visita agendada", "agendamento confirmado", "já agendei", "te espero", "vejo você", "nos vemos"
- Marcar FALSE se o lead apenas perguntou sobre visita, mas NÃO confirmou
- Marcar FALSE se ainda está em negociação ou pensando
- A confirmação pode vir tanto do atendente quanto do próprio lead aceitando

IMPORTANTE:
- Analise TODO o histórico de mensagens, não apenas as últimas
- Considere o contexto completo da conversa
- Se não houver informação suficiente, use "Não mencionado"
- Seja preciso e objetivo na probabilidade
- A análise deve ser útil para a equipe de vendas tomar decisões

Retorne APENAS o JSON, sem texto adicional antes ou depois."""

    def analyze_conversation(
        self,
        message_text: Optional[str],
        status: Optional[str] = None,
        has_human_intervention: bool = False,
        contact_name: Optional[str] = None,
        message_count: Optional[int] = None,
        **kwargs
    ) -> Dict[str, any]:
        """
        Analisa uma única conversa usando OpenAI.

        Args:
            message_text: Texto compilado da conversa
            status: Status da conversa (não usado, mas mantido para compatibilidade)
            has_human_intervention: Se teve intervenção humana (não usado)
            contact_name: Nome do contato (para contexto)
            message_count: Número de mensagens (para contexto)
            **kwargs: Outros argumentos (ignorados)

        Returns:
            Dict com análise completa (compatível com BaseAnalyzer)
        """
        # Resultado default
        result = {
            'is_lead': False,
            'visit_scheduled': False,
            'crm_converted': False,
            'ai_probability_label': 'N/A',
            'ai_probability_score': 0.0,
            'nome_mapeado_bot': '',
            'condicao_fisica': 'Não mencionado',
            'objetivo': 'Não mencionado',
            'analise_ia': '',
            'sugestao_disparo': '',
            'probabilidade_conversao': 0,
        }

        # Validar entrada
        if not message_text or not isinstance(message_text, str):
            logger.warning(f"Texto de mensagem vazio ou inválido para tenant {self.tenant_id}")
            return result

        if len(message_text) < 10:
            logger.debug(f"Texto muito curto ({len(message_text)} chars), retornando default")
            return result

        # Preparar contexto
        contact_info = contact_name or "Lead"
        msg_count = message_count or 0

        # Chamar OpenAI com retry
        analysis = self._call_openai_with_retry(
            conversation_text=message_text,
            contact_name=contact_info,
            message_count=msg_count
        )

        if not analysis:
            logger.warning(f"Falha na análise OpenAI para tenant {self.tenant_id}, retornando default")
            self.stats['failed_calls'] += 1
            return result

        # Processar resposta OpenAI
        result = self._process_openai_response(analysis)
        self.stats['successful_calls'] += 1

        return result

    def _call_openai_with_retry(
        self,
        conversation_text: str,
        contact_name: str,
        message_count: int
    ) -> Optional[Dict]:
        """
        Chama OpenAI com retry automático.

        Args:
            conversation_text: Texto da conversa
            contact_name: Nome do contato
            message_count: Número de mensagens

        Returns:
            Dict com análise ou None em caso de erro
        """
        user_message = f"""NOME DO LEAD: {contact_name}
TOTAL DE MENSAGENS DO LEAD: {message_count}

CONVERSA COMPLETA:
{conversation_text}

Analise esta conversa e retorne o JSON com as informações solicitadas."""

        for attempt in range(self.MAX_RETRIES):
            try:
                self.stats['total_calls'] += 1

                # Chamar OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_analysis_prompt()},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3,  # Baixa temperatura para consistência
                    max_tokens=1500,
                    response_format={"type": "json_object"}  # Força JSON
                )

                # Extrair resposta
                content = response.choices[0].message.content
                analysis = json.loads(content)

                # Rastrear tokens
                if hasattr(response, 'usage'):
                    self.stats['total_tokens'] += response.usage.total_tokens

                logger.debug(f"OpenAI API call sucesso (tentativa {attempt + 1}/{self.MAX_RETRIES})")
                return analysis

            except json.JSONDecodeError as e:
                logger.warning(f"Erro JSON (tentativa {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                continue

            except Exception as e:
                logger.error(f"Erro OpenAI (tentativa {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                continue

        logger.error(f"Falha após {self.MAX_RETRIES} tentativas para tenant {self.tenant_id}")
        return None

    def _process_openai_response(self, analysis: Dict) -> Dict:
        """
        Processa resposta da OpenAI e converte para formato padrão.

        Args:
            analysis: Dict retornado pela OpenAI

        Returns:
            Dict no formato padrão (compatível com BaseAnalyzer)
        """
        # Extrair campos
        prob_openai = analysis.get('probabilidade_conversao', 0)
        visit_scheduled = analysis.get('visita_agendada', False)

        # Validar probabilidade (0-5)
        if not isinstance(prob_openai, (int, float)) or prob_openai < 0 or prob_openai > 5:
            logger.warning(f"Probabilidade inválida: {prob_openai}, usando 0")
            prob_openai = 0
        else:
            prob_openai = int(prob_openai)

        # Converter probabilidade OpenAI (0-5) para score (0-100)
        score = self._openai_probability_to_score(prob_openai)

        # Determinar is_lead (probabilidade >= 2 = lead)
        is_lead = (prob_openai >= 2)

        # Determinar CRM converted (probabilidade == 5 geralmente indica conversão)
        crm_converted = (prob_openai == 5)

        # Montar resultado
        result = {
            # Campos padrão (BaseAnalyzer)
            'is_lead': is_lead,
            'visit_scheduled': bool(visit_scheduled),
            'crm_converted': crm_converted,
            'ai_probability_label': self._score_to_label(score),
            'ai_probability_score': score,

            # Campos específicos OpenAI
            'nome_mapeado_bot': analysis.get('nome_mapeado_bot', ''),
            'condicao_fisica': analysis.get('condicao_fisica', 'Não mencionado'),
            'objetivo': analysis.get('objetivo', 'Não mencionado'),
            'analise_ia': analysis.get('analise_ia', ''),
            'sugestao_disparo': analysis.get('sugestao_disparo', ''),
            'probabilidade_conversao': prob_openai,
        }

        logger.debug(f"Conversa processada: is_lead={is_lead}, prob={prob_openai}, score={score}")

        return result

    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa um DataFrame completo de conversas.

        Args:
            df: DataFrame com colunas:
                - message_compiled (texto das mensagens)
                - contact_name (opcional)
                - contact_messages_count (opcional)

        Returns:
            DataFrame com colunas de análise adicionadas
        """
        if df.empty:
            logger.warning("DataFrame vazio recebido para análise")
            return df

        logger.info(f"Analisando {len(df)} conversas com OpenAI para tenant {self.tenant_id}")
        start_time = time.time()

        # Aplicar análise linha por linha
        results = df.apply(
            lambda row: self.analyze_conversation(
                message_text=row.get('message_compiled', None),
                contact_name=row.get('contact_name', None),
                message_count=row.get('contact_messages_count', 0),
            ),
            axis=1
        )

        # Extrair campos
        df['is_lead'] = results.apply(lambda x: x['is_lead'])
        df['visit_scheduled'] = results.apply(lambda x: x['visit_scheduled'])
        df['crm_converted'] = results.apply(lambda x: x['crm_converted'])
        df['ai_probability_label'] = results.apply(lambda x: x['ai_probability_label'])
        df['ai_probability_score'] = results.apply(lambda x: x['ai_probability_score'])

        # Campos adicionais OpenAI
        df['nome_mapeado_bot'] = results.apply(lambda x: x.get('nome_mapeado_bot', ''))
        df['condicao_fisica'] = results.apply(lambda x: x.get('condicao_fisica', 'Não mencionado'))
        df['objetivo'] = results.apply(lambda x: x.get('objetivo', 'Não mencionado'))
        df['analise_ia'] = results.apply(lambda x: x.get('analise_ia', ''))
        df['sugestao_disparo'] = results.apply(lambda x: x.get('sugestao_disparo', ''))
        df['probabilidade_conversao'] = results.apply(lambda x: x.get('probabilidade_conversao', 0))

        # Estatísticas
        lead_count = df['is_lead'].sum()
        visit_count = df['visit_scheduled'].sum()
        conversion_count = df['crm_converted'].sum()

        elapsed = time.time() - start_time
        avg_time = elapsed / len(df) if len(df) > 0 else 0

        logger.info(f"Análise OpenAI concluída: {lead_count} leads, "
                   f"{visit_count} visitas, {conversion_count} conversões")
        logger.info(f"Tempo total: {elapsed:.2f}s, Média: {avg_time:.2f}s/conversa")
        logger.info(f"API calls: {self.stats['successful_calls']} sucesso, "
                   f"{self.stats['failed_calls']} falhas, "
                   f"{self.stats['total_tokens']} tokens")

        return df

    def get_usage_stats(self) -> Dict:
        """
        Retorna estatísticas de uso da API.

        Returns:
            Dict com estatísticas
        """
        return {
            **self.stats,
            'tenant_id': self.tenant_id,
            'model': self.model,
            'success_rate': round(
                (self.stats['successful_calls'] / self.stats['total_calls'] * 100)
                if self.stats['total_calls'] > 0 else 0,
                2
            )
        }


# ============================================================================
# FUNÇÃO HELPER PARA USAR NO TRANSFORMER
# ============================================================================

def add_openai_analysis(
    df: pd.DataFrame,
    tenant_id: int,
    api_key: str,
    model: Optional[str] = None
) -> pd.DataFrame:
    """
    Função helper para adicionar análise OpenAI ao DataFrame.

    Uso no transformer:
        df = add_openai_analysis(df, tenant_id=1, api_key="sk-...")

    Args:
        df: DataFrame de conversas
        tenant_id: ID do tenant
        api_key: OpenAI API key
        model: Modelo a usar (opcional, default: gpt-4o-mini)

    Returns:
        DataFrame com colunas de análise adicionadas
    """
    analyzer = OpenAIAnalyzer(tenant_id=tenant_id, api_key=api_key, model=model)
    df_analyzed = analyzer.analyze_dataframe(df)

    # Mostrar estatísticas
    stats = analyzer.get_statistics(df_analyzed)
    usage_stats = analyzer.get_usage_stats()

    logger.info(f"Estatísticas tenant {tenant_id}: {stats}")
    logger.info(f"Uso OpenAI: {usage_stats}")

    return df_analyzed
