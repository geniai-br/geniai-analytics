"""
CampaignVariableGenerator - Geração de Variáveis com IA
=======================================================

Este módulo usa OpenAI GPT-4o-mini para gerar variáveis personalizadas
para campanhas de remarketing.

Funcionalidades:
    - Geração de variáveis {{1}}, {{2}}, {{3}} baseadas em análise prévia
    - Processamento em lote com callback de progresso
    - Controle de custos e tokens
    - Rate limiting integrado

Autor: Isaac (via Claude Code)
Data: 2025-11-26
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import (
    Campaign,
    CampaignLead,
    CampaignType,
    CampaignTone,
    LeadStatus,
)

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes de custo (GPT-4o-mini - Nov 2025)
COST_PER_1K_INPUT_TOKENS_USD = 0.00015
COST_PER_1K_OUTPUT_TOKENS_USD = 0.0006
USD_TO_BRL = 5.80  # Taxa aproximada


class CampaignVariableGenerator:
    """
    Gera variáveis de campanha usando OpenAI GPT-4o-mini.

    Esta classe é responsável por:
    1. Buscar dados de análise prévia do lead (conversas_analytics_ai)
    2. Construir prompt com contexto da campanha
    3. Chamar OpenAI para gerar variáveis personalizadas
    4. Retornar variáveis com metadados de custo

    Uso:
        >>> generator = CampaignVariableGenerator(
        ...     openai_api_key="sk-...",
        ...     engine=engine,
        ...     tenant_id=1
        ... )
        >>> result = generator.generate_for_lead(campaign, lead)
        >>> print(result["var1"], result["var2"], result["var3"])
    """

    # Prompt para geração de variáveis - Sistema Flexível por Tipo de Campanha (FASE10 v2)
    VARIABLE_PROMPT_TEMPLATE = """Você é um especialista em remarketing de WhatsApp.

TAREFA: Gerar os valores das variáveis {{{{1}}}}, {{{{2}}}} e {{{{3}}}} para uma mensagem de {campaign_type_display}.

================================================================================
TIPO DE CAMPANHA: {campaign_type_display}
================================================================================
{campaign_type_description}

================================================================================
BRIEFING DA CAMPANHA (CONTEXTO PRINCIPAL)
================================================================================
{briefing}

================================================================================
TOM DA MENSAGEM
================================================================================
{tone_display}: {tone_description}

================================================================================
TEMPLATE DA MENSAGEM
================================================================================
{template}

================================================================================
DETALHES ESTRUTURADOS DA CAMPANHA
================================================================================
{structured_context}

================================================================================
ANÁLISE DO LEAD (conversa prévia)
================================================================================
- Nome do lead: {contact_name}
- Telefone: {contact_phone}
- Interesse principal: {interesse}
- Objetivo mencionado: {objetivo}
- Objeções identificadas: {objecoes}
- Contexto da conversa: {contexto_conversa}
- Última mensagem há: {dias_inativo} dias

================================================================================
INSTRUÇÕES PARA GERAÇÃO
================================================================================
1. {{{{1}}}} = PRIMEIRO NOME do lead (ex: "João", não "João Silva"). Se não souber, use "você"
2. {{{{2}}}} = Conexão personalizada baseada no briefing + interesse/objeção do lead
3. {{{{3}}}} = Call-to-action ou oferta baseada no briefing + tom definido

RESTRIÇÕES OBRIGATÓRIAS:
- {{{{1}}}}: Máximo 50 caracteres (apenas primeiro nome ou "você")
- {{{{2}}}}: Máximo 150 caracteres
- {{{{3}}}}: Máximo 200 caracteres
- Respeitar o TOM definido: {tone_display}
- NÃO usar emojis
- NÃO fazer promessas além do briefing/contexto
- Frases devem começar com letra minúscula (exceto nome próprio)
- NÃO terminar com ponto final (a mensagem continua depois)

