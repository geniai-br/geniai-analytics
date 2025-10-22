"""
Dashboard Principal - Analytics GenIAI
AllpFit Bot Performance Analytics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Imports locais
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import configure_page, THEME, format_number, format_percentage, format_phone, format_datetime, format_date_pt, format_conversation_readable
from utils.db_connector import get_all_conversations, get_conversations_today, clear_cache, get_engine
from utils.metrics import (
    calculate_total_contacts,
    calculate_ai_conversations,
    calculate_human_conversations,
    calculate_visits_scheduled,
    calculate_daily_metrics,
    calculate_leads_by_day,
    calculate_distribution_by_period,
    get_leads_table_data,
    get_leads_not_converted,
    get_leads_with_ai_analysis
)

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

configure_page()

# ============================================================================
# CABEÇALHO
# ============================================================================

# Inicializar session state para filtros
if 'date_start' not in st.session_state:
    st.session_state.date_start = None
if 'date_end' not in st.session_state:
    st.session_state.date_end = None

# Header com título e filtros no canto direito
col_title, col_spacer, col_date_start, col_date_end, col_refresh = st.columns([5, 1.5, 1, 1, 0.5])

with col_title:
    st.markdown("""
        <h1 style='color: white; letter-spacing: 1px; margin-top: 0; margin-bottom: 0.5rem; font-size: 1.5rem;'>
            ANALYTICS GENIAI - OVERVIEW
        </h1>
    """, unsafe_allow_html=True)

with col_date_start:
    date_start = st.date_input(
        "Início",
        value=st.session_state.date_start,
        format="DD/MM/YYYY",
        key="filter_date_start"
    )
    st.session_state.date_start = date_start

with col_date_end:
    date_end = st.date_input(
        "Fim",
        value=st.session_state.date_end,
        format="DD/MM/YYYY",
        key="filter_date_end"
    )
    st.session_state.date_end = date_end

with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️", help="Limpar filtros"):
        st.session_state.date_start = None
        st.session_state.date_end = None
        clear_cache()
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================================
# CARREGAR DADOS
# ============================================================================

@st.cache_data(ttl=300)
def load_data():
    """Carrega dados do banco"""
    return get_all_conversations()

# Carregar todos os dados
df_all = load_data()

# Aplicar filtro de período (Data Início e Data Fim)
df = df_all.copy()

if date_start is not None:
    df = df[df['conversation_date'] >= date_start]

if date_end is not None:
    df = df[df['conversation_date'] <= date_end]

if df.empty:
    st.error("❌ Nenhum dado encontrado no banco de dados")
    st.stop()

total_conversas = len(df)
total_conversas_banco = len(df_all)

# Mostrar indicador de filtro
if total_conversas < total_conversas_banco:
    filter_text = []
    if date_start:
        filter_text.append(f"a partir de {date_start.strftime('%d/%m/%Y')}")
    if date_end:
        filter_text.append(f"até {date_end.strftime('%d/%m/%Y')}")

    filter_display = " ".join(filter_text) if filter_text else "ativo"
    st.info(f"🔍 Mostrando **{total_conversas:,}** de **{total_conversas_banco:,}** conversas ({filter_display})")
    st.markdown("<br>", unsafe_allow_html=True)

# ============================================================================
# SEÇÃO 1: KPIs PRINCIPAIS (6 CARDS)
# ============================================================================

# Calcular métricas
total_contatos = calculate_total_contacts(df)
conversas_ai = calculate_ai_conversations(df)
conversas_humano = calculate_human_conversations(df)
visitas_agendadas = calculate_visits_scheduled(df)

# TODO: Integrar com CRM
vendas_trafego = 0  # Vendas que passaram pelo bot
vendas_geral = 0    # Total de vendas no CRM

# Calcular percentuais
perc_contatos = format_percentage(total_contatos, total_conversas)
perc_ai = format_percentage(conversas_ai, total_conversas)
perc_humano = format_percentage(conversas_humano, total_conversas)
perc_visitas = format_percentage(visitas_agendadas, total_conversas)
perc_trafego = format_percentage(vendas_trafego, total_conversas) if vendas_geral > 0 else "0%"
perc_geral = "N/A"  # Vendas gerais não tem percentual em relação a conversas

# Exibir cards
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        label="Total Contatos",
        value=format_number(total_contatos),
        delta=perc_contatos
    )

with col2:
    st.metric(
        label="Total conversas Agente AI",
        value=format_number(conversas_ai),
        delta=perc_ai
    )

with col3:
    st.metric(
        label="Humano",
        value=format_number(conversas_humano),
        delta=perc_humano
    )

with col4:
    st.metric(
        label="Visitas agendadas",
        value=format_number(visitas_agendadas),
        delta=perc_visitas
    )

with col5:
    st.metric(
        label="Vendas/Tráfego",
        value=format_number(vendas_trafego),
        delta=perc_trafego,
        help="Vendas do CRM que passaram pelo bot (requer integração CRM)"
    )

with col6:
    st.metric(
        label="Vendas/Geral",
        value=format_number(vendas_geral),
        delta=perc_geral,
        help="Total de vendas no CRM no período (requer integração CRM)"
    )

# ============================================================================
# SEÇÃO 2: RESULTADO DIÁRIO
# ============================================================================

st.markdown("<hr style='border: 1px dashed #262B3D; margin: 0.8rem 0;'>", unsafe_allow_html=True)

st.markdown("""
    <h3 style='text-align: center; color: white; margin-bottom: 0.5rem; margin-top: 0; font-size: 1rem;'>
        RESULTADO DIÁRIO
    </h3>
