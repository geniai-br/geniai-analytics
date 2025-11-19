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
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        Retorna o prompt genérico para análise de conversas de leads (multi-tenant).

        ATUALIZADO: Agora inclui análise de resolução e necessidade de remarketing.

        Returns:
            str: System prompt para OpenAI
        """
        return """Você é um analista especializado em conversas de leads de negócios.

Sua tarefa é analisar a conversa completa entre o lead e a empresa e extrair as seguintes informações em formato JSON:

{
  "nome_mapeado_bot": "string - nome completo do lead extraído da conversa",
  "visita_agendada": "boolean - confirmação explícita de agendamento",
  "status_resolucao": "string - resolvida | abandonada_cliente | abandonada_atendente | pendente_resposta | em_negociacao",
  "precisa_remarketing": "boolean - se precisa enviar mensagem de follow-up",
  "motivo_remarketing": "string - justificativa técnica (interna, não enviar ao cliente)",
  "nivel_interesse": "string - alto | medio | baixo | nenhum",
  "objecoes_identificadas": ["array de strings - objeções do lead"],
  "sinais_positivos": ["array de strings - indicadores de interesse"],
  "analise_ia": "string - análise detalhada 3-5 parágrafos",
  "sugestao_disparo": "string ou null - mensagem personalizada (null se não precisa remarketing)"
}

═══════════════════════════════════════════════════════════════════

📋 CAMPO: nome_mapeado_bot
═══════════════════════════════════════════════════════════════════
- Extrair o NOME COMPLETO que o lead forneceu durante a conversa
- Procurar por perguntas do atendente: "Qual é o seu nome?", "Me diz seu nome", "Como você se chama?"
- O nome deve ser EXATAMENTE como o lead respondeu (primeiro e último nome se possível)
- Se o lead NÃO forneceu nome na conversa, retornar string vazia ""
- NÃO usar o nome do contato do sistema, APENAS o que foi dito na conversa

═══════════════════════════════════════════════════════════════════
✅ CAMPO: visita_agendada
═══════════════════════════════════════════════════════════════════
Marcar TRUE apenas se houver CONFIRMAÇÃO EXPLÍCITA:
- Palavras-chave: "agendado ✅", "confirmado", "te espero", "nos vemos", "marcado para", "você está agendado"
- Atendente diz: "agendei sua visita", "visita confirmada", "anotei aqui"
- Lead confirma horário/data específica e atendente confirma de volta

Marcar FALSE se:
- Lead apenas perguntou sobre agendar ("posso agendar?", "como faço para marcar?")
- Ainda está negociando data/horário sem confirmação final
- Lead disse "vou pensar" ou "depois eu confirmo"

═══════════════════════════════════════════════════════════════════
🔄 CAMPO: status_resolucao
═══════════════════════════════════════════════════════════════════
Analise a ÚLTIMA MENSAGEM e o CONTEXTO GERAL para classificar:

"resolvida":
- Atendimento foi concluído com sucesso
- Exemplos: agendamento confirmado, pagamento resolvido, dúvida esclarecida, problema solucionado
- Lead agradeceu e encerrou: "obrigado", "tudo certo", "👍", "valeu"
- Última mensagem do atendente foi uma CONFIRMAÇÃO: "agendado ✅", "pago", "resolvido", "feito"
- NÃO PRECISA remarketing - atendimento completo

"abandonada_cliente":
- Lead parou de responder no meio da conversa
- Atendente fez pergunta/solicitação mas lead não respondeu
- Última mensagem foi do atendente ou bot esperando resposta do cliente
- PRECISA remarketing - tentar reengajar

"abandonada_atendente":
- Lead fez pergunta/solicitação mas atendente não respondeu
- Lead demonstrou interesse mas ficou sem retorno
- Última mensagem foi do lead esperando resposta
- PRECISA remarketing urgente - lead esperando atendimento

"pendente_resposta":
- Conversa ativa mas aguardando próxima interação
- Lead pediu tempo para pensar ("vou ver", "depois confirmo")
- Solicitação de informação que será enviada depois
- PODE PRECISAR remarketing suave após alguns dias

