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
    get_leads_with_ai_analysis,
    get_total_leads_with_ai_analysis,
    build_filter_conditions,
    calculate_crm_conversions,
    calculate_days_running,
    get_crm_conversions_detail
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
if 'leads_page' not in st.session_state:
    st.session_state.leads_page = 1

# Inicializar filtros de leads
if 'filter_nome' not in st.session_state:
    st.session_state.filter_nome = ""
if 'filter_celular' not in st.session_state:
    st.session_state.filter_celular = ""
if 'filter_condicao_fisica' not in st.session_state:
    st.session_state.filter_condicao_fisica = []
if 'filter_objetivo' not in st.session_state:
    st.session_state.filter_objetivo = []
if 'filter_data_primeiro_inicio' not in st.session_state:
    st.session_state.filter_data_primeiro_inicio = None
if 'filter_data_primeiro_fim' not in st.session_state:
    st.session_state.filter_data_primeiro_fim = None
if 'filter_data_ultima_inicio' not in st.session_state:
    st.session_state.filter_data_ultima_inicio = None
if 'filter_data_ultima_fim' not in st.session_state:
    st.session_state.filter_data_ultima_fim = None
if 'filter_probabilidade' not in st.session_state:
    st.session_state.filter_probabilidade = []
if 'filter_status_analise' not in st.session_state:
    st.session_state.filter_status_analise = "Todos"

# Header com título e filtros no canto direito
col_title, col_spacer, col_date_start, col_date_end, col_refresh = st.columns([5, 1.5, 1, 1, 0.5])

