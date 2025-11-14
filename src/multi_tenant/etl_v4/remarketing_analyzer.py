"""
Remarketing Analyzer - ETL V4 Multi-Tenant
===========================================

Responsável por detectar e resetar conversas reabertas, e analisar leads
inativos 24h+ usando OpenAI.

Fases integradas ao ETL:
- FASE 3.5: Reset de conversas reabertas (nova mensagem após análise)
- FASE 4: Análise de leads inativos 24h+

Regra de Negócio:
"A análise deve acontecer quando a última mensagem da conversa tenha passado de
mais de 24 horas. Isso marca a transição da janela de follow-up para a janela
de remarketing."

Fase: 8.2 - ETL Integration
Relacionado: docs/private/checkpoints/FASE8_ANALISE_OPENAI.md
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

import os
import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .analyzers.openai_lead_remarketing_analyzer import OpenAILeadRemarketingAnalyzer


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder para lidar com Decimal."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def detect_and_reset_reopened_conversations(
    local_engine: Engine,
    tenant_id: int
) -> int:
    """
    FASE 3.5: Detecta conversas que foram reabertas (nova mensagem após análise)
    e reseta análise antiga.

    Regra:
    - Se mc_last_message_at > analisado_em (nova mensagem depois da análise)
    - E mc_last_message_at < NOW() - 24h (mensagem recente, conversa reativou)
    - Então: limpar análise (será re-analisada após novo período de 24h)

    Args:
        local_engine: Engine do banco local
        tenant_id: ID do tenant

    Returns:
        Número de conversas resetadas
    """
    query = text("""
        UPDATE conversations_analytics
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
            AND analise_ia IS NOT NULL                           -- Tinha análise
            AND mc_last_message_at > analisado_em                -- Nova msg após análise
            AND mc_last_message_at > NOW() - INTERVAL '24 hours' -- Msg recente (<24h)
        RETURNING conversation_id
    """)

    with local_engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id})
        resetados = result.fetchall()
        conn.commit()

        if resetados:
            ids = [row[0] for row in resetados]
            logger.info(
                f"🔄 {len(resetados)} conversas reabertas detectadas. "
                f"Análises invalidadas."
            )
            logger.debug(f"IDs resetados: {ids}")
            return len(resetados)

        return 0


def analyze_inactive_leads(
    local_engine: Engine,
    tenant_id: int,
    openai_api_key: Optional[str] = None,
    limit: int = 10,
    max_cost_brl: float = 0.10
) -> Dict[str, Any]:
    """
    FASE 4: Analisa leads inativos 24h+ usando OpenAI.

    Query inteligente:
    - WHERE is_lead = true
    - AND analise_ia IS NULL
    - AND mc_last_message_at < NOW() - INTERVAL '24 hours' (CHAVE!)
    - AND contact_messages_count >= 3

    Args:
        local_engine: Engine do banco local
        tenant_id: ID do tenant
        openai_api_key: Chave OpenAI (se None, usa env var)
        limit: Máximo de leads a analisar por execução
        max_cost_brl: Custo máximo em BRL

    Returns:
        Dicionário com estatísticas da análise
    """
    # Verificar se análise de leads está habilitada
    analyze_enabled = os.getenv('ANALYZE_LEADS_ENABLED', 'true').lower() == 'true'
    if not analyze_enabled:
        logger.info("⏭️  Análise de leads DESABILITADA (ANALYZE_LEADS_ENABLED=false)")
        return {
            'analyzed_count': 0,
            'failed_count': 0,
            'total_tokens': 0,
            'total_cost_brl': 0.0,
            'skipped': True
        }

    # Verificar API key
    api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning(
            "⏭️  Análise de leads PULADA: OPENAI_API_KEY não configurada"
        )
        return {
            'analyzed_count': 0,
            'failed_count': 0,
            'total_tokens': 0,
            'total_cost_brl': 0.0,
            'skipped': True
        }

    logger.info("FASE 4: ANALYZE INACTIVE LEADS (24h+)")
    logger.info("-" * 80)

    # Buscar leads inativos 24h+ sem análise de remarketing
    # IMPORTANTE: Busca por tipo_conversa IS NULL (campo novo de remarketing)
    # ao invés de analise_ia IS NULL (campo antigo pode estar preenchido)
    query = text("""
        SELECT
            conversation_id,
            display_id,
            message_compiled,
            contact_name,
            inbox_name,
            contact_messages_count,
            mc_last_message_at,
            EXTRACT(EPOCH FROM (NOW() - mc_last_message_at)) / 3600 AS horas_inativo
        FROM conversations_analytics
        WHERE
            tenant_id = :tenant_id
            AND is_lead = true
            AND tipo_conversa IS NULL                            -- Campo NOVO de remarketing
            AND mc_last_message_at < NOW() - INTERVAL '24 hours'
            AND contact_messages_count >= 3
            AND message_compiled IS NOT NULL
        ORDER BY mc_last_message_at ASC
        LIMIT :limit
    """)

    with local_engine.connect() as conn:
        result = conn.execute(query, {
            'tenant_id': tenant_id,
            'limit': limit
        })
        leads = [dict(row._mapping) for row in result]

    if not leads:
        logger.info("✅ Nenhum lead inativo (24h+) para analisar")
        return {
            'analyzed_count': 0,
            'failed_count': 0,
            'total_tokens': 0,
            'total_cost_brl': 0.0
        }

    logger.info(f"📊 Encontrados {len(leads)} leads inativos para análise")

    # Inicializar analisador
    analyzer = OpenAILeadRemarketingAnalyzer(
        tenant_id=tenant_id,
        api_key=api_key,
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini-2024-07-18')
    )

    analyzed_count = 0
    failed_count = 0
    total_tokens = 0
    total_cost_brl = 0.0

    for lead in leads:
        try:
            # Verificar limite de custo
            if total_cost_brl >= max_cost_brl:
                logger.warning(
                    f"⚠️  Custo máximo atingido (R$ {total_cost_brl:.4f}). "
                    f"Parando análise (restam {len(leads) - analyzed_count} leads)"
                )
                break

            # Classificar tipo de remarketing
            tipo_remarketing = analyzer.get_remarketing_type(
                lead['horas_inativo']
            )

            # Analisar lead
            resultado = analyzer.analyze_lead(
                conversation_id=lead['conversation_id'],
                conversa_compilada=lead['message_compiled'],
                contact_name=lead['contact_name'] or 'Cliente',
                inbox_name=lead['inbox_name'] or 'Equipe',
                tipo_remarketing=tipo_remarketing,
                tempo_inativo_horas=lead['horas_inativo']
            )

            # Salvar no banco
            save_analysis_to_db(
                local_engine=local_engine,
                conversation_id=lead['conversation_id'],
                resultado=resultado
            )

            analyzed_count += 1
            total_tokens += resultado['metadados_analise_ia']['tokens_total']
            total_cost_brl += resultado['metadados_analise_ia']['custo_brl']

            logger.info(
                f"✅ Lead #{lead['display_id']} analisado: "
                f"{resultado['tipo_conversa']} ({lead['horas_inativo']:.1f}h inativo) | "
                f"Score: {resultado['score_prioridade']}"
            )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"❌ Erro ao analisar lead #{lead['display_id']}: {str(e)}"
            )

    # Log estatísticas
    logger.info("-" * 80)
    logger.info(
        f"ANÁLISE CONCLUÍDA: {analyzed_count} sucesso, {failed_count} falhas | "
        f"Tokens: {total_tokens} | Custo: R$ {total_cost_brl:.4f}"
    )

    return {
        'analyzed_count': analyzed_count,
        'failed_count': failed_count,
        'total_tokens': total_tokens,
        'total_cost_brl': total_cost_brl
    }


def save_analysis_to_db(
    local_engine: Engine,
    conversation_id: int,
    resultado: Dict[str, Any]
) -> None:
    """
    Salva resultado da análise no banco de dados.

    Args:
        local_engine: Engine do banco local
        conversation_id: ID da conversa
        resultado: Dicionário com resultado da análise
    """
    query = text("""
        UPDATE conversations_analytics
        SET
            tipo_conversa = :tipo_conversa,
            analise_ia = :analise_ia,
            sugestao_disparo = :sugestao_disparo,
            score_prioridade = :score_prioridade,
            dados_extraidos_ia = cast(:dados_extraidos_ia as jsonb),
            metadados_analise_ia = cast(:metadados_analise_ia as jsonb),
            analisado_em = :analisado_em
        WHERE conversation_id = :conversation_id
    """)

    with local_engine.connect() as conn:
        conn.execute(query, {
            'conversation_id': conversation_id,
            'tipo_conversa': resultado['tipo_conversa'],
            'analise_ia': resultado['analise_ia'],
            'sugestao_disparo': resultado['sugestao_disparo'],
            'score_prioridade': resultado['score_prioridade'],
            'dados_extraidos_ia': json.dumps(resultado['dados_extraidos_ia'], cls=DecimalEncoder),
            'metadados_analise_ia': json.dumps(resultado['metadados_analise_ia'], cls=DecimalEncoder),
            'analisado_em': resultado['analisado_em']
        })
        conn.commit()
