"""
FUNÇÕES ARQUIVADAS - ESPECÍFICAS ALLPFIT
Data: 2025-11-11
Motivo: Pós-apresentação aos superiores, removidas do dashboard multi-tenant

Estas funções eram específicas para o segmento fitness (AllpFit) e não se aplicam
a outros segmentos (educação, financeiro, etc.).

Preservado para referência futura e possível reativação para AllpFit.
"""

import streamlit as st
import pandas as pd
from app.config import format_number


# ============================================================================
# FUNIL DE CONVERSÃO - ALLPFIT ESPECÍFICO
# ============================================================================

def render_conversion_funnel_allpfit(metrics):
    """
    Renderiza funil de conversão AllpFit: Leads → Visitas → CRM

    ESPECÍFICO ALLPFIT: Este funil representa o processo de vendas de academia:
    1. Lead identificado (interesse em treino)
    2. Visita agendada (agendou aula experimental/tour)
    3. Convertido CRM (matriculou-se na academia)

    Não aplicável a outros segmentos:
    - Educação: Lead → Matrícula (sem visita física)
    - Financeiro: Lead → Proposta → Contratação
    - E-commerce: Lead → Carrinho → Compra

    Args:
        metrics: Dict com métricas calculadas
    """
    st.divider()
    st.subheader("🎯 Funil de Conversão")

    col1, col2, col3 = st.columns(3)

    # Calcular taxas do funil
    lead_to_visit_rate = 0
    visit_to_crm_rate = 0

    if metrics['leads'] > 0:
        lead_to_visit_rate = (metrics['visits_scheduled'] / metrics['leads']) * 100

    if metrics['visits_scheduled'] > 0:
        visit_to_crm_rate = (metrics['crm_converted'] / metrics['visits_scheduled']) * 100

    with col1:
        st.metric(
            "Leads Gerados",
            format_number(metrics['leads']),
            help="Total de leads identificados pela IA"
        )

    with col2:
        st.metric(
            "Visitas Agendadas",
            format_number(metrics['visits_scheduled']),
            delta=f"{lead_to_visit_rate:.1f}% dos leads",
            help="Leads que agendaram visita"
        )

    with col3:
        st.metric(
            "Conversões CRM",
            format_number(metrics['crm_converted']),
            delta=f"{visit_to_crm_rate:.1f}% das visitas",
            help="Visitas que converteram em cliente"
        )


# ============================================================================
# FILTROS OPENAI - ALLPFIT ESPECÍFICO
# ============================================================================

def render_allpfit_openai_filters():
    """
    Renderiza filtros OpenAI específicos AllpFit

    ESPECÍFICO ALLPFIT: Filtros baseados em análise IA de condição física e objetivos

    Filtros:
    - Apenas com Análise IA (tem análise_ia preenchida)
    - Probabilidade Alta (probabilidade_conversao 4-5)
    - Visita Agendada (visit_scheduled = True)
    - Classificação (Alto/Médio/Baixo)

    Returns:
        tuple: (filter_openai, filter_high_prob, filter_visit, filter_classification)
    """
    st.markdown("#### 🤖 Filtros OpenAI")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filter_openai = st.checkbox("Apenas com Análise IA", value=False, key="filter_openai")

    with col2:
        filter_high_prob = st.checkbox("Probabilidade Alta (4-5)", value=False, key="filter_high_prob")

    with col3:
        filter_visit = st.checkbox("Visita Agendada", value=False, key="filter_visit")

    with col4:
        filter_classification = st.selectbox(
            "Classificação",
            ["Todas", "Alto", "Médio", "Baixo"],
            key="filter_classification"
        )

    return filter_openai, filter_high_prob, filter_visit, filter_classification