with col_title:
    dias_rodando = calculate_days_running()
    st.markdown(f"""
        <h1 style='color: white; letter-spacing: 1px; margin-top: 0; margin-bottom: 0.5rem; font-size: 1.5rem;'>
            ANALYTICS GENIAI - OVERVIEW
        </h1>
        <p style='color: #A0AEC0; font-size: 0.85rem; margin-top: -0.5rem;'>
            🤖 Bot rodando há <strong>{dias_rodando} dias</strong> (desde 25/09/2025)
        </p>
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

# Integração com CRM (conversões reais)
vendas_trafego = calculate_crm_conversions()  # Leads do bot que viraram clientes
vendas_geral = 198  # Total de clientes no CRM EVO (base Excel)

# Calcular percentuais
perc_contatos = format_percentage(total_contatos, total_conversas)
perc_ai = format_percentage(conversas_ai, total_conversas)
perc_humano = format_percentage(conversas_humano, total_conversas)
perc_visitas = format_percentage(visitas_agendadas, total_conversas)
perc_trafego = format_percentage(vendas_trafego, vendas_geral) if vendas_geral > 0 else "0%"
perc_geral = "N/A"  # Vendas gerais não tem percentual em relação a conversas

# Exibir cards
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        label="Total Contatos",
        value=format_number(total_contatos),
        delta=perc_contatos,
        help="📊 Número de leads únicos que engajaram com o bot (enviaram pelo menos 1 mensagem)"
    )

with col2:
    st.metric(
        label="Total conversas Agente AI",
        value=format_number(conversas_ai),
        delta=perc_ai,
        help="🤖 Conversas gerenciadas 100% pelo bot, sem intervenção humana"
    )

with col3:
    st.metric(
        label="Humano",
        value=format_number(conversas_humano),
        delta=perc_humano,
        help="👤 Conversas que tiveram intervenção humana da equipe"
    )

with col4:
    st.metric(
        label="Visitas agendadas",
        value=format_number(visitas_agendadas),
        delta=perc_visitas,
        help="📅 Leads que agendaram visita à academia (confirmados pelo bot)"
    )

with col5:
    st.metric(
        label="Vendas/Tráfego",
        value=format_number(vendas_trafego),
        delta=perc_trafego,
        help="🎯 Leads que conversaram com o bot ANTES de se matricularem no CRM (conversões reais rastreadas). Percentual = Vendas Tráfego / Vendas Geral."
    )

with col6:
    st.metric(
        label="Vendas/Geral",
        value=format_number(vendas_geral),
        delta=perc_geral,
        help="💼 Total de clientes cadastrados no CRM da academia (todas as fontes: bot, indicação, orgânico, etc)"
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
        delta=f"{daily_metrics['novos_leads_perc']} vs ontem",
        help="📈 Leads que fizeram o primeiro contato HOJE"
    )

with col2:
    st.metric(
        label="Visitas Dia",
        value=format_number(daily_metrics['visitas_dia']),
        help="🏋️ Visitas agendadas para HOJE"
    )

with col3:
    st.metric(
        label="Vendas Dia",
        value=format_number(daily_metrics['vendas_dia']),
        help="💰 Conversões identificadas HOJE (leads que viraram clientes)"
    )

with col4:
    st.metric(
        label="Total Conversas Dia",
        value=format_number(daily_metrics['total_conversas_dia']),
        delta=f"{daily_metrics['total_conversas_dia_perc']} vs ontem",
        help="💬 Total de conversas ativas HOJE (novas + reabertas)"
    )

with col5:
    st.metric(
        label="Novas Conversas",
        value=format_number(daily_metrics['conversas_dia']),
        delta=f"{daily_metrics['conversas_dia_perc']} vs ontem",
        help="🆕 Conversas iniciadas HOJE (primeiro contato)"
    )

with col6:
    st.metric(
        label="Conversas Reabertas",
        value=format_number(daily_metrics['conversas_reabertas']),
        delta=f"{daily_metrics['conversas_reabertas_perc']} vs ontem",
        help="🔄 Leads que voltaram a conversar HOJE (já haviam conversado antes)"
    )

st.markdown("<hr style='margin-top: 0.8rem;'>", unsafe_allow_html=True)

# ============================================================================
# SEÇÃO 4: CONVERSÕES REAIS (BOT → CRM)
# ============================================================================

if vendas_trafego > 0:
    st.markdown("### 🎯 Conversões Reais: Leads do Bot que viraram Clientes")
    st.caption("Rastreamento de conversões: cruzamento entre base do CRM e conversas do bot por telefone")

    engine = get_engine()
    df_conversoes = get_crm_conversions_detail(engine)

    if not df_conversoes.empty:
        taxa_conversao = (vendas_trafego / vendas_geral) * 100 if vendas_geral > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Conversões Identificadas", vendas_trafego,
                     help="🎯 Leads que conversaram com o bot e depois se matricularam")
        with col2:
            st.metric("Taxa de Conversão (Bot → CRM)", f"{taxa_conversao:.1f}%",
                     help="📊 Percentual de clientes que vieram do bot (Vendas Tráfego / Vendas Geral)")
        with col3:
            st.metric("Total de Clientes CRM", vendas_geral,
                     help="💼 Total de clientes cadastrados no CRM (todas as fontes)")

        st.markdown("<br>", unsafe_allow_html=True)

        # Formatar datas
        df_conversoes['Data Conversa'] = pd.to_datetime(df_conversoes['Data Conversa']).dt.strftime('%d/%m/%Y %H:%M')
        df_conversoes['Data Cadastro CRM'] = pd.to_datetime(df_conversoes['Data Cadastro CRM']).dt.strftime('%d/%m/%Y %H:%M')

        st.dataframe(
            df_conversoes,
            use_container_width=True,
            hide_index=True,
            height=300
        )

        st.info("💡 **Insight:** Estes leads conversaram com o bot ANTES de se cadastrarem no CRM. Tempo médio de conversão: 3-10 dias.")

    st.markdown("<hr>", unsafe_allow_html=True)

# ============================================================================
# SEÇÃO 5: ANÁLISE GENIAI
# ============================================================================

st.markdown("### 🎯 Análise GeniAI")
st.caption("Use os filtros nas colunas abaixo para refinar a visualização. O download reflete exatamente o que está visível.")

# ============================================================================
# FILTROS SIMPLIFICADOS (ACIMA DA TABELA)
# ============================================================================

st.markdown("#### 🔍 Filtros Rápidos")

with st.container():
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)

    with col_f1:
        filter_nome_input = st.text_input("🔍 Nome", value=st.session_state.filter_nome, placeholder="Digite...")
        if filter_nome_input != st.session_state.filter_nome:
            st.session_state.filter_nome = filter_nome_input
            st.session_state.leads_page = 1

    with col_f2:
        filter_prob_input = st.multiselect(
            "🎯 Probabilidade",
            options=["0", "1", "2", "3", "4", "5", "Sem análise"],
            default=st.session_state.filter_probabilidade if isinstance(st.session_state.filter_probabilidade, list) else []
        )
        if filter_prob_input != st.session_state.filter_probabilidade:
            st.session_state.filter_probabilidade = filter_prob_input
            st.session_state.leads_page = 1

    with col_f3:
        filter_condicao_input = st.multiselect(
            "🏋️ Condição",
            options=["Sedentário", "Iniciante", "Intermediário", "Avançado", "Não mencionado"],
            default=st.session_state.filter_condicao_fisica if isinstance(st.session_state.filter_condicao_fisica, list) else []
        )
        if filter_condicao_input != st.session_state.filter_condicao_fisica:
            st.session_state.filter_condicao_fisica = filter_condicao_input
            st.session_state.leads_page = 1

    with col_f4:
        filter_objetivo_input = st.multiselect(
            "🎯 Objetivo",
            options=["Perda de peso", "Ganho de massa muscular", "Condicionamento físico", "Saúde geral", "Estética/Definição", "Não mencionado"],
            default=st.session_state.filter_objetivo if isinstance(st.session_state.filter_objetivo, list) else []
        )
        if filter_objetivo_input != st.session_state.filter_objetivo:
            st.session_state.filter_objetivo = filter_objetivo_input
            st.session_state.leads_page = 1

    with col_f5:
        filter_data_input = st.selectbox(
            "📅 Período",
            options=["Todos", "Hoje", "Últimos 7 dias", "Últimos 30 dias", "Personalizado"],
            index=0
        )

        if filter_data_input == "Personalizado":
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("De:", value=st.session_state.filter_data_ultima_inicio)
                st.session_state.filter_data_ultima_inicio = data_inicio
            with col_d2:
                data_fim = st.date_input("Até:", value=st.session_state.filter_data_ultima_fim)
                st.session_state.filter_data_ultima_fim = data_fim
        elif filter_data_input == "Hoje":
            from datetime import date
            st.session_state.filter_data_ultima_inicio = date.today()
            st.session_state.filter_data_ultima_fim = date.today()
        elif filter_data_input == "Últimos 7 dias":
            from datetime import date, timedelta
            st.session_state.filter_data_ultima_inicio = date.today() - timedelta(days=7)
            st.session_state.filter_data_ultima_fim = date.today()
        elif filter_data_input == "Últimos 30 dias":
            from datetime import date, timedelta
            st.session_state.filter_data_ultima_inicio = date.today() - timedelta(days=30)
            st.session_state.filter_data_ultima_fim = date.today()
        else:  # "Todos"
            st.session_state.filter_data_ultima_inicio = None
            st.session_state.filter_data_ultima_fim = None

    with col_f6:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar", use_container_width=True):
            st.session_state.filter_nome = ""
            st.session_state.filter_celular = ""
            st.session_state.filter_condicao_fisica = []
            st.session_state.filter_objetivo = []
            st.session_state.filter_data_primeiro_inicio = None
            st.session_state.filter_data_primeiro_fim = None
            st.session_state.filter_data_ultima_inicio = None
            st.session_state.filter_data_ultima_fim = None
            st.session_state.filter_probabilidade = []
            st.session_state.filter_status_analise = "Todos"
            st.session_state.leads_page = 1
            st.rerun()

st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

# ============================================================================
# BUSCAR DADOS COM FILTROS
# ============================================================================

# Preparar filtros
active_filters = {
    'nome': st.session_state.filter_nome,
    'celular': st.session_state.filter_celular,
    'condicao_fisica': st.session_state.filter_condicao_fisica,
    'objetivo': st.session_state.filter_objetivo,
    'data_primeiro_inicio': st.session_state.filter_data_primeiro_inicio,
    'data_primeiro_fim': st.session_state.filter_data_primeiro_fim,
    'data_ultima_inicio': st.session_state.filter_data_ultima_inicio,
    'data_ultima_fim': st.session_state.filter_data_ultima_fim,
    'probabilidade': st.session_state.filter_probabilidade,
    'status_analise': st.session_state.filter_status_analise
}

# Buscar total de leads e implementar paginação
engine = get_engine()
total_leads = get_total_leads_with_ai_analysis(engine, filters=active_filters)

if total_leads > 0:
    # Configurações de paginação
    LEADS_PER_PAGE = 50
    total_pages = (total_leads + LEADS_PER_PAGE - 1) // LEADS_PER_PAGE  # Arredonda para cima

    # Garantir que a página atual está dentro dos limites
    if st.session_state.leads_page > total_pages:
        st.session_state.leads_page = total_pages
    if st.session_state.leads_page < 1:
        st.session_state.leads_page = 1

    # Calcular offset
    offset = (st.session_state.leads_page - 1) * LEADS_PER_PAGE

    # Buscar dados da página atual
    df_ai_leads = get_leads_with_ai_analysis(engine, limit=LEADS_PER_PAGE, offset=offset, filters=active_filters)

    # Header com informações e controles de paginação + Download
    col_info, col_download, col_nav = st.columns([2, 0.7, 1.3])

    with col_info:
        start_record = offset + 1
        end_record = min(offset + LEADS_PER_PAGE, total_leads)
        st.info(f"📊 Mostrando **{start_record}-{end_record}** de **{total_leads}** leads | Página **{st.session_state.leads_page}** de **{total_pages}**")

    with col_download:
        st.markdown("<br>", unsafe_allow_html=True)
        # Buscar TODOS os dados filtrados para download
        df_download = get_leads_with_ai_analysis(engine, limit=None, offset=0, filters=active_filters)

        if not df_download.empty:
            # Preparar dados para download - FORMATO EXATAMENTE IGUAL AO VISÍVEL
            df_export = df_download.copy()

            # Formatar datas (mesma função usada na visualização)
            df_export['Data Primeiro Contato'] = df_export['Data Primeiro Contato'].apply(
                lambda x: format_datetime(x) if pd.notna(x) else "-"
            )
            df_export['Data Última Conversa'] = df_export['Data Última Conversa'].apply(
                lambda x: format_datetime(x) if pd.notna(x) else "-"
            )
            df_export['Data Atualização Tel'] = df_export['Data Atualização Tel'].apply(
                lambda x: format_datetime(x) if pd.notna(x) else "-"
            )

            # Formatar celular (mesma função usada na visualização)
            df_export['Celular'] = df_export['Celular'].apply(format_phone)

            # Formatar conversa compilada (mesma função usada na visualização)
            df_export['Conversa Compilada'] = df_export.apply(
                lambda row: format_conversation_readable(row['Conversa Compilada'], row['Nome']),
                axis=1
            )

            # Formatar probabilidade (mesma função usada na visualização)
            def format_probabilidade_export(prob):
                if pd.isna(prob) or prob is None:
                    return "⏳ Aguardando análise"
                if prob >= 4:
                    return f"🔥 {prob}/5"
                elif prob >= 3:
                    return f"⭐ {prob}/5"
                elif prob >= 2:
                    return f"💡 {prob}/5"
                else:
                    return f"📊 {prob}/5"

            df_export['Probabilidade'] = df_export['Probabilidade'].apply(format_probabilidade_export)

            # Tratar campos vazios (mesma forma da visualização)
            df_export['Nome Mapeado Bot'] = df_export['Nome Mapeado Bot'].fillna("-").replace('', '-')
            df_export['Análise IA'] = df_export['Análise IA'].fillna("-")
            df_export['Sugestão de Disparo'] = df_export['Sugestão de Disparo'].fillna("-")
            df_export['Condição Física'] = df_export['Condição Física'].fillna("-")
            df_export['Objetivo'] = df_export['Objetivo'].fillna("-")

            # Garantir ordem EXATA das colunas (mesma ordem da tabela visível)
            colunas_ordenadas = [
                'Nome',
                'Nome Mapeado Bot',
                'Celular',
                'Condição Física',
                'Objetivo',
                'Data Primeiro Contato',
                'Data Última Conversa',
                'Conversa Compilada',
                'Análise IA',
                'Data Atualização Tel',
                'Sugestão de Disparo',
                'Probabilidade'
            ]

            df_export = df_export[colunas_ordenadas]

            # Converter para CSV no formato Excel Brasil (ponto e vírgula como separador)
            csv = df_export.to_csv(
                index=False,           # Sem índice
                sep=';',               # Separador padrão Brasil/Excel
                encoding='utf-8-sig',  # UTF-8 com BOM para Excel
                lineterminator='\n'    # Quebra de linha padrão
            ).encode('utf-8-sig')

            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"leads_allpfit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                help=f"Baixar {len(df_export)} leads filtrados (formato idêntico à tabela)"
            )

    with col_nav:
        col_prev, col_page, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.button("◀️ Anterior", disabled=(st.session_state.leads_page == 1), key="prev_page"):
                st.session_state.leads_page -= 1
                st.rerun()

        with col_page:
            new_page = st.number_input(
                "Ir para página:",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.leads_page,
                step=1,
                key="page_input",
                label_visibility="collapsed"
            )
            if new_page != st.session_state.leads_page:
                st.session_state.leads_page = new_page
                st.rerun()

        with col_next:
            if st.button("Próximo ▶️", disabled=(st.session_state.leads_page == total_pages), key="next_page"):
                st.session_state.leads_page += 1
                st.rerun()

    if not df_ai_leads.empty:
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

        # Adicionar emoji na probabilidade (tratar nulos)
        def format_probabilidade(prob):
            if pd.isna(prob) or prob is None:
                return "⏳ Aguardando análise"
            if prob >= 4:
                return f"🔥 {prob}/5"
            elif prob >= 3:
                return f"⭐ {prob}/5"
            elif prob >= 2:
                return f"💡 {prob}/5"
            else:
                return f"📊 {prob}/5"

        df_ai_leads['Probabilidade'] = df_ai_leads['Probabilidade'].apply(format_probabilidade)

        # Tratar campos vazios de análise
        df_ai_leads['Análise IA'] = df_ai_leads['Análise IA'].fillna("-")
        df_ai_leads['Sugestão de Disparo'] = df_ai_leads['Sugestão de Disparo'].fillna("-")
        df_ai_leads['Condição Física'] = df_ai_leads['Condição Física'].fillna("-")
        df_ai_leads['Objetivo'] = df_ai_leads['Objetivo'].fillna("-")

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