"em_negociacao":
- Conversa ativa, múltiplas trocas de mensagens recentes
- Negociando detalhes (preço, horário, condições)
- Ainda não chegou a uma conclusão
- NÃO PRECISA remarketing agora - aguardar conclusão natural

═══════════════════════════════════════════════════════════════════
🎯 CAMPO: precisa_remarketing
═══════════════════════════════════════════════════════════════════
Marcar TRUE apenas se REALMENTE precisa enviar mensagem de follow-up:

TRUE (PRECISA):
- status_resolucao = "abandonada_cliente" (cliente sumiu, tentar reengajar)
- status_resolucao = "abandonada_atendente" (cliente sem resposta, urgente)
- status_resolucao = "pendente_resposta" E já passou tempo (lead pediu tempo)
- Lead demonstrou interesse mas não concluiu ação

FALSE (NÃO PRECISA):
- status_resolucao = "resolvida" (atendimento completo, não incomodar)
- status_resolucao = "em_negociacao" (conversa ativa, aguardar)
- Lead agradeceu e encerrou
- Pagamento/agendamento/problema já foi resolvido
- Lead explicitamente pediu para não ser contatado

═══════════════════════════════════════════════════════════════════
💬 CAMPO: motivo_remarketing
═══════════════════════════════════════════════════════════════════
Justificativa TÉCNICA INTERNA (NÃO enviar ao cliente):
- Explicar por que precisa (ou não) de remarketing
- Exemplos:
  * "Lead agendou visita e atendente confirmou. Atendimento completo."
  * "Lead perguntou sobre treino mas não recebeu resposta do atendente. Precisa follow-up."
  * "Cliente demonstrou interesse em plano mas parou de responder. Tentar reengajar."
  * "Pagamento foi resolvido e cliente agradeceu. Não precisa contato adicional."

═══════════════════════════════════════════════════════════════════
📊 CAMPO: nivel_interesse
═══════════════════════════════════════════════════════════════════
"alto":
- Fez perguntas específicas sobre produto/serviço
- Solicitou agendamento/compra/contratação
- Demonstrou urgência ("hoje", "agora", "rápido")
- Engajamento alto (múltiplas mensagens, respostas rápidas)

"medio":
- Perguntou sobre preços/condições
- Demonstrou interesse mas com dúvidas
- Respondeu perguntas do atendente
- Não demonstrou urgência

"baixo":
- Respostas curtas e vagas
- Poucas mensagens
- Interesse superficial
- Pediu tempo para pensar

"nenhum":
- Não demonstrou interesse real
- Spam, mensagem errada, engano
- Apenas queria informação pontual
- Não é lead qualificado

═══════════════════════════════════════════════════════════════════
🚫 CAMPO: objecoes_identificadas
═══════════════════════════════════════════════════════════════════
Lista de objeções/barreiras que o lead mencionou:
- Preço: "muito caro", "não cabe no orçamento", "tem mais barato?"
- Tempo: "não tenho tempo", "muita correria", "horário ruim"
- Distância: "muito longe", "não tenho como ir", "fica onde?"
- Dúvidas: "não sei se funciona", "tenho medo", "será que dá certo?"
- Outros: qualquer barreira mencionada

Retornar array vazio [] se não houver objeções.

═══════════════════════════════════════════════════════════════════
✨ CAMPO: sinais_positivos
═══════════════════════════════════════════════════════════════════
Lista de indicadores positivos de interesse/engajamento:
- "quero agendar", "quando posso ir?", "tem vaga hoje?"
- "quanto custa?", "quais são os planos?"
- Respondeu rápido, fez múltiplas perguntas
- Agradeceu, elogiou, mostrou entusiasmo
- Confirmou interesse explicitamente

Retornar array vazio [] se não houver sinais positivos.

═══════════════════════════════════════════════════════════════════
📝 CAMPO: analise_ia
═══════════════════════════════════════════════════════════════════
Análise detalhada com 3-5 parágrafos:

Parágrafo 1: Resumo do perfil do lead
- Contexto da conversa, interesse demonstrado, necessidades mencionadas