def apply_allpfit_openai_filters(df, filter_openai, filter_high_prob, filter_visit, filter_classification):
    """
    Aplica filtros OpenAI específicos AllpFit ao DataFrame

    Args:
        df: DataFrame com conversas
        filter_openai: Boolean - filtrar apenas com análise IA
        filter_high_prob: Boolean - filtrar probabilidade alta (4-5)
        filter_visit: Boolean - filtrar visita agendada
        filter_classification: String - classificação ("Todas", "Alto", "Médio", "Baixo")

    Returns:
        pd.DataFrame: DataFrame filtrado
    """
    df_filtered = df.copy()

    if filter_openai:
        # Filtrar apenas conversas com análise IA
        df_filtered = df_filtered[
            (df_filtered['analise_ia'].notna()) &
            (df_filtered['analise_ia'] != '') &
            (df_filtered['analise_ia'].str.len() > 10)
        ]

    if filter_high_prob:
        # Filtrar apenas leads com probabilidade 4 ou 5
        df_filtered = df_filtered[
            (df_filtered['probabilidade_conversao'].notna()) &
            (df_filtered['probabilidade_conversao'] >= 4)
        ]

    if filter_visit:
        # Filtrar apenas leads com visita agendada
        df_filtered = df_filtered[df_filtered['visit_scheduled'] == True]

    if filter_classification != "Todas":
        # Filtrar por classificação IA
        df_filtered = df_filtered[df_filtered['ai_probability_label'] == filter_classification]

    return df_filtered


# ============================================================================
# MODAL DE ANÁLISE IA - ALLPFIT ESPECÍFICO
# ============================================================================

def render_allpfit_ai_analysis_modal(leads_df):
    """
    Renderiza modal com análise IA detalhada AllpFit

    ESPECÍFICO ALLPFIT: Exibe:
    - condicao_fisica (Sedentário, Ativo, Atleta, etc.)
    - objetivo (Emagrecimento, Ganho de massa, Condicionamento, etc.)
    - analise_ia (texto longo gerado por GPT-4o-mini)
    - sugestao_disparo (mensagem personalizada para enviar ao lead)
    - probabilidade_conversao (0-5)

    Args:
        leads_df: DataFrame com leads (deve conter colunas OpenAI)
    """
    st.divider()
    st.caption("💡 **Ver Análise IA Detalhada:** Selecione um lead abaixo para visualizar análise e sugestão de disparo")

    # Filtrar leads com análise IA disponível
    leads_with_ai = leads_df[
        (leads_df['analise_ia'].notna()) &
        (leads_df['analise_ia'] != '') &
        (leads_df['analise_ia'].str.len() > 10)
    ].copy()

    if not leads_with_ai.empty:
        # Criar lista de opções para o selectbox
        lead_options = ["Selecione um lead..."] + [
            f"{row['contact_name']} ({row['contact_phone']}) - {row['conversation_date']}"
            for _, row in leads_with_ai.iterrows()
        ]

        selected_lead_idx = st.selectbox(
            "🔍 Selecionar Lead para Ver Análise",
            range(len(lead_options)),
            format_func=lambda x: lead_options[x],
            key="selected_lead_modal"
        )

        # Se selecionou um lead (não o placeholder)
        if selected_lead_idx > 0:
            # Pegar dados do lead selecionado (índice -1 porque o primeiro é placeholder)
            lead_data = leads_with_ai.iloc[selected_lead_idx - 1]

            # Exibir modal com análise detalhada
            with st.container():
                st.markdown("---")
                st.markdown("### 🤖 Análise IA Detalhada")

                # Informações do lead
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"**Nome:** {lead_data['contact_name']}")
                    st.markdown(f"**Nome IA:** {lead_data['nome_mapeado_bot'] if pd.notna(lead_data['nome_mapeado_bot']) and lead_data['nome_mapeado_bot'] != '' else 'N/A'}")

                with col2:
                    st.markdown(f"**Telefone:** {lead_data['contact_phone']}")
                    st.markdown(f"**Data:** {lead_data['conversation_date']}")

                with col3:
                    prob_0_5 = lead_data['probabilidade_conversao'] if pd.notna(lead_data['probabilidade_conversao']) else 0
                    score = lead_data['ai_probability_score'] if pd.notna(lead_data['ai_probability_score']) else 0
                    label = lead_data['ai_probability_label'] if pd.notna(lead_data['ai_probability_label']) else 'N/A'
                    st.markdown(f"**Probabilidade:** {prob_0_5}/5 ({score:.0f}%)")
                    st.markdown(f"**Classificação:** {label}")

                # Detalhes OpenAI
                col1, col2 = st.columns(2)

                with col1:
                    condicao = lead_data['condicao_fisica'] if pd.notna(lead_data['condicao_fisica']) and lead_data['condicao_fisica'] != 'Não mencionado' else 'N/A'
                    st.markdown(f"**Condição Física:** {condicao}")

                with col2:
                    objetivo = lead_data['objetivo'] if pd.notna(lead_data['objetivo']) and lead_data['objetivo'] != 'Não mencionado' else 'N/A'
                    st.markdown(f"**Objetivo:** {objetivo}")

                st.markdown("---")

                # Análise IA (em expander para economizar espaço)
                with st.expander("📄 **Análise IA Completa**", expanded=True):
                    analise = lead_data['analise_ia']
                    if pd.notna(analise) and analise != '':
                        st.markdown(analise)
                    else:
                        st.info("Análise não disponível")

                # Sugestão de disparo (destacado)
                st.markdown("#### 📨 Sugestão de Disparo")
                sugestao = lead_data['sugestao_disparo']
                if pd.notna(sugestao) and sugestao != '':
                    st.success(sugestao)

                    # Botão para copiar sugestão
                    if st.button("📋 Copiar Sugestão", key="copy_suggestion"):
                        st.toast("✅ Sugestão copiada! (use Ctrl+C para copiar o texto acima)", icon="✅")
                else:
                    st.info("Sugestão não disponível")

                st.markdown("---")
    else:
        st.info("ℹ️ Nenhum lead com análise IA disponível ainda. Execute o ETL OpenAI para gerar análises.")


