"""
FUNÇÕES ARQUIVADAS - MÉTRICAS DE QUALIDADE
Data: 2025-11-11
Motivo: Removidas do dashboard multi-tenant por decisão de simplificação

Estas funções são genéricas (aplicáveis a todos os tenants), mas foram removidas
para simplificar o dashboard e focar nas métricas principais de leads/conversão.

Preservado para referência futura e possível reativação.
"""

import streamlit as st
import pandas as pd


def render_quality_metrics(metrics, df):
    """
    Renderiza métricas de qualidade (IA%, Resolução%, Tempo Resposta)
    [FASE 5.5 - REMOVIDA EM 2025-11-11]

    Args:
        metrics: Dict com métricas calculadas
        df: DataFrame com conversas
    """
    st.divider()
    st.subheader("⚙️ Métricas de Qualidade")

    col1, col2, col3, col4 = st.columns(4)

    total = len(df) if not df.empty else 1

    with col1:
        pct_ai = (metrics['ai_conversations'] / total * 100) if total > 0 else 0
        st.metric(
            "Conversas IA %",
            f"{pct_ai:.1f}%",
            help="Percentual de conversas 100% automáticas (sem intervenção humana)"
        )

    with col2:
        st.metric(
            "Taxa Resolução",
            f"{metrics['resolution_rate']:.1f}%",
            help="Percentual de conversas resolvidas"
        )

    with col3:
        # Converter minutos para horas se > 60
        avg_time = metrics['avg_response_time']
        if avg_time >= 60:
            time_display = f"{avg_time/60:.1f}h"
        else:
            time_display = f"{avg_time:.0f}min"

        st.metric(
            "Tempo Resposta",
            time_display,
            help="Tempo médio da primeira resposta"
        )

    with col4:
        # Engagement = taxa de retorno (contatos únicos vs total de conversas)
        # Quanto menor que 100%, mais contatos retornam (mais engagement)
        # 100% = cada contato teve apenas 1 conversa
        # <100% = contatos retornam (bom engagement)
        pct_engagement = (metrics['unique_contacts'] / total * 100) if total > 0 else 0

        # Calcular taxa de retorno (inverso do engagement)
        return_rate = 100 - pct_engagement

        st.metric(
            "Taxa Retorno",
            f"{return_rate:.1f}%",
            help="Percentual de conversas de contatos que retornaram (quanto maior, melhor o engagement)"
        )


# ============================================================================
# CÁLCULOS NECESSÁRIOS (mantidos para referência)
# ============================================================================

def calculate_quality_metrics_archived(df):
    """
    Calcula métricas de qualidade (usado pela função acima)

    NOTA: Esta lógica foi integrada em calculate_metrics() no dashboard principal

    Args:
        df: DataFrame com conversas

    Returns:
        dict: Métricas de qualidade
    """
    if df.empty:
        return {
            'ai_conversations': 0,
            'unique_contacts': 0,
            'resolution_rate': 0.0,
            'avg_response_time': 0.0,
        }

    total = len(df)

    # Contar contatos únicos
    unique_contacts = df['contact_name'].nunique() if 'contact_name' in df.columns else total

    # Conversas IA (sem intervenção humana)
    ai_conversations = len(df[df['has_human_intervention'] == False]) if 'has_human_intervention' in df.columns else len(df[df['bot_messages'] > 0])

    # Taxa de resolução
    if 'is_resolved' in df.columns:
        resolved_count = len(df[df['is_resolved'] == True])
        resolution_rate = (resolved_count / total * 100) if total > 0 else 0.0
    else:
        resolution_rate = 0.0

    # Tempo resposta médio (em minutos)
    if 'first_response_time_minutes' in df.columns:
        valid_times = df[df['first_response_time_minutes'].notna()]['first_response_time_minutes']
        avg_response_time = valid_times.mean() if len(valid_times) > 0 else 0.0
    else:
        avg_response_time = 0.0

    return {
        'ai_conversations': ai_conversations,
        'unique_contacts': unique_contacts,
        'resolution_rate': resolution_rate,
        'avg_response_time': avg_response_time,
    }