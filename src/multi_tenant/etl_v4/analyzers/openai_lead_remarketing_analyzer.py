"""
OpenAI Lead Remarketing Analyzer - ETL V4 Multi-Tenant
=======================================================

Responsável por analisar LEADS INATIVOS (24h+) usando OpenAI GPT-4o-mini para:
- Classificar tipo de remarketing (RECENTE, MEDIO, FRIO) baseado em tempo de inatividade
- Extrair dados estruturados (objetivo, objeções, urgência, interesse)
- Gerar análise contextual detalhada
- Criar sugestão de mensagem de remarketing personalizada
- Calcular score de prioridade (0-5)

REGRA DE NEGÓCIO CHAVE (Hyago - Product Owner):
"A análise deve acontecer quando a última mensagem da conversa tenha passado de
mais de 24 horas. Isso marca a transição da janela de follow-up para a janela
de remarketing."

Fase: 8.1 - Foundation (Sistema de Análise Inteligente)
Relacionado: docs/private/checkpoints/FASE8_ANALISE_OPENAI.md
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from decimal import Decimal

from openai import OpenAI
from openai.types.chat import ChatCompletion

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenAILeadRemarketingAnalyzer:
    """
    Analisa leads inativos (24h+) usando OpenAI GPT-4o-mini para gerar
    análises de remarketing personalizadas.

    Tipos de Remarketing (baseado em tempo de inatividade):
    - REMARKETING_RECENTE: 24-48h (tom casual, lembrete suave)
    - REMARKETING_MEDIO: 48h-7d (tom profissional, reengajamento)
    - REMARKETING_FRIO: 7+ dias (tom formal, resgate)
    """

    # Modelo padrão OpenAI
    DEFAULT_MODEL = 'gpt-4o-mini-2024-07-18'

    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos

    # Timeout por análise
    TIMEOUT_SECONDS = 30

    # Custos OpenAI (atualizado Nov/2024)
    # GPT-4o-mini pricing (USD por 1M tokens)
    COST_INPUT_PER_1M = 0.150  # USD
    COST_OUTPUT_PER_1M = 0.600  # USD
    USD_TO_BRL = 5.50  # Taxa de câmbio aproximada

    def __init__(
        self,
        tenant_id: int,
        api_key: str,
        model: Optional[str] = None,
        template_manager: Optional[Any] = None
    ):
        """
        Inicializa o OpenAI Lead Remarketing Analyzer.

        Args:
            tenant_id: ID do tenant
            api_key: OpenAI API key
            model: Modelo a usar (default: gpt-4o-mini-2024-07-18)
            template_manager: Instância do TemplateManager (será criada se None)

        Raises:
            ValueError: Se api_key não fornecida
        """
        if not api_key:
            raise ValueError(f"OpenAI API key é obrigatória para tenant {tenant_id}")

        self.tenant_id = tenant_id
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.client = OpenAI(api_key=self.api_key)

        # TemplateManager será injetado ou criado
        if template_manager is None:
            from ..utils.template_manager import TemplateManager
            self.template_manager = TemplateManager(tenant_id=tenant_id)
        else:
            self.template_manager = template_manager

        # Estatísticas de uso
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_cost_brl': 0.0,
        }

        logger.info(
            f"OpenAILeadRemarketingAnalyzer inicializado - "
            f"Tenant: {tenant_id} | Modelo: {self.model}"
        )

    def get_remarketing_type(self, tempo_inativo_horas: float) -> str:
        """
        Classifica tipo de remarketing baseado em tempo de inatividade.

        Regra de Negócio (Hyago):
        - 24-48h: RECENTE (lead ainda "morno", tom casual)
        - 48h-7d: MEDIO (lead esfriando, oferta direta)
        - 7d+: FRIO (lead frio, resgate agressivo)

        Args:
            tempo_inativo_horas: Horas desde última mensagem

        Returns:
            Tipo de remarketing (REMARKETING_RECENTE, MEDIO, FRIO)
        """
        if 24 <= tempo_inativo_horas < 48:
            return 'REMARKETING_RECENTE'
        elif 48 <= tempo_inativo_horas < 168:  # 7 dias
            return 'REMARKETING_MEDIO'
        else:  # 7+ dias
            return 'REMARKETING_FRIO'

    def _build_system_prompt(self, tipo_remarketing: str) -> str:
        """
        Constrói prompt de sistema otimizado para análise de remarketing.

        Args:
            tipo_remarketing: Tipo de remarketing (RECENTE, MEDIO, FRIO)

        Returns:
            System prompt formatado
        """
        tipo_descricao = {
            'REMARKETING_RECENTE': 'Lead inativo há 24-48h (tom casual, lembrete suave)',
            'REMARKETING_MEDIO': 'Lead inativo há 48h-7d (tom profissional, reengajamento)',
            'REMARKETING_FRIO': 'Lead inativo há 7+ dias (tom formal, resgate)',
        }

        return f"""Você é um analista especializado em leads inativos de academias/serviços.