# ============================================================================
# COLUNAS DA TABELA - ALLPFIT ESPECÍFICO
# ============================================================================

def get_allpfit_table_columns():
    """
    Retorna lista de colunas para tabela de leads AllpFit

    ESPECÍFICO ALLPFIT: Inclui:
    - nome_mapeado_bot
    - condicao_fisica
    - objetivo
    - probabilidade_conversao (0-5)

    Returns:
        tuple: (column_list, column_names)
    """
    columns = [
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'conversation_date',
        'is_lead',
        'visit_scheduled',
        'crm_converted',
        'ai_probability_label',
        'ai_probability_score',
        'nome_mapeado_bot',
        'condicao_fisica',
        'objetivo',
        'probabilidade_conversao'
    ]

    column_names = [
        'ID',
        'Nome',
        'Telefone',
        'Data',
        'Lead',
        'Visita',
        'CRM',
        'Classificação IA',
        'Score IA',
        'Nome IA',
        'Condição',
        'Objetivo',
        'Prob (0-5)'
    ]

    return columns, column_names


# ============================================================================
# NOTAS DE IMPLEMENTAÇÃO
# ============================================================================

"""
COMO REATIVAR PARA ALLPFIT:

1. No client_dashboard.py, adicionar colunas OpenAI na query:
   - condicao_fisica
   - objetivo
   - analise_ia
   - sugestao_disparo
   - probabilidade_conversao

2. Importar funções deste arquivo:
   from multi_tenant.dashboards._archived.allpfit_specific_functions import (
       render_conversion_funnel_allpfit,
       render_allpfit_openai_filters,
       apply_allpfit_openai_filters,
       render_allpfit_ai_analysis_modal
   )

3. Adicionar chamadas nos locais apropriados:
   - Após render_kpis(): render_conversion_funnel_allpfit(metrics)
   - Após filtros de data: filtros = render_allpfit_openai_filters()
   - Após carregar df: df = apply_allpfit_openai_filters(df, *filtros)
   - Após tabela de leads: render_allpfit_ai_analysis_modal(df)

CUSTO ESTIMADO (AllpFit, 1.317 conversas):
- R$ 29,55 total
- ~R$ 0,022 por conversa
- 742 conversas analisadas até 2025-11-09
"""