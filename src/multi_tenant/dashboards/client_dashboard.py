"""
Dashboard do Cliente - Multi-Tenant
Fase 2 - GeniAI Analytics
Base: Dashboard da porta 8503 (tema dark azul/laranja)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
from sqlalchemy import text
import io

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import get_database_engine, logout_user
from multi_tenant.auth.middleware import clear_session_state, set_rls_context
from multi_tenant.dashboards.branding import get_tenant_branding, apply_branding, render_header_with_logo
from app.config import format_number, format_percentage


# ============================================================================
# QUERIES DE DADOS (COM RLS AUTOMÁTICO)
# ============================================================================

@st.cache_data(ttl=300)  # Cache de 5 minutos
def load_conversations(tenant_id, date_start=None, date_end=None, inbox_filter=None, status_filter=None):
    """
    Carrega conversas do tenant (filtrado automaticamente via RLS)

    Args:
        tenant_id: ID do tenant (usado apenas para display, RLS filtra automaticamente)
        date_start: Data início do filtro (opcional)
        date_end: Data fim do filtro (opcional)

    Returns:
        pd.DataFrame: Conversas do tenant
    """
    engine = get_database_engine()

    # Query base (RLS filtra automaticamente por tenant_id)
    query = """
        SELECT
            id,
            conversation_id,
            display_id as conversation_display_id,
            inbox_id,
            inbox_name,
            contact_name,
            contact_phone,
            contact_email,
            DATE(conversation_created_at) as conversation_date,
            conversation_created_at,
            t_messages as total_messages,
            contact_messages_count as contact_messages,
            user_messages_count as agent_messages,
            0 as bot_messages,
            status as conversation_status,
            is_lead,
            visit_scheduled,
            crm_converted,
            ai_probability_label,
            ai_probability_score,
            has_human_intervention,
            is_resolved,
            first_response_time_minutes,
            conversation_period,
            is_weekday,
            is_business_hours,
            etl_updated_at as synced_at,
            -- Colunas Genéricas Multi-Tenant
            nome_mapeado_bot,
            mc_first_message_at as primeiro_contato,
            mc_last_message_at as ultimo_contato,
            message_compiled as conversa_compilada
            -- REMOVIDO: Colunas AllpFit-específicas (condicao_fisica, objetivo, analise_ia, sugestao_disparo, probabilidade_conversao)
            -- Motivo: Não aplicáveis a outros segmentos (educação, financeiro, etc.)
            -- Data: 2025-11-11 (pós-apresentação aos superiores)
        FROM conversations_analytics
        WHERE 1=1
    """

    params = {}

    # Filtros de data
    if date_start:
        query += " AND conversation_date >= :date_start"
        params['date_start'] = date_start

    if date_end:
        query += " AND conversation_date <= :date_end"
        params['date_end'] = date_end

    # Filtro por inbox (Fase 4)
    if inbox_filter and inbox_filter != "Todos":
        query += " AND inbox_id = :inbox_id"
        params['inbox_id'] = inbox_filter

    # Filtro por status (Fase 4)
    if status_filter and status_filter != "Todos":
        status_map = {"Abertas": 0, "Resolvidas": 1, "Pendentes": 2}
        if status_filter in status_map:
            query += " AND status = :status"
            params['status'] = status_map[status_filter]

    query += " ORDER BY conversation_date DESC, conversation_id DESC"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    return df


def get_tenant_info(tenant_id):
    """
    Retorna informações do tenant

    Args:
        tenant_id: ID do tenant

    Returns:
        dict: Informações do tenant
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            id,
            name,
            slug,
            inbox_ids,
            status,
            plan
        FROM tenants
        WHERE id = :tenant_id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id}).fetchone()

        if result:
            return {
                'id': result.id,
                'name': result.name,
                'slug': result.slug,
                'inbox_ids': result.inbox_ids,
                'status': result.status,
                'plan': result.plan,
            }

        return None