Tipo de Análise: {tipo_descricao.get(tipo_remarketing, 'Indefinido')}

Sua tarefa é analisar a conversa completa entre o lead e a empresa e extrair informações estruturadas em formato JSON:

{{
  "objetivo": "string - objetivo/interesse principal mencionado (ex: 'Perda de peso', 'CrossFit', 'Consulta nutricional')",
  "condicao_fisica": "string - se mencionado (ex: 'Sedentário', 'Iniciante', 'Avançado') ou 'Não mencionado'",
  "objecoes": ["lista de objeções identificadas (ex: 'Preço alto', 'Distância', 'Falta de tempo')"],
  "urgencia": "string - urgência percebida: 'Alta' | 'Média' | 'Baixa'",
  "interesse_especifico": "string - interesse específico extraído (ex: 'Aulas de CrossFit', 'Personal trainer')",
  "contexto_adicional": "string - qualquer informação relevante (horários mencionados, preferências, etc.)",
  "score_prioridade": "number - de 0 a 5, onde:
    5 = Lead quente com urgência alta e objeções baixas
    4 = Lead interessado com objeções moderadas
    3 = Lead neutro
    2 = Lead com objeções fortes ou urgência baixa
    1 = Lead pouco engajado
    0 = Lead sem potencial aparente",
  "analise_contextual": "string - análise detalhada do contexto da conversa e perfil do lead (2-3 frases)"
}}

INSTRUÇÕES IMPORTANTES:
1. Seja GENÉRICO e NÃO mencione promoções/ofertas específicas que você não controla
2. Foque em INFORMAÇÕES e SUPORTE, não em vendas agressivas
3. Extraia apenas dados EXPLICITAMENTE mencionados na conversa
4. Se algo não foi mencionado, use "Não mencionado" ou lista vazia
5. A análise deve ser objetiva e baseada em fatos da conversa
6. O score deve refletir potencial real de conversão baseado na conversa

RETORNE APENAS O JSON, sem texto adicional."""

    def _build_user_prompt(
        self,
        conversa_compilada: Dict[str, Any],
        contact_name: str,
        inbox_name: str,
        tempo_inativo_horas: float
    ) -> str:
        """
        Constrói prompt do usuário com dados da conversa.

        Args:
            conversa_compilada: Conversa em formato JSONB
            contact_name: Nome do contato
            inbox_name: Nome do inbox
            tempo_inativo_horas: Horas de inatividade

        Returns:
            User prompt formatado
        """
        # Extrair mensagens da conversa compilada
        mensagens = conversa_compilada.get('messages', [])

        # Formatar mensagens para contexto
        mensagens_formatadas = []
        for msg in mensagens:
            sender = msg.get('sender_type', 'Desconhecido')
            content = msg.get('content', '')
            timestamp = msg.get('created_at', '')

            # Limitar tamanho da mensagem (evitar prompt muito grande)
            if len(content) > 500:
                content = content[:500] + '...'

            mensagens_formatadas.append(f"[{sender}] {content}")

        conversa_texto = "\n".join(mensagens_formatadas[:20])  # Limitar a 20 mensagens

        return f"""
DADOS DO LEAD:
- Nome: {contact_name or 'Não identificado'}
- Canal: {inbox_name or 'Desconhecido'}
- Tempo Inativo: {tempo_inativo_horas:.1f} horas (~{int(tempo_inativo_horas/24)} dias)

CONVERSA COMPLETA:
{conversa_texto}