Parágrafo 2: Nível de engajamento e sinais de interesse
- Perguntas feitas, tom da conversa, urgência, qualidade das respostas

Parágrafo 3: Objeções ou barreiras identificadas (se houver)
- O que pode impedir a conversão, preocupações do lead

Parágrafo 4: Status da conversa e próximos passos
- Se foi resolvida, se precisa follow-up, o que ficou pendente

Parágrafo 5: Recomendação estratégica
- Como abordar esse lead, melhor momento para contato, estratégia de conversão

═══════════════════════════════════════════════════════════════════
💌 CAMPO: sugestao_disparo
═══════════════════════════════════════════════════════════════════
IMPORTANTE: Só preencher se precisa_remarketing = true

Se precisa_remarketing = false:
- Retornar null (não enviar mensagem)

Se precisa_remarketing = true:
- Mensagem PERSONALIZADA baseada no perfil e interesse do lead
- Mencionar especificamente o que o lead demonstrou interesse
- Incluir call-to-action claro
- Usar tom humanizado e empático
- Máximo 3-4 frases
- Não mencionar "há alguns dias" se foi recente

Exemplos de BOAS sugestões:
- "Oi [Nome]! Vi que você perguntou sobre [X]. Conseguiu tirar suas dúvidas? Estou à disposição!"
- "Olá [Nome]! Notei seu interesse em [X]. Gostaria de saber mais ou agendar uma visita?"

Exemplos de RUINS (evitar):
- Mensagens genéricas sem personalização
- Mencionar tempo incorreto ("há alguns dias" quando foi ontem)
- Perguntar algo que já foi resolvido

═══════════════════════════════════════════════════════════════════