def get_tenant_inboxes(tenant_id):
    """
    Retorna lista de inboxes do tenant

    Args:
        tenant_id: ID do tenant

    Returns:
        list[dict]: Lista de inboxes com id e name
    """
    engine = get_database_engine()

    query = text("""
        SELECT DISTINCT
            itm.inbox_id,
            itm.inbox_name
        FROM inbox_tenant_mapping itm
        WHERE itm.tenant_id = :tenant_id
        ORDER BY itm.inbox_name
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id})
        inboxes = []

        for row in result:
            inboxes.append({
                'id': row.inbox_id,
                'name': row.inbox_name
            })

        return inboxes


# ============================================================================
# CÁLCULOS DE MÉTRICAS
# ============================================================================

def calculate_metrics(df):
    """
    Calcula métricas principais do dashboard

    Agora inclui:
    - Métricas de qualidade (IA%, Resolução, etc)
    - Performance (tempo resposta)

    Args:
        df: DataFrame com conversas

    Returns:
        dict: Métricas calculadas
    """
    if df.empty:
        return {
            'total_contacts': 0,
            'unique_contacts': 0,  # NOVO: contatos únicos
            'ai_conversations': 0,
            'human_conversations': 0,
            'leads': 0,
            'visits_scheduled': 0,
            'crm_converted': 0,
            'resolution_rate': 0.0,
            'avg_response_time': 0.0,
        }

    total = len(df)

    # Contar contatos únicos (para métrica de engagement)
    unique_contacts = df['contact_name'].nunique() if 'contact_name' in df.columns else total

    # Métricas Existentes
    metrics = {
        'total_contacts': total,
        'unique_contacts': unique_contacts,  # NOVO: contatos únicos
        'ai_conversations': len(df[df['has_human_intervention'] == False]) if 'has_human_intervention' in df.columns else len(df[df['bot_messages'] > 0]),
        'human_conversations': len(df[df['has_human_intervention'] == True]) if 'has_human_intervention' in df.columns else 0,
        'leads': len(df[df['is_lead'] == True]),
        'visits_scheduled': len(df[df['visit_scheduled'] == True]),
        'crm_converted': len(df[df['crm_converted'] == True]),
    }

    # NOVAS - Métricas de Qualidade [FASE 5.5]
    if 'is_resolved' in df.columns:
        resolved_count = len(df[df['is_resolved'] == True])
        metrics['resolution_rate'] = (resolved_count / total * 100) if total > 0 else 0.0
    else:
        metrics['resolution_rate'] = 0.0

    # Tempo resposta médio (em minutos)
    if 'first_response_time_minutes' in df.columns:
        valid_times = df[df['first_response_time_minutes'].notna()]['first_response_time_minutes']
        metrics['avg_response_time'] = valid_times.mean() if len(valid_times) > 0 else 0.0
    else:
        metrics['avg_response_time'] = 0.0

    return metrics


def prepare_leads_by_day(df):
    """
    Prepara dados de leads por dia para gráfico (consolidado)

    Args:
        df: DataFrame com conversas

    Returns:
        pd.DataFrame: Leads agrupados por dia
    """
    if df.empty:
        return pd.DataFrame(columns=['Data', 'Leads'])

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        return pd.DataFrame(columns=['Data', 'Leads'])

    # Agrupar por data
    leads_by_day = leads_df.groupby('conversation_date').size().reset_index(name='Leads')
    leads_by_day.rename(columns={'conversation_date': 'Data'}, inplace=True)

    # Ordenar por data
    leads_by_day = leads_by_day.sort_values('Data')

    return leads_by_day


def prepare_leads_by_day_with_inbox(df):
    """
    Prepara dados de leads por dia E por inbox (para stacked bar chart)

    Args:
        df: DataFrame com conversas

    Returns:
        pd.DataFrame: Leads agrupados por dia e inbox (formato: Data, Inbox1, Inbox2, ...)
    """
    if df.empty:
        return pd.DataFrame()

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        return pd.DataFrame()

    # Agrupar por data E inbox
    leads_grouped = leads_df.groupby(['conversation_date', 'inbox_name']).size().reset_index(name='Leads')

    # Pivotar para ter inbox como colunas
    leads_pivot = leads_grouped.pivot(index='conversation_date', columns='inbox_name', values='Leads').fillna(0)

    # Resetar index para ter 'Data' como coluna
    leads_pivot = leads_pivot.reset_index()
    leads_pivot.rename(columns={'conversation_date': 'Data'}, inplace=True)

    # Ordenar por data
    leads_pivot = leads_pivot.sort_values('Data')

    return leads_pivot


def prepare_leads_by_inbox(df):
    """
    Prepara dados de leads por inbox para gráfico

    Args:
        df: DataFrame com conversas

    Returns:
        pd.DataFrame: Leads agrupados por inbox
    """
    if df.empty:
        return pd.DataFrame(columns=['Inbox', 'Leads'])

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        return pd.DataFrame(columns=['Inbox', 'Leads'])

    # Agrupar por inbox
    leads_by_inbox = leads_df.groupby('inbox_name').size().reset_index(name='Leads')
    leads_by_inbox.rename(columns={'inbox_name': 'Inbox'}, inplace=True)

    # Ordenar por quantidade de leads (descendente)
    leads_by_inbox = leads_by_inbox.sort_values('Leads', ascending=False)

    return leads_by_inbox


def prepare_score_distribution(df):
    """
    Prepara dados de distribuição de score IA para gráfico de pizza

    Args:
        df: DataFrame com conversas

    Returns:
        pd.DataFrame: Distribuição de score IA
    """
    if df.empty:
        return pd.DataFrame(columns=['Classificação', 'Quantidade'])

    # Filtrar apenas leads com classificação
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        return pd.DataFrame(columns=['Classificação', 'Quantidade'])

    # Agrupar por classificação IA
    score_dist = leads_df.groupby('ai_probability_label').size().reset_index(name='Quantidade')
    score_dist.rename(columns={'ai_probability_label': 'Classificação'}, inplace=True)

    # Ordenar por ordem de prioridade (Alto > Médio > Baixo > N/A)
    order = {'Alto': 1, 'Médio': 2, 'Baixo': 3, 'N/A': 4}
    score_dist['_order'] = score_dist['Classificação'].map(order)
    score_dist = score_dist.sort_values('_order').drop('_order', axis=1)

    return score_dist


def prepare_period_distribution(df):
    """
    Prepara dados de distribuição de conversas por período do dia
    [FASE 5.5 - NOVA FUNÇÃO]

    Args:
        df: DataFrame com conversas

    Returns:
        pd.DataFrame: Distribuição por período (Manhã/Tarde/Noite/Madrugada)
    """
    if df.empty or 'conversation_period' not in df.columns:
        return pd.DataFrame(columns=['Período', 'Quantidade'])

    # Filtrar períodos válidos (não nulos)
    period_df = df[df['conversation_period'].notna()].copy()

    if period_df.empty:
        return pd.DataFrame(columns=['Período', 'Quantidade'])

    # Agrupar por período
    period_dist = period_df.groupby('conversation_period').size().reset_index(name='Quantidade')
    period_dist.rename(columns={'conversation_period': 'Período'}, inplace=True)

    # Ordenar por ordem lógica dos períodos
    period_order = {'Manhã': 1, 'Tarde': 2, 'Noite': 3, 'Madrugada': 4}
    period_dist['_order'] = period_dist['Período'].map(period_order).fillna(99)
    period_dist = period_dist.sort_values('_order').drop('_order', axis=1)

    return period_dist


def prepare_csv_export(df):
    """
    Prepara dados para exportação CSV

    Args:
        df: DataFrame com conversas

    Returns:
        str: CSV formatado como string
    """
    if df.empty:
        return None

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        return None

    # Selecionar e renomear colunas para exportação
    export_df = leads_df[[
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'contact_email',
        'inbox_name',
        'conversation_date',
        'is_lead',
        'visit_scheduled',
        'crm_converted',
        'ai_probability_label',
        'ai_probability_score',
        'total_messages',
        'contact_messages',
        'agent_messages',
        'conversation_status'
    ]].copy()

    # Renomear colunas para português
    export_df.columns = [
        'ID Conversa',
        'Nome Contato',
        'Telefone',
        'Email',
        'Inbox',
        'Data',
        'Lead',
        'Visita Agendada',
        'Convertido CRM',
        'Classificação IA',
        'Score IA (%)',
        'Total Mensagens',
        'Mensagens Contato',
        'Mensagens Agente',
        'Status'
    ]

    # Formatar booleanos
    export_df['Lead'] = export_df['Lead'].apply(lambda x: 'Sim' if x else 'Não')
    export_df['Visita Agendada'] = export_df['Visita Agendada'].apply(lambda x: 'Sim' if x else 'Não')
    export_df['Convertido CRM'] = export_df['Convertido CRM'].apply(lambda x: 'Sim' if x else 'Não')

    # Formatar status
    status_map = {0: 'Aberta', 1: 'Resolvida', 2: 'Pendente'}
    export_df['Status'] = export_df['Status'].map(status_map)

    # Converter para CSV
    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')  # utf-8-sig para Excel
    return csv_buffer.getvalue()


# ============================================================================
# COMPONENTES UI
# ============================================================================

def render_header(session, tenant_name, show_back=False):
    """
    Renderiza header do dashboard

    Args:
        session: Dados da sessão
        tenant_name: Nome do tenant exibido
        show_back: Se mostra botão voltar (apenas para admins)

    Returns:
        str: Ação do usuário ('back', 'logout', None)
    """
    cols = st.columns([1, 5, 1])

    action = None

    with cols[0]:
        if show_back:
            if st.button("← Voltar", use_container_width=True):
                action = 'back'

    with cols[1]:
        st.title(f"📊 Analytics - {tenant_name}")
        st.caption(f"👤 {session['full_name']} ({session['role']})")

    with cols[2]:
        if st.button("🚪 Sair", use_container_width=True):
            action = 'logout'

    return action


def render_kpis(metrics):
    """
    Renderiza KPIs principais (cards de métricas)

    Args:
        metrics: Dict com métricas calculadas
    """
    # Linha 1: Métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Contatos", format_number(metrics['total_contacts']))

    with col2:
        st.metric("Leads", format_number(metrics['leads']))

    with col3:
        st.metric("Visitas Agendadas", format_number(metrics['visits_scheduled']))

    with col4:
        st.metric("Conversões CRM", format_number(metrics['crm_converted']))

    with col5:
        st.metric("Taxa de Conversão", format_percentage(metrics['leads'], metrics['total_contacts']))

    # REMOVIDO: Funil de Conversão (específico AllpFit - Leads → Visitas → CRM)
    # Motivo: Fluxo específico de vendas fitness, não aplicável a outros segmentos
    # Data: 2025-11-11 (pós-apresentação)


def render_leads_chart(leads_by_day, df_full=None):
    """
    Renderiza gráfico de leads por dia (consolidado ou por inbox)

    Args:
        leads_by_day: DataFrame com leads agrupados por dia (consolidado)
        df_full: DataFrame completo com todas conversas (para split por inbox)
    """
    if leads_by_day.empty:
        st.info("ℹ️ Nenhum lead para exibir no período selecionado")
        return

    st.subheader("📈 Leads por Dia")

    # === TOGGLE: CONSOLIDADO vs POR INBOX ===
    col_periodo, col_viz = st.columns([3, 2])

    with col_periodo:
        periodo_grafico = st.selectbox(
            "📅 Período:",
            options=[
                "Últimos 7 dias",
                "Últimos 15 dias",
            "Últimos 30 dias",
            "Mês atual",
            "Mês passado",
            "Últimos 3 meses",
            "Últimos 6 meses",
            "Último ano",
            "Todos os dados"
        ],
        index=2,  # Default: Últimos 30 dias
        key="periodo_grafico_leads"
    )

    with col_viz:
        # Radio buttons horizontal para escolher visualização
        viz_mode = st.radio(
            "📊 Visualização:",
            options=["Consolidado", "Por Inbox"],
            index=0,
            key="viz_mode_leads",
            horizontal=True,
            help="Consolidado: total de leads por dia | Por Inbox: leads separados por inbox (stacked)"
        )

    # Filtrar dados baseado no período selecionado
    from datetime import datetime, timedelta

    hoje = pd.Timestamp(datetime.now().date())

    if periodo_grafico == "Últimos 7 dias":
        data_corte = hoje - timedelta(days=7)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    elif periodo_grafico == "Últimos 15 dias":
        data_corte = hoje - timedelta(days=15)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    elif periodo_grafico == "Últimos 30 dias":
        data_corte = hoje - timedelta(days=30)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    elif periodo_grafico == "Mês atual":
        inicio_mes = hoje.replace(day=1)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= inicio_mes].copy()
    elif periodo_grafico == "Mês passado":
        inicio_mes_passado = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        fim_mes_passado = hoje.replace(day=1) - timedelta(days=1)
        leads_filtrados = leads_by_day[
            (pd.to_datetime(leads_by_day['Data']) >= inicio_mes_passado) &
            (pd.to_datetime(leads_by_day['Data']) <= fim_mes_passado)
        ].copy()
    elif periodo_grafico == "Últimos 3 meses":
        data_corte = hoje - timedelta(days=90)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    elif periodo_grafico == "Últimos 6 meses":
        data_corte = hoje - timedelta(days=180)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    elif periodo_grafico == "Último ano":
        data_corte = hoje - timedelta(days=365)
        leads_filtrados = leads_by_day[pd.to_datetime(leads_by_day['Data']) >= data_corte].copy()
    else:  # Todos os dados
        leads_filtrados = leads_by_day.copy()

    # Se não houver dados após filtro, mostrar mensagem
    if leads_filtrados.empty:
        st.info(f"ℹ️ Nenhum lead encontrado no período: **{periodo_grafico}**")
        return

    # Converter Data para datetime
    leads_filtrados['Data'] = pd.to_datetime(leads_filtrados['Data'])

    # LÓGICA SIMPLIFICADA: Granularidade automática baseada no período selecionado
    # Últimos 7/15/30 dias → Diário
    # Mês atual/passado → Mensal (1 barra)
    # Últimos 3/6 meses ou ano → Mensal
    # Todos os dados → Inteligente (baseado na quantidade de dias)

    if periodo_grafico in ["Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias"]:
        # Mostrar cada dia individualmente
        leads_filtrados['Periodo'] = leads_filtrados['Data'].dt.strftime('%d/%m')
        chart_data = leads_filtrados
        x_col = 'Periodo'
        x_title = 'Data'

    elif periodo_grafico in ["Mês atual", "Mês passado"]:
        # Agrupar tudo em 1 barra mensal
        agrupado = leads_filtrados.groupby(leads_filtrados['Data'].dt.to_period('M')).agg({'Leads': 'sum'}).reset_index()
        agrupado['Data'] = agrupado['Data'].dt.to_timestamp()
        agrupado['Periodo'] = agrupado['Data'].dt.strftime('%b/%Y')

        chart_data = agrupado
        x_col = 'Periodo'
        x_title = 'Mês'

    elif periodo_grafico in ["Últimos 3 meses", "Últimos 6 meses", "Último ano"]:
        # Agrupar por mês (3, 6 ou 12 barras)
        agrupado = leads_filtrados.groupby(leads_filtrados['Data'].dt.to_period('M')).agg({'Leads': 'sum'}).reset_index()
        agrupado['Data'] = agrupado['Data'].dt.to_timestamp()
        agrupado['Periodo'] = agrupado['Data'].dt.strftime('%b/%Y')

        chart_data = agrupado
        x_col = 'Periodo'
        x_title = 'Mês'

    else:  # "Todos os dados"
        # Agrupamento inteligente baseado na quantidade de dias
        num_days = len(leads_filtrados)

        if num_days > 90:
            # Mais de 90 dias: agrupar por mês
            agrupado = leads_filtrados.groupby(leads_filtrados['Data'].dt.to_period('M')).agg({'Leads': 'sum'}).reset_index()
            agrupado['Data'] = agrupado['Data'].dt.to_timestamp()
            agrupado['Periodo'] = agrupado['Data'].dt.strftime('%b/%Y')

            chart_data = agrupado
            x_col = 'Periodo'
            x_title = 'Mês'

        elif num_days > 60:
            # Entre 60 e 90 dias: agrupar por semana
            agrupado = leads_filtrados.groupby(leads_filtrados['Data'].dt.to_period('W')).agg({'Leads': 'sum'}).reset_index()
            agrupado['Data'] = agrupado['Data'].dt.to_timestamp()
            agrupado['Periodo'] = agrupado['Data'].dt.strftime('%d/%m')

            chart_data = agrupado
            x_col = 'Periodo'
            x_title = 'Semana'

        else:
            # Até 60 dias: diário
            leads_filtrados['Periodo'] = leads_filtrados['Data'].dt.strftime('%d/%m')
            chart_data = leads_filtrados
            x_col = 'Periodo'
            x_title = 'Data'

    # === RENDERIZAR GRÁFICO: CONSOLIDADO vs POR INBOX ===
    import plotly.express as px
    import plotly.graph_objects as go

    if viz_mode == "Consolidado":
        # MODO CONSOLIDADO: Barra única azul por período
        fig = px.bar(
            chart_data,
            x=x_col,
            y='Leads',
            title='',
            labels={x_col: x_title, 'Leads': 'Quantidade de Leads'},
            text='Leads'
        )

        fig.update_traces(
            textposition='outside',
            marker_color='#1f77b4',
            hovertemplate=f'<b>{x_title}:</b> %{{x}}<br><b>Leads:</b> %{{y}}<extra></extra>'
        )

        num_bars = len(chart_data)
        rotate_labels = num_bars > 30

        fig.update_layout(
            xaxis_title=x_title,
            yaxis_title='Leads',
            showlegend=False,
            height=400,
            bargap=0.15,
            hovermode='x unified',
            xaxis={'tickangle': -45 if rotate_labels else 0}
        )

    else:
        # MODO POR INBOX: Stacked bar chart colorido 🎨
        if df_full is None or df_full.empty:
            st.warning("⚠️ Dados completos não disponíveis para visualização por inbox")
            return

        # Preparar dados por inbox
        leads_inbox_full = prepare_leads_by_day_with_inbox(df_full)

        if leads_inbox_full.empty:
            st.info("ℹ️ Nenhum lead para exibir")
            return

        # Aplicar filtros de período
        leads_inbox_full['Data'] = pd.to_datetime(leads_inbox_full['Data'])

        if periodo_grafico == "Últimos 7 dias":
            data_corte = hoje - timedelta(days=7)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        elif periodo_grafico == "Últimos 15 dias":
            data_corte = hoje - timedelta(days=15)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        elif periodo_grafico == "Últimos 30 dias":
            data_corte = hoje - timedelta(days=30)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        elif periodo_grafico == "Mês atual":
            inicio_mes = hoje.replace(day=1)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= inicio_mes].copy()
        elif periodo_grafico == "Mês passado":
            inicio_mes_passado = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
            fim_mes_passado = hoje.replace(day=1) - timedelta(days=1)
            leads_inbox_filtered = leads_inbox_full[
                (leads_inbox_full['Data'] >= inicio_mes_passado) &
                (leads_inbox_full['Data'] <= fim_mes_passado)
            ].copy()
        elif periodo_grafico == "Últimos 3 meses":
            data_corte = hoje - timedelta(days=90)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        elif periodo_grafico == "Últimos 6 meses":
            data_corte = hoje - timedelta(days=180)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        elif periodo_grafico == "Último ano":
            data_corte = hoje - timedelta(days=365)
            leads_inbox_filtered = leads_inbox_full[leads_inbox_full['Data'] >= data_corte].copy()
        else:
            leads_inbox_filtered = leads_inbox_full.copy()

        if leads_inbox_filtered.empty:
            st.info(f"ℹ️ Nenhum lead no período: **{periodo_grafico}**")
            return

        # Aplicar granularidade
        if periodo_grafico in ["Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias"]:
            leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%d/%m')
            x_title_inbox = 'Data'
        elif periodo_grafico in ["Mês atual", "Mês passado"]:
            leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%b/%Y')
            x_title_inbox = 'Mês'
        elif periodo_grafico in ["Últimos 3 meses", "Últimos 6 meses", "Último ano"]:
            leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%b/%Y')
            x_title_inbox = 'Mês'
        else:
            num_days_inbox = len(leads_inbox_filtered)
            if num_days_inbox > 90:
                leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%b/%Y')
                x_title_inbox = 'Mês'
            elif num_days_inbox > 60:
                leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%d/%m')
                x_title_inbox = 'Semana'
            else:
                leads_inbox_filtered['Periodo'] = leads_inbox_filtered['Data'].dt.strftime('%d/%m')
                x_title_inbox = 'Data'

        # Criar stacked bar chart
        inbox_columns = [col for col in leads_inbox_filtered.columns if col not in ['Data', 'Periodo']]
        colors = px.colors.qualitative.Set2 + px.colors.qualitative.Pastel

        fig = go.Figure()

        for idx, inbox_col in enumerate(inbox_columns):
            fig.add_trace(go.Bar(
                x=leads_inbox_filtered['Periodo'],
                y=leads_inbox_filtered[inbox_col],
                name=inbox_col,
                marker_color=colors[idx % len(colors)],
                hovertemplate=f'<b>{inbox_col}</b><br>Leads: %{{y}}<extra></extra>'
            ))

        num_bars_inbox = len(leads_inbox_filtered)
        rotate_labels_inbox = num_bars_inbox > 30

        fig.update_layout(
            barmode='stack',
            xaxis_title=x_title_inbox,
            yaxis_title='Leads',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=450,
            bargap=0.15,
            hovermode='x unified',
            xaxis={'tickangle': -45 if rotate_labels_inbox else 0}
        )

    # Remover botões confusos do Plotly
    config = {
        'displayModeBar': False,
        'displaylogo': False
    }

    st.plotly_chart(fig, use_container_width=True, config=config)

    # Dica de interatividade (apenas no modo "Por Inbox")
    if viz_mode == "Por Inbox":
        st.caption("💡 **Dica:** Clique nos nomes das inboxes na legenda acima para mostrar/ocultar no gráfico")


def render_leads_by_inbox_chart(leads_by_inbox):
    """
    Renderiza gráfico de leads por inbox

    Args:
        leads_by_inbox: DataFrame com leads agrupados por inbox
    """
    if leads_by_inbox.empty:
        st.info("ℹ️ Nenhum lead para exibir no período selecionado")
        return

    st.subheader("📊 Leads por Inbox")
    st.bar_chart(leads_by_inbox.set_index('Inbox')['Leads'], use_container_width=True)


def render_score_distribution_chart(score_dist):
    """
    Renderiza gráfico de distribuição de score IA

    Args:
        score_dist: DataFrame com distribuição de scores
    """
    if score_dist.empty:
        st.info("ℹ️ Nenhum lead com classificação para exibir")
        return

    st.subheader("🎯 Distribuição de Classificação IA")

    # Usar colunas para melhor layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Gráfico de barras horizontal
        st.bar_chart(score_dist.set_index('Classificação')['Quantidade'], use_container_width=True)

    with col2:
        # Tabela resumo
        st.write("**Resumo:**")
        for _, row in score_dist.iterrows():
            st.write(f"- **{row['Classificação']}**: {row['Quantidade']} leads")


# REMOVIDO: render_quality_metrics() - Arquivada em _archived/quality_metrics_removed.py
# Data: 2025-11-11
# Motivo: Simplificação do dashboard (métricas de qualidade não essenciais)


def render_period_distribution_chart(period_dist):
    """
    Renderiza gráfico de distribuição por período do dia
    [FASE 5.5 - NOVA FUNÇÃO]

    Args:
        period_dist: DataFrame com distribuição de períodos
    """
    if period_dist.empty:
        st.info("ℹ️ Nenhum dado para exibir")
        return

    st.subheader("🕐 Distribuição por Período do Dia")

    # Gráfico de barras
    st.bar_chart(period_dist.set_index('Período')['Quantidade'], use_container_width=True)

    # Resumo em colunas
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]

    for idx, (_, row) in enumerate(period_dist.iterrows()):
        if idx < 4:
            with cols[idx]:
                st.metric(row['Período'], f"{row['Quantidade']}")


# ============================================================================
# CONVERSA COMPILADA [FASE 6]
# ============================================================================

def format_message_preview(message_compiled, max_messages=3):
    """
    Formata prévia da conversa compilada (primeiras N mensagens)

    Args:
        message_compiled: JSONB com mensagens (lista de dicts ou None)
        max_messages: Número máximo de mensagens a exibir na prévia

    Returns:
        str: Texto formatado para exibição na tabela
    """
    import json

    # CORREÇÃO: Verificar tipo ANTES de usar pd.isna() para evitar erro com arrays
    # JSONB do PostgreSQL vem como lista/dict Python (não string!)

    # Caso 1: JSONB já parseado (lista ou dict)
    if isinstance(message_compiled, (list, dict)):
        messages = message_compiled

        # Verificar se lista está vazia
        if isinstance(messages, list) and len(messages) == 0:
            return "N/A"

    # Caso 2: None ou NaN (somente DEPOIS de verificar se não é lista/dict)
    elif message_compiled is None or pd.isna(message_compiled):
        return "N/A"

    # Caso 3: String JSON (fallback para compatibilidade)
    elif isinstance(message_compiled, str):
        try:
            messages = json.loads(message_compiled)
            if isinstance(messages, list) and len(messages) == 0:
                return "N/A"
        except Exception as e:
            return f"Erro: {str(e)}"

    # Caso 4: Tipo desconhecido
    else:
        return "N/A"

    try:

        # Pegar primeiras N mensagens
        preview_messages = messages[:max_messages]

        # Formatar cada mensagem
        formatted = []
        for msg in preview_messages:
            sender = msg.get('sender', '?')
            text = msg.get('text', '')

            # Emoji por tipo de sender
            if sender == 'Contact':
                emoji = '👤'
            elif sender == 'AgentBot':
                emoji = '🤖'
            elif sender == 'User':
                emoji = '👨‍💼'
            else:
                emoji = '📩'

            # Limitar texto a 50 caracteres
            if len(text) > 50:
                text = text[:47] + "..."

            formatted.append(f"{emoji} {text}")

        # Juntar com quebra de linha
        result = "\n".join(formatted)

        # Indicar se há mais mensagens
        if len(messages) > max_messages:
            result += f"\n... (+{len(messages) - max_messages} mensagens)"

        return result

    except Exception as e:
        return f"Erro: {str(e)}"


def render_conversation_modal(conversation_id, message_compiled, contact_name):
    """
    Renderiza modal expandido com conversa completa

    Args:
        conversation_id: ID da conversa
        message_compiled: JSONB com todas as mensagens
        contact_name: Nome do contato
    """
    import json

    with st.expander(f"💬 Conversa Completa - {contact_name} (ID: {conversation_id})"):
        # CORREÇÃO: Mesma lógica de format_message_preview()
        # Verificar tipo ANTES de usar pd.isna()

        # Caso 1: JSONB já parseado (lista ou dict)
        if isinstance(message_compiled, (list, dict)):
            messages = message_compiled

            # Verificar se lista está vazia
            if isinstance(messages, list) and len(messages) == 0:
                st.info("ℹ️ Nenhuma mensagem encontrada")
                return

        # Caso 2: None ou NaN
        elif message_compiled is None or pd.isna(message_compiled):
            st.warning("⚠️ Conversa não disponível")
            return

        # Caso 3: String JSON (fallback)
        elif isinstance(message_compiled, str):
            try:
                messages = json.loads(message_compiled)
                if isinstance(messages, list) and len(messages) == 0:
                    st.info("ℹ️ Nenhuma mensagem encontrada")
                    return
            except Exception as e:
                st.error(f"❌ Erro ao fazer parse do JSON: {str(e)}")
                return

        # Caso 4: Tipo desconhecido
        else:
            st.warning("⚠️ Formato de conversa não reconhecido")
            return

        try:

            st.caption(f"📊 Total de mensagens: {len(messages)}")
            st.divider()

            # Exibir cada mensagem
            for idx, msg in enumerate(messages, 1):
                sender = msg.get('sender', 'Desconhecido')
                text = msg.get('text', '')
                sent_at = msg.get('sent_at', '')

                # Emoji e cor por tipo de sender
                if sender == 'Contact':
                    emoji = '👤'
                    label = 'Contato'
                    color = '#4CAF50'  # Verde
                elif sender == 'AgentBot':
                    emoji = '🤖'
                    label = 'Bot'
                    color = '#2196F3'  # Azul
                elif sender == 'User':
                    emoji = '👨‍💼'
                    label = 'Atendente'
                    color = '#FF9800'  # Laranja
                else:
                    emoji = '📩'
                    label = sender
                    color = '#9E9E9E'  # Cinza

                # Formatar timestamp
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                    time_str = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    time_str = sent_at

                # Exibir mensagem
                st.markdown(f"""
                <div style="margin-bottom: 10px; padding: 10px; border-left: 3px solid {color}; background-color: rgba(0,0,0,0.05);">
                    <strong>{emoji} {label}</strong> <small style="color: #888;">({time_str})</small><br>
                    {text}
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Erro ao carregar conversa: {str(e)}")


# ============================================================================
# ANÁLISE POR INBOX [FASE 5]
# ============================================================================

def prepare_inbox_metrics(df):
    """
    Prepara métricas agregadas e individuais por inbox

    Args:
        df: DataFrame com conversas

    Returns:
        tuple: (metrics_agregadas, metrics_por_inbox)
    """
    if df.empty:
        return {}, pd.DataFrame()

    # Métricas agregadas (todas as inboxes juntas)
    total_conversas = len(df)
    total_leads = len(df[df['is_lead'] == True])
    total_visitas = len(df[df['visit_scheduled'] == True])
    total_crm = len(df[df['crm_converted'] == True])

    # Tempo médio de primeira resposta (em minutos)
    avg_response_time = df['first_response_time_minutes'].mean() if 'first_response_time_minutes' in df.columns else 0

    metrics_agregadas = {
        'total_conversas': total_conversas,
        'total_leads': total_leads,
        'total_visitas': total_visitas,
        'total_crm': total_crm,
        'taxa_conversao_leads': (total_leads / total_conversas * 100) if total_conversas > 0 else 0,
        'taxa_conversao_crm': (total_crm / total_leads * 100) if total_leads > 0 else 0,
        'avg_response_time': avg_response_time
    }

    # Métricas por inbox individual
    inbox_groups = df.groupby('inbox_name').agg({
        'conversation_id': 'count',  # Total de conversas
        'is_lead': lambda x: (x == True).sum(),  # Total de leads
        'visit_scheduled': lambda x: (x == True).sum(),  # Total de visitas
        'crm_converted': lambda x: (x == True).sum(),  # Total CRM
        'first_response_time_minutes': 'mean'  # Tempo médio de resposta
    }).reset_index()

    inbox_groups.columns = ['inbox_name', 'total_conversas', 'total_leads', 'total_visitas', 'total_crm', 'avg_response_time']

    # Calcular taxas de conversão
    inbox_groups['taxa_leads'] = inbox_groups.apply(
        lambda row: (row['total_leads'] / row['total_conversas'] * 100) if row['total_conversas'] > 0 else 0,
        axis=1
    )
    inbox_groups['taxa_crm'] = inbox_groups.apply(
        lambda row: (row['total_crm'] / row['total_leads'] * 100) if row['total_leads'] > 0 else 0,
        axis=1
    )

    # Ordenar por total de conversas (decrescente)
    inbox_groups = inbox_groups.sort_values('total_conversas', ascending=False)

    return metrics_agregadas, inbox_groups


def render_inbox_analysis(df):
    """
    Renderiza seção de Análise por Inbox (FASE 5)

    Exibe métricas de DUAS formas:
    1. Agregadas: Todas as inboxes juntas (visão geral)
    2. Separadas: Métricas individuais por inbox (visão detalhada)

    Args:
        df: DataFrame com conversas
    """
    st.subheader("📬 Análise por Inbox")

    if df.empty:
        st.info("ℹ️ Nenhum dado disponível para análise por inbox")
        return

    # Preparar dados
    metrics_agregadas, inbox_metrics = prepare_inbox_metrics(df)

    # Toggle entre visão agregada e separada
    view_mode = st.radio(
        "Modo de Visualização:",
        options=["📊 Visão Agregada (Consolidado)", "📋 Visão Separada (Por Inbox)"],
        horizontal=True,
        key="inbox_view_mode"
    )

    st.divider()

    if view_mode == "📊 Visão Agregada (Consolidado)":
        # === VISÃO AGREGADA ===
        st.markdown("#### 📊 Métricas Consolidadas (Todas as Inboxes)")

        # Métricas principais em 5 colunas
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Total Conversas",
                format_number(metrics_agregadas['total_conversas']),
                help="Total de conversas em todas as inboxes"
            )

        with col2:
            st.metric(
                "Total Leads",
                format_number(metrics_agregadas['total_leads']),
                delta=f"{metrics_agregadas['taxa_conversao_leads']:.1f}% conversão",
                help="Leads identificados em todas as inboxes"
            )

        with col3:
            st.metric(
                "Visitas Agendadas",
                format_number(metrics_agregadas['total_visitas']),
                help="Total de visitas agendadas"
            )

        with col4:
            st.metric(
                "Conversões CRM",
                format_number(metrics_agregadas['total_crm']),
                delta=f"{metrics_agregadas['taxa_conversao_crm']:.1f}% dos leads",
                help="Leads convertidos em CRM"
            )

        with col5:
            # Formatar tempo de resposta
            avg_time = metrics_agregadas['avg_response_time']
            if pd.notna(avg_time) and avg_time > 0:
                if avg_time < 60:
                    time_str = f"{avg_time:.0f}min"
                else:
                    hours = avg_time / 60
                    time_str = f"{hours:.1f}h"
            else:
                time_str = "N/A"

            st.metric(
                "Tempo Médio Resposta",
                time_str,
                help="Tempo médio de primeira resposta"
            )

        st.divider()

        # Gráfico de distribuição por inbox
        st.markdown("#### 📊 Distribuição de Conversas por Inbox")

        if not inbox_metrics.empty:
            # Gráfico de barras horizontal
            import plotly.express as px

            fig = px.bar(
                inbox_metrics,
                x='total_conversas',
                y='inbox_name',
                orientation='h',
                title='Total de Conversas por Inbox',
                labels={'total_conversas': 'Conversas', 'inbox_name': 'Inbox'},
                color='total_conversas',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    else:
        # === VISÃO SEPARADA (POR INBOX) ===
        st.markdown("#### 📋 Métricas Individuais por Inbox")

        if inbox_metrics.empty:
            st.info("ℹ️ Nenhuma inbox encontrada")
            return

        # Exibir tabela com métricas por inbox
        display_inbox = inbox_metrics[[
            'inbox_name',
            'total_conversas',
            'total_leads',
            'taxa_leads',
            'total_visitas',
            'total_crm',
            'taxa_crm',
            'avg_response_time'
        ]].copy()

        # Renomear colunas
        display_inbox.columns = [
            'Inbox',
            'Conversas',
            'Leads',
            'Taxa Leads (%)',
            'Visitas',
            'CRM',
            'Taxa CRM (%)',
            'Tempo Resp. (min)'
        ]

        # Formatar colunas
        display_inbox['Taxa Leads (%)'] = display_inbox['Taxa Leads (%)'].apply(lambda x: f"{x:.1f}%")
        display_inbox['Taxa CRM (%)'] = display_inbox['Taxa CRM (%)'].apply(lambda x: f"{x:.1f}%")
        display_inbox['Tempo Resp. (min)'] = display_inbox['Tempo Resp. (min)'].apply(
            lambda x: f"{x:.0f}" if pd.notna(x) and x > 0 else "N/A"
        )

        # Exibir tabela
        st.dataframe(display_inbox, use_container_width=True, hide_index=True)

        st.divider()

        # Cards individuais por inbox (top 3)
        st.markdown("#### 🏆 Top 3 Inboxes (por volume)")

        top3 = inbox_metrics.head(3)

        if len(top3) > 0:
            cols = st.columns(min(len(top3), 3))

            for idx, (_, row) in enumerate(top3.iterrows()):
                if idx < 3:
                    with cols[idx]:
                        st.markdown(f"**{row['inbox_name']}**")
                        st.metric("Conversas", format_number(int(row['total_conversas'])))
                        st.metric("Leads", format_number(int(row['total_leads'])), delta=f"{row['taxa_leads']:.1f}%")

                        # Tempo de resposta
                        avg_time = row['avg_response_time']
                        if pd.notna(avg_time) and avg_time > 0:
                            if avg_time < 60:
                                time_str = f"{avg_time:.0f}min"
                            else:
                                hours = avg_time / 60
                                time_str = f"{hours:.1f}h"
                        else:
                            time_str = "N/A"

                        st.caption(f"⏱️ Tempo Resp: {time_str}")


def render_leads_table(df, df_original, tenant_name, date_start, date_end):
    """
    Renderiza tabela de leads genérica (multi-tenant)

    Args:
        df: DataFrame com conversas (JÁ FILTRADO pelos filtros rápidos)
        df_original: DataFrame original SEM filtros (para extrair inboxes disponíveis)
        tenant_name: Nome do tenant (para nome do arquivo)
        date_start: Data início (para nome do arquivo)
        date_end: Data fim (para nome do arquivo)
    """
    # Header com botão de exportação
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📋 Tabela de Leads")

    with col2:
        # Botão de exportação CSV
        csv_data = prepare_csv_export(df)
        if csv_data:
            # Gerar nome do arquivo
            filename = f"leads_{tenant_name.lower().replace(' ', '_')}_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}.csv"

            st.download_button(
                label="📥 Exportar CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Exportar CSV", disabled=True, use_container_width=True, help="Nenhum lead para exportar")

    st.divider()

    # === FILTROS RÁPIDOS === [FASE 4]
    st.markdown("#### 🔍 Filtros Rápidos")

    # 6 colunas horizontais
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)

    with col_f1:
        filter_nome_input = st.text_input(
            "👤 Nome",
            value=st.session_state.filter_nome,
            placeholder="Digite...",
            key="input_filter_nome",
            help="Busca parcial no nome do contato"
        )
        # Atualizar session state
        if filter_nome_input != st.session_state.filter_nome:
            st.session_state.filter_nome = filter_nome_input
            st.rerun()

    with col_f2:
        filter_telefone_input = st.text_input(
            "📞 Telefone",
            value=st.session_state.filter_telefone,
            placeholder="Digite...",
            key="input_filter_telefone",
            help="Busca parcial no telefone"
        )
        # Atualizar session state
        if filter_telefone_input != st.session_state.filter_telefone:
            st.session_state.filter_telefone = filter_telefone_input
            st.rerun()

    with col_f3:
        # IMPORTANTE: Usar inboxes REAIS dos dados (não do mapeamento inbox_tenant_mapping)
        # Motivo: Mapeamento pode estar desatualizado, causando filtros que não retornam dados
        inbox_names_available = sorted(df_original['inbox_name'].dropna().unique().tolist()) if not df_original.empty else []

        # Limpar filtros inválidos do session_state (inboxes que não existem mais nos dados)
        valid_selected = [inbox for inbox in st.session_state.filter_inboxes if inbox in inbox_names_available]
        if valid_selected != st.session_state.filter_inboxes:
            st.session_state.filter_inboxes = valid_selected

        filter_inboxes_input = st.multiselect(
            "📬 Inboxes",
            options=inbox_names_available,
            default=st.session_state.filter_inboxes,
            key="input_filter_inboxes",
            help="Selecione uma ou mais inboxes (baseado nos dados reais)"
        )
        # Atualizar session state
        if filter_inboxes_input != st.session_state.filter_inboxes:
            st.session_state.filter_inboxes = filter_inboxes_input
            st.rerun()

    with col_f4:
        filter_status_input = st.multiselect(
            "📊 Status",
            options=["Aberta", "Resolvida", "Pendente"],
            default=st.session_state.filter_status_list,
            key="input_filter_status",
            help="Status da conversa"
        )
        # Atualizar session state
        if filter_status_input != st.session_state.filter_status_list:
            st.session_state.filter_status_list = filter_status_input
            st.rerun()

    with col_f5:
        filter_classificacao_input = st.multiselect(
            "🎯 Classificação",
            options=["Alto", "Médio", "Baixo"],
            default=st.session_state.filter_classificacao,
            key="input_filter_classificacao",
            help="Classificação IA do lead"
        )
        # Atualizar session state
        if filter_classificacao_input != st.session_state.filter_classificacao:
            st.session_state.filter_classificacao = filter_classificacao_input
            st.rerun()

    with col_f6:
        filter_score_input = st.slider(
            "📈 Score IA Mín.",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.filter_score_min,
            step=5.0,
            key="input_filter_score",
            help="Score mínimo IA (0-100%)"
        )
        # Atualizar session state
        if filter_score_input != st.session_state.filter_score_min:
            st.session_state.filter_score_min = filter_score_input
            st.rerun()

    # Linha de controle: Limpar filtros + Indicador
    col_control1, col_control2 = st.columns([1, 4])

    with col_control1:
        if st.button("🗑️ Limpar Filtros", use_container_width=True):
            st.session_state.filter_nome = ""
            st.session_state.filter_telefone = ""
            st.session_state.filter_inboxes = []
            st.session_state.filter_status_list = []
            st.session_state.filter_classificacao = []
            st.session_state.filter_score_min = 0.0
            st.rerun()

    with col_control2:
        # Contar filtros ativos
        active_filters = 0
        if st.session_state.filter_nome:
            active_filters += 1
        if st.session_state.filter_telefone:
            active_filters += 1
        if st.session_state.filter_inboxes:
            active_filters += 1
        if st.session_state.filter_status_list:
            active_filters += 1
        if st.session_state.filter_classificacao:
            active_filters += 1
        if st.session_state.filter_score_min > 0:
            active_filters += 1

        if active_filters > 0:
            st.caption(f"✅ {active_filters} filtro(s) ativo(s)")
        else:
            st.caption("ℹ️ Nenhum filtro aplicado")

    st.divider()

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        st.info("ℹ️ Nenhum lead encontrado no período selecionado")
        return

    # Selecionar colunas genéricas multi-tenant (incluindo conversa_compilada) [FASE 6]
    display_df = leads_df[[
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'inbox_name',
        'conversation_date',
        'is_lead',
        'visit_scheduled',
        'crm_converted',
        'ai_probability_label',
        'ai_probability_score',
        'nome_mapeado_bot',
        'conversa_compilada'  # [FASE 6 - NOVO]
    ]].copy()

    # Adicionar coluna de prévia da conversa [FASE 6]
    display_df['preview_conversa'] = display_df['conversa_compilada'].apply(lambda x: format_message_preview(x, max_messages=3))

    # Renomear colunas
    display_df_view = display_df[[
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'inbox_name',
        'conversation_date',
        'is_lead',
        'visit_scheduled',
        'crm_converted',
        'ai_probability_label',
        'ai_probability_score',
        'nome_mapeado_bot',
        'preview_conversa'
    ]].copy()

    display_df_view.columns = [
        'ID',
        'Nome',
        'Telefone',
        'Inbox',
        'Data',
        'Lead',
        'Visita',
        'CRM',
        'Classificação IA',
        'Score IA',
        'Nome Mapeado',
        'Prévia Conversa'  # [FASE 6 - NOVO]
    ]

    # Formatar colunas booleanas
    display_df_view['Lead'] = display_df_view['Lead'].apply(lambda x: '✅' if x else '❌')
    display_df_view['Visita'] = display_df_view['Visita'].apply(lambda x: '✅' if x else '❌')
    display_df_view['CRM'] = display_df_view['CRM'].apply(lambda x: '✅' if x else '❌')

    # Formatar score
    display_df_view['Score IA'] = display_df_view['Score IA'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")

    # Exibir tabela
    st.dataframe(display_df_view, use_container_width=True, hide_index=True)

    st.divider()

    # === CONVERSAS COMPLETAS (EXPANDERS) === [FASE 6 - NOVO]
    st.markdown("#### 💬 Ver Conversas Completas")

    # Limitar a 10 conversas para não sobrecarregar a UI
    max_conversations_to_show = min(10, len(leads_df))

    if max_conversations_to_show > 0:
        st.caption(f"📊 Exibindo até {max_conversations_to_show} conversas (primeiros {max_conversations_to_show} leads da tabela)")

        # Iterar sobre os primeiros N leads
        for idx, row in leads_df.head(max_conversations_to_show).iterrows():
            conversation_id = row['conversation_display_id']
            contact_name = row['contact_name'] or "Sem nome"
            message_compiled = row['conversa_compilada']

            # Renderizar modal/expander para cada conversa
            render_conversation_modal(conversation_id, message_compiled, contact_name)
    else:
        st.info("ℹ️ Nenhuma conversa disponível para exibição")

    # REMOVIDO: Modal de Análise IA Detalhada (específico AllpFit)
    # Ver: src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py → render_allpfit_ai_analysis_modal()


# ============================================================================
# TELA PRINCIPAL
# ============================================================================

def show_client_dashboard(session, tenant_id=None):
    """
    Dashboard do cliente (ou admin visualizando cliente específico)

    Args:
        session: Dados da sessão
        tenant_id: Se admin, pode visualizar tenant específico (opcional)
                   Se None, usa tenant_id da sessão

    Features:
    - Header com nome do tenant e role
    - Filtros de data
    - KPIs principais
    - Gráfico de leads por dia
    - Tabela de leads
    - RLS configurado automaticamente
    """

    # Determinar qual tenant mostrar
    if session['role'] in ['super_admin', 'admin'] and session['tenant_id'] == 0 and tenant_id:
        # Admin visualizando cliente específico
        display_tenant_id = tenant_id
        tenant_info = get_tenant_info(display_tenant_id)

        if not tenant_info:
            st.error(f"❌ Cliente não encontrado (ID: {tenant_id})")
            st.stop()

        tenant_name = tenant_info['name']
        show_back_button = True
    else:
        # Cliente vendo seus próprios dados
        display_tenant_id = session['tenant_id']
        tenant_name = session['tenant_name']
        show_back_button = False
        # Buscar info do tenant para exibir no expander
        tenant_info = get_tenant_info(display_tenant_id)

    # Configurar RLS para o tenant correto
    engine = get_database_engine()
    set_rls_context(engine, display_tenant_id, session['user_id'])

    # Header
    action = render_header(session, tenant_name, show_back=show_back_button)

    # Processar ações
    if action == 'back':
        # Voltar ao painel admin
        if 'selected_tenant_id' in st.session_state:
            del st.session_state['selected_tenant_id']
        st.rerun()

    elif action == 'logout':
        # Logout
        logout_user(engine, session['session_id'])
        clear_session_state()
        st.rerun()

    st.divider()

    # === INICIALIZAR SESSION STATE DOS FILTROS RÁPIDOS === [FASE 4]
    if 'filter_nome' not in st.session_state:
        st.session_state.filter_nome = ""
    if 'filter_telefone' not in st.session_state:
        st.session_state.filter_telefone = ""
    if 'filter_inboxes' not in st.session_state:
        st.session_state.filter_inboxes = []
    if 'filter_status_list' not in st.session_state:
        st.session_state.filter_status_list = []
    if 'filter_classificacao' not in st.session_state:
        st.session_state.filter_classificacao = []
    if 'filter_score_min' not in st.session_state:
        st.session_state.filter_score_min = 0.0

    # === FILTROS DE DATA E INBOX ===
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

    with col1:
        # Indicador de próxima atualização automática
        from multi_tenant.utils.etl_schedule import get_next_etl_time, format_etl_countdown
        next_info = get_next_etl_time()
        st.caption(format_etl_countdown(next_info))

    with col2:
        date_start = st.date_input(
            "Início",
            value=datetime.now() - timedelta(days=30),
            key="date_start"
        )

    with col3:
        date_end = st.date_input(
            "Fim",
            value=datetime.now(),
            key="date_end"
        )

    with col4:
        # Placeholder para filtro de inbox (será populado após carregar dados)
        inbox_filter_placeholder = st.empty()

    # === CARREGAR DADOS (SEM FILTRO DE INBOX PRIMEIRO) ===
    with st.spinner("🔄 Carregando dados..."):
        df_original = load_conversations(display_tenant_id, date_start, date_end, inbox_filter=None)

    if df_original.empty:
        st.warning("⚠️ Nenhum dado encontrado para o período selecionado")
        st.info("""
            **Possíveis motivos:**
            - Ainda não foi executado o ETL para este cliente
            - O período selecionado não possui conversas
            - Os dados ainda estão sendo sincronizados

            **Próximos passos:**
            - Aguardar a Fase 3 (ETL Multi-Tenant) para popular os dados
            - Verificar se os inboxes estão mapeados corretamente
        """)
        st.stop()

    # === RENDERIZAR FILTRO DE INBOX COM DADOS REAIS ===
    # Extrair inboxes reais dos dados carregados
    inbox_names_real = sorted(df_original['inbox_name'].dropna().unique().tolist())
    inbox_options_real = ["Todas as Inboxes"] + inbox_names_real

    # Inicializar session state
    if 'inbox_filter_global' not in st.session_state:
        st.session_state['inbox_filter_global'] = "Todas as Inboxes"

    # Renderizar selectbox no placeholder
    with inbox_filter_placeholder:
        selected_inbox_name = st.selectbox(
            "Inbox",
            options=inbox_options_real,
            key="inbox_filter_global"
        )

    # === APLICAR FILTROS RÁPIDOS === [FASE 4 - NOVO]
    df_filtered = df_original.copy()

    # NOVO: Filtro por Inbox Global (selecionado no topo)
    if selected_inbox_name != "Todas as Inboxes":
        df_filtered = df_filtered[df_filtered['inbox_name'] == selected_inbox_name]

    # Filtro por Nome (busca parcial, case-insensitive)
    if st.session_state.filter_nome:
        df_filtered = df_filtered[
            df_filtered['contact_name'].str.contains(st.session_state.filter_nome, case=False, na=False)
        ]

    # Filtro por Telefone (busca parcial)
    if st.session_state.filter_telefone:
        df_filtered = df_filtered[
            df_filtered['contact_phone'].str.contains(st.session_state.filter_telefone, na=False)
        ]

    # Filtro por Inboxes (multi-select)
    if st.session_state.filter_inboxes:
        df_filtered = df_filtered[df_filtered['inbox_name'].isin(st.session_state.filter_inboxes)]

    # Filtro por Status (multi-select)
    if st.session_state.filter_status_list:
        status_map_filter = {"Aberta": 0, "Resolvida": 1, "Pendente": 2}
        status_values = [status_map_filter[s] for s in st.session_state.filter_status_list if s in status_map_filter]
        df_filtered = df_filtered[df_filtered['conversation_status'].isin(status_values)]

    # Filtro por Classificação IA (multi-select)
    if st.session_state.filter_classificacao:
        df_filtered = df_filtered[df_filtered['ai_probability_label'].isin(st.session_state.filter_classificacao)]

    # Filtro por Score IA mínimo (slider)
    if st.session_state.filter_score_min > 0:
        df_filtered = df_filtered[
            (df_filtered['ai_probability_score'].notna()) &
            (df_filtered['ai_probability_score'] >= st.session_state.filter_score_min)
        ]

    # Usar DataFrame filtrado para o restante do dashboard
    df = df_filtered

    # === MÉTRICAS ===
    metrics = calculate_metrics(df)
    render_kpis(metrics)

    st.divider()

    # === ANÁLISE POR INBOX === [FASE 5 - NOVO]
    render_inbox_analysis(df)

    st.divider()

    # === GRÁFICOS ===
    st.subheader("📊 Análise de Leads")

    # Linha 1: Leads por dia (largura completa)
    leads_by_day = prepare_leads_by_day(df)
    render_leads_chart(leads_by_day, df_full=df)

    st.divider()

    # Linha 2: Leads por inbox + Distribuição de Score (lado a lado)
    col1, col2 = st.columns(2)

    with col1:
        leads_by_inbox = prepare_leads_by_inbox(df)
        render_leads_by_inbox_chart(leads_by_inbox)

    with col2:
        score_dist = prepare_score_distribution(df)
        render_score_distribution_chart(score_dist)

    st.divider()

    # === DISTRIBUIÇÃO POR PERÍODO === [FASE 5.5 - NOVO]
    period_dist = prepare_period_distribution(df)
    render_period_distribution_chart(period_dist)

    st.divider()

    # === TABELA DE LEADS ===
    render_leads_table(df, df_original, tenant_name, date_start, date_end)

    st.divider()

    # === INFORMAÇÕES ADICIONAIS ===
    with st.expander("ℹ️ Informações do Cliente"):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Nome:** {tenant_name}")
            st.write(f"**Slug:** `{session['tenant_slug']}`")
            st.write(f"**Status:** {tenant_info['status'] if tenant_info else 'N/A'}")

        with col2:
            st.write(f"**Plano:** {tenant_info['plan'] if tenant_info else 'N/A'}")
            st.write(f"**Inboxes:** {len(tenant_info['inbox_ids']) if tenant_info else 0}")
            st.write(f"**Período:** {date_start.strftime('%d/%m/%Y')} - {date_end.strftime('%d/%m/%Y')}")


# ============================================================================
# TESTES LOCAIS
# ============================================================================

if __name__ == "__main__":
    # Configurar página
    st.set_page_config(
        page_title="Dashboard Cliente - GeniAI",
        page_icon="📊",
        layout="wide"
    )

    # Aplicar CSS do config.py
    from app.config import apply_custom_css
    apply_custom_css()

    # Simular sessão de cliente (para teste local)
    if 'user' not in st.session_state:
        st.session_state['user'] = {
            'user_id': 3,
            'tenant_id': 1,
            'tenant_name': 'AllpFit CrossFit',
            'tenant_slug': 'allpfit',
            'full_name': 'Isaac Santos',
            'role': 'admin',
            'session_id': 'test-session-id',
        }

    session = st.session_state['user']
    show_client_dashboard(session)