ANALISE A CONVERSA E RETORNE O JSON COM OS DADOS ESTRUTURADOS.
"""

    def _calculate_cost(self, tokens_input: int, tokens_output: int) -> float:
        """
        Calcula custo da análise em BRL.

        Args:
            tokens_input: Tokens de entrada
            tokens_output: Tokens de saída

        Returns:
            Custo em BRL
        """
        cost_input_usd = (tokens_input / 1_000_000) * self.COST_INPUT_PER_1M
        cost_output_usd = (tokens_output / 1_000_000) * self.COST_OUTPUT_PER_1M
        cost_total_usd = cost_input_usd + cost_output_usd
        cost_brl = cost_total_usd * self.USD_TO_BRL
        return round(cost_brl, 6)

    def analyze_lead(
        self,
        conversation_id: int,
        conversa_compilada: Dict[str, Any],
        contact_name: str,
        inbox_name: str,
        tipo_remarketing: str,
        tempo_inativo_horas: float
    ) -> Dict[str, Any]:
        """
        Analisa um lead inativo usando OpenAI.

        Args:
            conversation_id: ID da conversa
            conversa_compilada: Conversa em formato JSONB
            contact_name: Nome do contato
            inbox_name: Nome do inbox
            tipo_remarketing: Tipo de remarketing (RECENTE, MEDIO, FRIO)
            tempo_inativo_horas: Horas de inatividade

        Returns:
            Dict com resultado da análise completa

        Raises:
            Exception: Se falha após MAX_RETRIES tentativas
        """
        logger.info(
            f"Analisando lead {conversation_id} - "
            f"Tipo: {tipo_remarketing} | Inativo: {tempo_inativo_horas:.1f}h"
        )

        # Construir prompts
        system_prompt = self._build_system_prompt(tipo_remarketing)
        user_prompt = self._build_user_prompt(
            conversa_compilada, contact_name, inbox_name, tempo_inativo_horas
        )

        # Retry loop
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                start_time = time.time()

                # Chamar OpenAI API
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,  # Baixa temperatura para consistência
                    max_tokens=800,  # Suficiente para análise + JSON
                    timeout=self.TIMEOUT_SECONDS
                )

                elapsed_time = time.time() - start_time

                # Extrair resposta
                content = response.choices[0].message.content.strip()

                # Parsear JSON
                try:
                    dados_extraidos = json.loads(content)
                except json.JSONDecodeError:
                    # Tentar extrair JSON de markdown code block
                    if '```json' in content:
                        json_start = content.find('```json') + 7
                        json_end = content.find('```', json_start)
                        content = content[json_start:json_end].strip()
                        dados_extraidos = json.loads(content)
                    else:
                        raise

                # Validar estrutura mínima
                required_fields = ['objetivo', 'score_prioridade', 'analise_contextual']
                for field in required_fields:
                    if field not in dados_extraidos:
                        raise ValueError(f"Campo obrigatório ausente: {field}")

                # Extrair score de prioridade
                score_prioridade = int(dados_extraidos.get('score_prioridade', 0))
                if not (0 <= score_prioridade <= 5):
                    score_prioridade = max(0, min(5, score_prioridade))

                # Gerar sugestão de remarketing usando template
                sugestao_disparo = self.template_manager.generate_remarketing_message(
                    tipo_remarketing=tipo_remarketing,
                    dados_extraidos=dados_extraidos,
                    contact_name=contact_name,
                    inbox_name=inbox_name,
                    tempo_inativo_horas=tempo_inativo_horas
                )

                # Calcular custo
                tokens_input = response.usage.prompt_tokens
                tokens_output = response.usage.completion_tokens
                tokens_total = response.usage.total_tokens
                custo_brl = self._calculate_cost(tokens_input, tokens_output)

                # Atualizar estatísticas
                self.stats['total_calls'] += 1
                self.stats['successful_calls'] += 1
                self.stats['total_tokens'] += tokens_total
                self.stats['total_cost_brl'] += custo_brl

                # Montar resultado
                resultado = {
                    'tipo_conversa': tipo_remarketing,
                    'analise_ia': dados_extraidos.get('analise_contextual', ''),
                    'sugestao_disparo': sugestao_disparo,
                    'score_prioridade': score_prioridade,
                    'dados_extraidos_ia': dados_extraidos,
                    'metadados_analise_ia': {
                        'modelo': self.model,
                        'tokens_prompt': tokens_input,
                        'tokens_completion': tokens_output,
                        'tokens_total': tokens_total,
                        'custo_brl': custo_brl,
                        'tempo_segundos': round(elapsed_time, 2),
                        'versao_prompt': '1.0',
                        'template_usado': f'{tipo_remarketing}_v1',
                        'analisado_em': datetime.now().isoformat(),
                        'tempo_inativo_horas': tempo_inativo_horas
                    },
                    'analisado_em': datetime.now()
                }

                logger.info(
                    f"✅ Lead {conversation_id} analisado com sucesso - "
                    f"Score: {score_prioridade} | Custo: R$ {custo_brl:.4f} | "
                    f"Tokens: {tokens_total} | Tempo: {elapsed_time:.2f}s"
                )

                return resultado

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Tentativa {attempt}/{self.MAX_RETRIES} falhou "
                    f"para lead {conversation_id}: {str(e)}"
                )

                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    self.stats['total_calls'] += 1
                    self.stats['failed_calls'] += 1
                    logger.error(
                        f"❌ Falha permanente ao analisar lead {conversation_id} "
                        f"após {self.MAX_RETRIES} tentativas: {str(e)}"
                    )
                    raise

        # Nunca deve chegar aqui, mas por segurança
        raise last_exception or Exception(f"Falha desconhecida ao analisar lead {conversation_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de uso do analyzer.

        Returns:
            Dict com estatísticas
        """
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_calls'] / self.stats['total_calls']
                if self.stats['total_calls'] > 0 else 0
            ),
            'avg_cost_brl': (
                self.stats['total_cost_brl'] / self.stats['successful_calls']
                if self.stats['successful_calls'] > 0 else 0
            )
        }

    def reset_stats(self):
        """Reseta estatísticas de uso."""
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_cost_brl': 0.0,
        }
        logger.info(f"Estatísticas resetadas para tenant {self.tenant_id}")