""", unsafe_allow_html=True)

# Calcular métricas diárias
daily_metrics = calculate_daily_metrics(df_all)  # Usar df_all para capturar conversas reabertas

# Layout com todos os KPIs lado a lado
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        label="Novos Leads",
        value=format_number(daily_metrics['novos_leads']),
        delta=f"{daily_metrics['novos_leads_perc']} vs ontem"
    )

with col2:
    st.metric(
        label="Visitas Dia",
        value=format_number(daily_metrics['visitas_dia'])
    )

with col3:
    st.metric(
        label="Vendas Dia",
        value=format_number(daily_metrics['vendas_dia'])
    )

with col4:
    st.metric(
        label="Total Conversas Dia",
        value=format_number(daily_metrics['total_conversas_dia']),
        delta=f"{daily_metrics['total_conversas_dia_perc']} vs ontem"
    )

with col5:
    st.metric(
        label="Novas Conversas",
        value=format_number(daily_metrics['conversas_dia']),
        delta=f"{daily_metrics['conversas_dia_perc']} vs ontem"
    )

with col6:
    st.metric(
        label="Conversas Reabertas",
        value=format_number(daily_metrics['conversas_reabertas']),
        delta=f"{daily_metrics['conversas_reabertas_perc']} vs ontem"
    )

st.markdown("<hr style='margin-top: 0.8rem;'>", unsafe_allow_html=True)

# ============================================================================
# SEÇÃO 3: GRÁFICOS
# ============================================================================

col_graph1, col_graph2 = st.columns([1, 1])

# GRÁFICO 1: Média Leads por Dia
with col_graph1:
    st.markdown("### MÉDIA LEADS POR DIA")

    leads_by_day = calculate_leads_by_day(df, days=30)

    if not leads_by_day.empty:
        # Formatar datas em português
        leads_by_day['data_pt'] = leads_by_day['data'].apply(format_date_pt)

        # Calcular média
        media = leads_by_day['leads'].mean()

        fig = go.Figure()

        # Adicionar barras
        fig.add_trace(go.Bar(
            x=leads_by_day['data_pt'],
            y=leads_by_day['leads'],
            name='Leads',
            marker=dict(color=THEME['primary']),
            text=leads_by_day['leads'],
            textposition='outside',
            textfont=dict(color='white', size=12)
        ))

        # Adicionar linha de média
        fig.add_trace(go.Scatter(
            x=leads_by_day['data_pt'],
            y=[media] * len(leads_by_day),
            mode='lines',
            name=f'Média: {media:.1f}',
            line=dict(color=THEME['secondary'], width=2, dash='dash'),
            showlegend=True
        ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis=dict(
                showgrid=False,
                title=None,
                tickangle=-45
            ),
            yaxis=dict(
                showgrid=False,
                title=None
            ),
            margin=dict(l=20, r=20, t=20, b=60),
            height=250,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.1,
                xanchor="center",
                x=0.5,
                font=dict(color='white')
            )
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para exibir")

# GRÁFICO 2: Distribuição por Período do Dia
with col_graph2:
    st.markdown("### Distribuição por Período do Dia")

    distribution = calculate_distribution_by_period(df)

    if not distribution.empty:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=distribution['periodo'],
            y=distribution['quantidade'],
            marker=dict(color=THEME['secondary']),
            text=distribution['quantidade'],
            textposition='outside',
            textfont=dict(color='white')
        ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis=dict(
                showgrid=False,
                title=None
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                title=None
            ),
            margin=dict(l=20, r=20, t=20, b=20),
            height=250
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para exibir")

st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================================
# SEÇÃO 4: LEADS NÃO CONVERTIDOS COM ANÁLISE DE IA
# ============================================================================

st.markdown("### 🎯 Leads não convertidos com análise de IA")

# Buscar leads com análise de IA
engine = get_engine()
df_ai_leads = get_leads_with_ai_analysis(engine, limit=50)

if not df_ai_leads.empty:
    st.info(f"📊 Total de leads analisados: **{len(df_ai_leads)}** (priorizados por probabilidade de conversão)")

    # Formatar datas
    df_ai_leads['Data Primeiro Contato'] = df_ai_leads['Data Primeiro Contato'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else "-"
    )
    df_ai_leads['Data Última Conversa'] = df_ai_leads['Data Última Conversa'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else "-"
    )
    df_ai_leads['Data Atualização Tel'] = df_ai_leads['Data Atualização Tel'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else "-"
    )

    # Formatar celular
    df_ai_leads['Celular'] = df_ai_leads['Celular'].apply(format_phone)

    # Formatar conversa compilada em formato legível de chat
    df_ai_leads['Conversa Compilada'] = df_ai_leads.apply(
        lambda row: format_conversation_readable(row['Conversa Compilada'], row['Nome']),
        axis=1
    )

    # Adicionar emoji na probabilidade
    def format_probabilidade(prob):
        if prob >= 4:
            return f"🔥 {prob}/5"
        elif prob >= 3:
            return f"⭐ {prob}/5"
        elif prob >= 2:
            return f"💡 {prob}/5"
        else:
            return f"📊 {prob}/5"

    df_ai_leads['Probabilidade'] = df_ai_leads['Probabilidade'].apply(format_probabilidade)

    # Exibir tabela
    st.dataframe(
        df_ai_leads,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "Conversa Compilada": st.column_config.TextColumn(
                "Conversa Compilada",
                width="large",
                help="Conversa completa formatada como chat"
            ),
            "Análise IA": st.column_config.TextColumn(
                "Análise IA",
                width="medium"
            ),
            "Sugestão de Disparo": st.column_config.TextColumn(
                "Sugestão de Disparo",
                width="large"
            ),
            "Probabilidade": st.column_config.TextColumn(
                "Probabilidade",
                width="small"
            )
        }
    )
else:
    st.success("✅ Nenhum lead não convertido para analisar!")

# ============================================================================
# RODAPÉ
# ============================================================================

st.markdown("<hr>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(f"""
        <p style='text-align: center; color: {THEME["text_muted"]}; font-size: 0.85rem;'>
            Dashboard atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
            Total de conversas no banco: {total_conversas:,}
        </p>
    """, unsafe_allow_html=True)