INSTRUÇÕES FINAIS:
- Analise TODO o histórico de mensagens, não apenas as últimas
- Considere o contexto completo da conversa
- Seja preciso na classificação do status_resolucao
- Só marque precisa_remarketing = true se REALMENTE fizer sentido
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
            'analise_ia': '',
            'sugestao_disparo': '',
        }

        # Validar entrada
        if not message_text or not isinstance(message_text, str):
            logger.warning(f"Texto de mensagem vazio ou inválido para tenant {self.tenant_id}")
            return result

        # SANITIZAR texto de entrada (remover NULL bytes antes de enviar para OpenAI)
        message_text = self._sanitize_text(message_text)

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

    def _sanitize_text(self, text: str) -> str:
        """
        Remove NULL bytes e caracteres inválidos para PostgreSQL.

        Args:
            text: Texto a ser sanitizado

        Returns:
            Texto limpo sem NULL bytes
        """
        if not text:
            return ''

        # Remover NULL bytes (0x00) - causam erro no PostgreSQL
        text = text.replace('\x00', '')

        # Remover outros caracteres de controle problemáticos (opcional)
        # text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')

        return text

    def _process_openai_response(self, analysis: Dict) -> Dict:
        """
        Processa resposta da OpenAI e converte para formato padrão.

        ATUALIZADO: Agora usa novos campos (status_resolucao, precisa_remarketing, nivel_interesse)
        para calcular score de forma mais inteligente.

        Args:
            analysis: Dict retornado pela OpenAI

        Returns:
            Dict no formato padrão (compatível com BaseAnalyzer)
        """
        # ===================================================================
        # EXTRAIR CAMPOS DO JSON DA IA
        # ===================================================================
        visit_scheduled = analysis.get('visita_agendada', False)
        status_resolucao = analysis.get('status_resolucao', 'em_negociacao')
        precisa_remarketing = analysis.get('precisa_remarketing', True)
        nivel_interesse = analysis.get('nivel_interesse', 'medio')
        objecoes = analysis.get('objecoes_identificadas', [])
        sinais_positivos = analysis.get('sinais_positivos', [])
        analise_ia = analysis.get('analise_ia', '')
        sugestao_disparo = analysis.get('sugestao_disparo', None)
        motivo_remarketing = analysis.get('motivo_remarketing', '')

        # ===================================================================
        # DETERMINAR is_lead
        # ===================================================================
        # É lead se tem análise válida E nível de interesse não é "nenhum"
        has_analysis = bool(analise_ia and len(analise_ia) > 50)
        is_lead = has_analysis and nivel_interesse != 'nenhum'

        # ===================================================================
        # CALCULAR SCORE INTELIGENTE (0-100)
        # ===================================================================
        score = self._calculate_smart_score(
            visit_scheduled=visit_scheduled,
            status_resolucao=status_resolucao,
            nivel_interesse=nivel_interesse,
            precisa_remarketing=precisa_remarketing,
            num_objecoes=len(objecoes) if isinstance(objecoes, list) else 0,
            num_sinais_positivos=len(sinais_positivos) if isinstance(sinais_positivos, list) else 0
        )

        # ===================================================================
        # CRM CONVERTED
        # ===================================================================
        # Converteu se: agendou visita OU status foi resolvido positivamente
        crm_converted = bool(visit_scheduled) or (status_resolucao == 'resolvida' and nivel_interesse in ['alto', 'medio'])

        # ===================================================================
        # SUGESTÃO DE DISPARO
        # ===================================================================
        # Se precisa_remarketing = False, limpar sugestão (não enviar)
        if not precisa_remarketing:
            sugestao_disparo = None
        elif sugestao_disparo:
            sugestao_disparo = self._sanitize_text(str(sugestao_disparo))
        else:
            sugestao_disparo = ''

        # ===================================================================
        # MONTAR RESULTADO
        # ===================================================================
        result = {
            # Campos padrão (BaseAnalyzer)
            'is_lead': is_lead,
            'visit_scheduled': bool(visit_scheduled),
            'crm_converted': crm_converted,
            'ai_probability_label': self._score_to_label(score),
            'ai_probability_score': score,

            # Campos específicos OpenAI (SANITIZAR para remover NULL bytes)
            'nome_mapeado_bot': self._sanitize_text(analysis.get('nome_mapeado_bot', '')),
            'analise_ia': self._sanitize_text(analise_ia),
            'sugestao_disparo': sugestao_disparo if sugestao_disparo else '',

            # Novos campos para remarketing (opcional - podem ser salvos em JSONB)
            '_status_resolucao': status_resolucao,
            '_precisa_remarketing': precisa_remarketing,
            '_nivel_interesse': nivel_interesse,
            '_motivo_remarketing': motivo_remarketing,
            '_objecoes': objecoes if isinstance(objecoes, list) else [],
            '_sinais_positivos': sinais_positivos if isinstance(sinais_positivos, list) else [],
        }

        logger.debug(f"Conversa processada: is_lead={is_lead}, score={score:.1f}, "
                    f"status={status_resolucao}, remarketing={precisa_remarketing}")

        return result

    def _calculate_smart_score(
        self,
        visit_scheduled: bool,
        status_resolucao: str,
        nivel_interesse: str,
        precisa_remarketing: bool,
        num_objecoes: int,
        num_sinais_positivos: int
    ) -> float:
        """
        Calcula score inteligente baseado em múltiplos fatores.

        Lógica:
        - Visita agendada = 95+ (muito alta prioridade)
        - Abandonada atendente = 85-90 (urgente, cliente esperando)
        - Alto interesse + sinais positivos = 70-85
        - Médio interesse = 40-70 (varia com objeções)
        - Baixo interesse = 20-40
        - Resolvida sem remarketing = 5-15 (baixíssima prioridade)
        - Nenhum interesse = 0

        Args:
            visit_scheduled: Se agendou visita
            status_resolucao: Status da conversa
            nivel_interesse: Nível de interesse do lead
            precisa_remarketing: Se precisa follow-up
            num_objecoes: Quantidade de objeções
            num_sinais_positivos: Quantidade de sinais positivos

        Returns:
            float: Score de 0 a 100
        """
        score = 50.0  # Base

        # ====== VISITA AGENDADA (máxima prioridade) ======
        if visit_scheduled:
            return 95.0

        # ====== STATUS DE RESOLUÇÃO ======
        if status_resolucao == 'abandonada_atendente':
            # Cliente esperando resposta = urgente!
            score = 88.0
        elif status_resolucao == 'abandonada_cliente':
            # Cliente sumiu, tentar reengajar
            score = 65.0
        elif status_resolucao == 'pendente_resposta':
            # Aguardando ação do cliente
            score = 55.0
        elif status_resolucao == 'em_negociacao':
            # Conversa ativa, não precisa remarketing ainda
            score = 45.0
        elif status_resolucao == 'resolvida':
            # Atendimento completo
            if precisa_remarketing:
                score = 30.0  # Resolvida mas pode tentar upsell
            else:
                score = 10.0  # Resolvida, não incomodar

        # ====== NÍVEL DE INTERESSE (ajuste) ======
        if nivel_interesse == 'alto':
            score += 20
        elif nivel_interesse == 'medio':
            score += 5
        elif nivel_interesse == 'baixo':
            score -= 10
        elif nivel_interesse == 'nenhum':
            return 0.0  # Sem interesse, score zero

        # ====== SINAIS POSITIVOS (boost) ======
        if num_sinais_positivos > 0:
            score += min(num_sinais_positivos * 3, 12)  # Até +12

        # ====== OBJEÇÕES (penalidade) ======
        if num_objecoes > 0:
            score -= min(num_objecoes * 5, 15)  # Até -15

        # ====== REMARKETING (ajuste final) ======
        if not precisa_remarketing:
            # Não precisa remarketing = baixa prioridade
            score = min(score, 15.0)

        # ====== GARANTIR RANGE 0-100 ======
        score = max(0.0, min(100.0, score))

        return round(score, 1)

    def analyze_dataframe(self, df: pd.DataFrame, skip_analyzed: bool = True) -> pd.DataFrame:
        """
        Analisa um DataFrame completo de conversas.

        Args:
            df: DataFrame com colunas:
                - message_compiled (texto das mensagens)
                - contact_name (opcional)
                - contact_messages_count (opcional)
                - analise_ia (opcional - para skip_analyzed)
            skip_analyzed: Se True, pula conversas que já têm analise_ia preenchida

        Returns:
            DataFrame com colunas de análise adicionadas
        """
        if df.empty:
            logger.warning("DataFrame vazio recebido para análise")
            return df

        total_rows = len(df)

        # Filtrar conversas que precisam ser analisadas
        if skip_analyzed and 'analise_ia' in df.columns:
            # Identificar conversas que NÃO têm análise (analise_ia vazio ou NULL)
            needs_analysis = (df['analise_ia'].isna()) | (df['analise_ia'] == '')
            df_to_analyze = df[needs_analysis].copy()
            df_already_analyzed = df[~needs_analysis].copy()

            skipped = len(df_already_analyzed)
            to_process = len(df_to_analyze)

            logger.info(f"Total conversas: {total_rows}")
            logger.info(f"  ✅ Já analisadas (pulando): {skipped}")
            logger.info(f"  🔄 Pendentes (processando): {to_process}")

            if to_process == 0:
                logger.info("Todas as conversas já foram analisadas! Nada a fazer.")
                return df
        else:
            df_to_analyze = df.copy()
            df_already_analyzed = pd.DataFrame()
            to_process = total_rows
            logger.info(f"Analisando {to_process} conversas com OpenAI para tenant {self.tenant_id}")

        start_time = time.time()

        # PROCESSAMENTO PARALELO - 5 workers simultâneos
        logger.info(f"🚀 Iniciando processamento PARALELO com 5 workers...")

        results_list = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Criar futures para cada conversa
            future_to_idx = {
                executor.submit(
                    self.analyze_conversation,
                    message_text=row.get('message_compiled', None),
                    contact_name=row.get('contact_name', None),
                    message_count=row.get('contact_messages_count', 0)
                ): idx
                for idx, row in df_to_analyze.iterrows()
            }

            # Processar resultados conforme completam
            completed = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result(timeout=30)  # 30s timeout por conversa
                    results_list.append((idx, result))
                    completed += 1

                    # Log progresso a cada 10 conversas
                    if completed % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (to_process - completed) / rate if rate > 0 else 0
                        logger.info(f"  ⏳ {completed}/{to_process} ({completed/to_process*100:.1f}%) - "
                                  f"{rate:.1f} conv/s - ETA: {eta/60:.1f} min")
                except Exception as e:
                    logger.error(f"Erro ao processar conversa {idx}: {e}")
                    # Resultado default em caso de erro
                    results_list.append((idx, {
                        'is_lead': False,
                        'visit_scheduled': False,
                        'crm_converted': False,
                        'ai_probability_label': 'N/A',
                        'ai_probability_score': 0.0,
                        'nome_mapeado_bot': '',
                        'analise_ia': '',
                        'sugestao_disparo': '',
                    }))

        # Ordenar resultados pelo índice original
        results_list.sort(key=lambda x: x[0])
        results = pd.Series([r[1] for r in results_list], index=[r[0] for r in results_list])

        # Extrair campos APENAS para df_to_analyze
        df_to_analyze['is_lead'] = results.apply(lambda x: x['is_lead'])
        df_to_analyze['visit_scheduled'] = results.apply(lambda x: x['visit_scheduled'])
        df_to_analyze['crm_converted'] = results.apply(lambda x: x['crm_converted'])
        df_to_analyze['ai_probability_label'] = results.apply(lambda x: x['ai_probability_label'])
        df_to_analyze['ai_probability_score'] = results.apply(lambda x: x['ai_probability_score'])

        # Campos adicionais OpenAI (apenas campos genéricos multi-tenant)
        df_to_analyze['nome_mapeado_bot'] = results.apply(lambda x: x.get('nome_mapeado_bot', ''))
        df_to_analyze['analise_ia'] = results.apply(lambda x: x.get('analise_ia', ''))
        df_to_analyze['sugestao_disparo'] = results.apply(lambda x: x.get('sugestao_disparo', ''))

        # ===================================================================
        # NOVOS CAMPOS: Remarketing Intelligence (2025-11-19)
        # ===================================================================
        # Colunas dedicadas no banco (queries rápidas)
        df_to_analyze['precisa_remarketing'] = results.apply(lambda x: x.get('_precisa_remarketing', True))
        df_to_analyze['status_resolucao'] = results.apply(lambda x: x.get('_status_resolucao', None))
        df_to_analyze['nivel_interesse'] = results.apply(lambda x: x.get('_nivel_interesse', None))

        # JSONB: Dados estruturados completos em dados_extraidos_ia
        df_to_analyze['dados_extraidos_ia'] = results.apply(lambda x: json.dumps({
            'status_resolucao': x.get('_status_resolucao', ''),
            'precisa_remarketing': x.get('_precisa_remarketing', True),
            'nivel_interesse': x.get('_nivel_interesse', ''),
            'motivo_remarketing': x.get('_motivo_remarketing', ''),
            'objecoes_identificadas': x.get('_objecoes', []),
            'sinais_positivos': x.get('_sinais_positivos', []),
        }) if x.get('_precisa_remarketing') is not None else None)

        # Combinar DataFrames (analisadas + já existentes)
        if not df_already_analyzed.empty:
            df_final = pd.concat([df_to_analyze, df_already_analyzed], ignore_index=False)
            # Restaurar ordem original
            df_final = df_final.loc[df.index]
        else:
            df_final = df_to_analyze

        # Estatísticas
        lead_count = df_to_analyze['is_lead'].sum()
        visit_count = df_to_analyze['visit_scheduled'].sum()
        conversion_count = df_to_analyze['crm_converted'].sum()

        elapsed = time.time() - start_time
        avg_time = elapsed / to_process if to_process > 0 else 0

        logger.info(f"Análise OpenAI concluída: {lead_count} leads, "
                   f"{visit_count} visitas, {conversion_count} conversões")
        logger.info(f"Tempo total: {elapsed:.2f}s, Média: {avg_time:.2f}s/conversa")
        logger.info(f"API calls: {self.stats['successful_calls']} sucesso, "
                   f"{self.stats['failed_calls']} falhas, "
                   f"{self.stats['total_tokens']} tokens")

        return df_final

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