================================================================================
RESPONDA APENAS EM JSON VÁLIDO (sem markdown, sem explicações):
================================================================================
{{"var1": "valor", "var2": "valor", "var3": "valor"}}"""

    # Mapeamento de tipos para descrições legíveis
    CAMPAIGN_TYPE_DESCRIPTIONS = {
        "promotional": ("Campanha Promocional", "Foco em descontos, ofertas e vendas. A mensagem deve criar urgência e destacar a economia."),
        "reengagement": ("Campanha de Reengajamento", "Foco em reconquistar leads inativos. A mensagem deve ser empática e reconhecer que o lead já demonstrou interesse antes."),
        "event": ("Campanha de Evento/Convite", "Foco em convidar para um evento. A mensagem deve destacar data, local e benefício de participar."),
        "survey": ("Campanha de Pesquisa/Feedback", "Foco em coletar opinião. A mensagem deve valorizar o cliente e mostrar que a opinião dele importa."),
        "informative": ("Campanha Informativa", "Foco em comunicar novidades ou mudanças. A mensagem deve ser clara e direta."),
        "custom": ("Campanha Personalizada", "Sem formato específico. Use o briefing como guia principal para entender o objetivo."),
    }

    # Mapeamento de tons para descrições
    TONE_DESCRIPTIONS_MAP = {
        "urgente": ("Urgente", "Criar senso de escassez e tempo limitado. Use frases como 'últimas vagas', 'só até amanhã', 'não perca'."),
        "amigavel": ("Amigável", "Tom leve e descontraído, como se fosse um amigo falando. Use linguagem informal mas respeitosa."),
        "profissional": ("Profissional", "Formal mas acolhedor. Linguagem correta, sem gírias, mas não robótica."),
        "empatico": ("Empático", "Demonstrar compreensão e cuidado. Reconhecer possíveis objeções e mostrar que entende o lado do cliente."),
        "animado": ("Animado", "Entusiasmado e convidativo. Transmitir energia positiva e empolgação."),
        "agradecido": ("Agradecido", "Valorizar o cliente. Começar agradecendo ou reconhecendo a importância dele."),
        "curioso": ("Curioso", "Despertar interesse. Usar perguntas ou frases que gerem curiosidade."),
        "exclusivo": ("Exclusivo", "Fazer o cliente se sentir especial. Usar termos como 'selecionado', 'exclusivo para você', 'poucos escolhidos'."),
        "direto": ("Direto", "Objetivo e sem rodeios. Ir direto ao ponto, sem floreios."),
    }

    def __init__(
        self,
        openai_api_key: str,
        engine: Engine,
        tenant_id: int,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 400,
        rate_limit_rpm: int = 60
    ):
        """
        Inicializa o gerador de variáveis.

        Args:
            openai_api_key: Chave da API OpenAI
            engine: Engine SQLAlchemy
            tenant_id: ID do tenant
            model: Modelo OpenAI (default: gpt-4o-mini)
            temperature: Temperatura para geração (0.0-1.0)
            max_tokens: Máximo de tokens na resposta
            rate_limit_rpm: Limite de requisições por minuto
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.engine = engine
        self.tenant_id = tenant_id
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rate_limit_rpm = rate_limit_rpm

        # Controle de rate limiting
        self._last_request_time = 0
        self._min_interval = 60.0 / rate_limit_rpm

        # Estatísticas da sessão
        self._stats = {
            "calls": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0,
            "cost_brl": 0.0,
            "errors": 0,
        }

        logger.info(f"CampaignVariableGenerator inicializado (model={model}, tenant={tenant_id})")

    def _wait_rate_limit(self) -> None:
        """Aguarda se necessário para respeitar rate limit"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calcula custo em BRL.

        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída

        Returns:
            Custo em reais
        """
        input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS_USD
        output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS_USD
        total_usd = input_cost + output_cost
        return round(total_usd * USD_TO_BRL, 6)

    def _get_lead_analysis(self, conversation_id: int) -> Dict[str, Any]:
        """
        Busca análise prévia do lead em conversations_analytics.

        Os dados de análise estão armazenados em:
        - analise_ia: Texto resumido da análise
        - dados_extraidos_ia: JSON com interesse, objeções, etc.
        - nivel_interesse: alto/medio/baixo/nenhum
        - sugestao_disparo: Sugestão de mensagem

        Args:
            conversation_id: ID da conversa

        Returns:
            Dicionário com dados da análise
        """
        query = text("""
            SELECT
                ca.contact_name,
                ca.contact_phone,
                ca.nome_mapeado_bot,
                ca.message_compiled,
                ca.mc_last_message_at,
                ca.tipo_conversa,
                ca.nivel_interesse,
                ca.analise_ia,
                ca.sugestao_disparo,
                ca.dados_extraidos_ia
            FROM conversations_analytics ca
            WHERE ca.conversation_id = :conversation_id
              AND ca.tenant_id = :tenant_id
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "conversation_id": conversation_id,
                "tenant_id": self.tenant_id
            })
            row = result.fetchone()

            if not row:
                return {}

            # Calcular dias de inatividade
            dias_inativo = 0
            if row[4]:  # mc_last_message_at
                delta = datetime.now() - row[4]
                dias_inativo = delta.days

            # Extrair dados do JSON (dados_extraidos_ia)
            dados_ia = row[9] or {}
            if isinstance(dados_ia, str):
                try:
                    dados_ia = json.loads(dados_ia)
                except:
                    dados_ia = {}

            # Formatar objeções como string
            objecoes = dados_ia.get("objecoes_identificadas", dados_ia.get("objecoes", []))
            if isinstance(objecoes, list):
                objecoes = ", ".join(objecoes) if objecoes else "nenhuma identificada"

            return {
                "contact_name": row[2] or row[0] or "Lead",  # nome_mapeado_bot ou contact_name
                "contact_phone": row[1] or "",
                "tipo_conversa": row[5] or "não classificada",
                "interesse": dados_ia.get("interesse_mencionado", dados_ia.get("interesse", "não identificado")),
                "objetivo": dados_ia.get("objetivo", "não identificado"),
                "objecoes": objecoes,
                "contexto_conversa": row[7] or dados_ia.get("contexto_resumido", "conversa padrão"),  # analise_ia
                "sugestao_remarketing": row[8] or "",  # sugestao_disparo
                "dias_inativo": dias_inativo,
                "nivel_interesse": row[6] or "não definido",
            }

    def _build_prompt(
        self,
        campaign: Campaign,
        lead: CampaignLead,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Constrói prompt para a OpenAI usando o sistema flexível de contexto.

        O novo sistema usa:
        - campaign_type: Tipo da campanha (promotional, reengagement, event, etc.)
        - tone: Tom da mensagem (urgente, amigavel, profissional, etc.)
        - briefing: Texto livre descrevendo o objetivo da campanha
        - promotional_context: Detalhes estruturados específicos por tipo

        Args:
            campaign: Campanha com template, tipo, tom, briefing e contexto
            lead: Lead a processar
            analysis: Análise prévia do lead

        Returns:
            Prompt formatado
        """
        # Obter tipo e descrição da campanha
        campaign_type_key = "promotional"  # default
        if hasattr(campaign, 'campaign_type') and campaign.campaign_type:
            if hasattr(campaign.campaign_type, 'value'):
                campaign_type_key = campaign.campaign_type.value
            else:
                campaign_type_key = str(campaign.campaign_type)

        type_info = self.CAMPAIGN_TYPE_DESCRIPTIONS.get(
            campaign_type_key,
            ("Campanha", "Campanha de remarketing.")
        )
        campaign_type_display = type_info[0]
        campaign_type_description = type_info[1]

        # Obter tom e descrição
        tone_key = "profissional"  # default
        if hasattr(campaign, 'tone') and campaign.tone:
            if hasattr(campaign.tone, 'value'):
                tone_key = campaign.tone.value
            else:
                tone_key = str(campaign.tone)

        tone_info = self.TONE_DESCRIPTIONS_MAP.get(
            tone_key,
            ("Profissional", "Tom formal mas acolhedor.")
        )
        tone_display = tone_info[0]
        tone_description = tone_info[1]

        # Obter briefing
        briefing = "Nenhum briefing definido."
        if hasattr(campaign, 'briefing') and campaign.briefing:
            briefing = campaign.briefing

        # Formatar contexto estruturado (campos específicos por tipo)
        structured_context = "Nenhum detalhe estruturado adicional."
        if campaign.promotional_context:
            structured_lines = []
            for key, value in campaign.promotional_context.items():
                # Formatar key para exibição (snake_case -> Title Case)
                display_key = key.replace("_", " ").title()
                structured_lines.append(f"- {display_key}: {value}")
            if structured_lines:
                structured_context = "\n".join(structured_lines)

        return self.VARIABLE_PROMPT_TEMPLATE.format(
            campaign_type_display=campaign_type_display,
            campaign_type_description=campaign_type_description,
            briefing=briefing,
            tone_display=tone_display,
            tone_description=tone_description,
            template=campaign.template_text,
            structured_context=structured_context,
            contact_name=analysis.get("contact_name", lead.contact_name or "Lead"),
            contact_phone=lead.contact_phone,
            interesse=analysis.get("interesse", "não identificado"),
            objetivo=analysis.get("objetivo", "não identificado"),
            objecoes=analysis.get("objecoes", "nenhuma identificada"),
            contexto_conversa=analysis.get("contexto_conversa", "conversa padrão"),
            dias_inativo=analysis.get("dias_inativo", 0),
        )

    def _extract_first_name(self, full_name: str) -> str:
        """Extrai primeiro nome de um nome completo"""
        if not full_name or full_name.lower() in ["lead", "você", "cliente"]:
            return "você"
        return full_name.split()[0].strip()

    def generate_for_lead(
        self,
        campaign: Campaign,
        lead: CampaignLead
    ) -> Dict[str, Any]:
        """
        Gera variáveis para um lead específico.

        Args:
            campaign: Campanha com template e contexto
            lead: Lead a processar

        Returns:
            Dicionário com var1, var2, var3, message_preview, metadata

        Raises:
            Exception: Se erro na geração
        """
        start_time = time.time()

        try:
            # Rate limiting
            self._wait_rate_limit()

            # Buscar análise prévia
            analysis = self._get_lead_analysis(lead.conversation_id)

            # Construir prompt
            prompt = self._build_prompt(campaign, lead, analysis)

            # Chamar OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em remarketing. Responda apenas em JSON válido."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extrair resposta
            content = response.choices[0].message.content.strip()

            # Limpar markdown se presente
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            # Parse JSON
            variables = json.loads(content)

            # Extrair tokens e calcular custo
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost_brl = self._calculate_cost(input_tokens, output_tokens)
            duration = time.time() - start_time

            # Atualizar estatísticas
            self._stats["calls"] += 1
            self._stats["tokens_input"] += input_tokens
            self._stats["tokens_output"] += output_tokens
            self._stats["tokens_total"] += total_tokens
            self._stats["cost_brl"] += cost_brl

            # Preparar resultado
            var1 = variables.get("var1", self._extract_first_name(lead.contact_name))[:50]
            var2 = variables.get("var2", "")[:150]
            var3 = variables.get("var3", "")[:200]

            # Gerar preview da mensagem
            message_preview = campaign.render_preview(var1, var2, var3)

            result = {
                "var1": var1,
                "var2": var2,
                "var3": var3,
                "message_preview": message_preview,
                "status": LeadStatus.PROCESSED,
                "metadata": {
                    "model": self.model,
                    "tokens_input": input_tokens,
                    "tokens_output": output_tokens,
                    "tokens_total": total_tokens,
                    "cost_brl": cost_brl,
                    "duration_seconds": round(duration, 2),
                    "generated_at": datetime.now().isoformat(),
                }
            }

            logger.debug(f"Variáveis geradas para lead {lead.id}: var1='{var1}'")
            return result

        except json.JSONDecodeError as e:
            self._stats["errors"] += 1
            logger.error(f"Erro ao parsear JSON da OpenAI para lead {lead.id}: {e}")
            return {
                "status": LeadStatus.ERROR,
                "error_message": f"Erro ao parsear resposta da IA: {str(e)}",
                "metadata": {"error_type": "json_parse_error"}
            }

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Erro ao gerar variáveis para lead {lead.id}: {e}")
            return {
                "status": LeadStatus.ERROR,
                "error_message": str(e),
                "metadata": {"error_type": type(e).__name__}
            }

    def generate_batch(
        self,
        campaign: Campaign,
        leads: List[CampaignLead],
        on_progress: Optional[Callable[[int, int, CampaignLead], None]] = None,
        max_errors: int = 5
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Processa múltiplos leads em lote.

        Args:
            campaign: Campanha com template e contexto
            leads: Lista de leads a processar
            on_progress: Callback (current, total, lead) chamado após cada lead
            max_errors: Máximo de erros consecutivos antes de parar

        Returns:
            Tupla (lista de resultados, estatísticas do batch)
        """
        results = []
        consecutive_errors = 0
        batch_stats = {
            "total": len(leads),
            "processed": 0,
            "errors": 0,
            "cost_brl": 0.0,
            "tokens_total": 0,
            "duration_seconds": 0,
        }

        start_time = time.time()

        for i, lead in enumerate(leads):
            try:
                result = self.generate_for_lead(campaign, lead)
                result["lead_id"] = lead.id
                result["conversation_id"] = lead.conversation_id
                results.append(result)

                if result.get("status") == LeadStatus.PROCESSED:
                    batch_stats["processed"] += 1
                    batch_stats["cost_brl"] += result.get("metadata", {}).get("cost_brl", 0)
                    batch_stats["tokens_total"] += result.get("metadata", {}).get("tokens_total", 0)
                    consecutive_errors = 0
                else:
                    batch_stats["errors"] += 1
                    consecutive_errors += 1

                # Verificar limite de erros
                if consecutive_errors >= max_errors:
                    logger.warning(f"Interrompendo batch: {max_errors} erros consecutivos")
                    break

                # Callback de progresso
                if on_progress:
                    on_progress(i + 1, len(leads), lead)

            except Exception as e:
                logger.error(f"Erro inesperado no batch (lead {lead.id}): {e}")
                consecutive_errors += 1
                batch_stats["errors"] += 1
                results.append({
                    "lead_id": lead.id,
                    "conversation_id": lead.conversation_id,
                    "status": LeadStatus.ERROR,
                    "error_message": str(e),
                })

                if consecutive_errors >= max_errors:
                    break

        batch_stats["duration_seconds"] = round(time.time() - start_time, 2)

        logger.info(
            f"Batch concluído: {batch_stats['processed']}/{batch_stats['total']} processados, "
            f"{batch_stats['errors']} erros, R$ {batch_stats['cost_brl']:.4f}"
        )

        return results, batch_stats

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da sessão atual.

        Returns:
            Dicionário com estatísticas acumuladas
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reseta estatísticas da sessão"""
        self._stats = {
            "calls": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_total": 0,
            "cost_brl": 0.0,
            "errors": 0,
        }

    def estimate_batch_cost(self, num_leads: int) -> Dict[str, float]:
        """
        Estima custo de processar um batch.

        Args:
            num_leads: Número de leads

        Returns:
            Dicionário com estimativas (min, avg, max)
        """
        # Estimativas baseadas em médias observadas
        avg_input_tokens = 800  # prompt médio
        avg_output_tokens = 100  # resposta média

        cost_per_lead = self._calculate_cost(avg_input_tokens, avg_output_tokens)

        return {
            "num_leads": num_leads,
            "cost_per_lead_brl": cost_per_lead,
            "total_estimated_brl": round(cost_per_lead * num_leads, 4),
            "min_estimated_brl": round(cost_per_lead * num_leads * 0.7, 4),
            "max_estimated_brl": round(cost_per_lead * num_leads * 1.5, 4),
        }