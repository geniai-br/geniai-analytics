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
        tenant_id: ID do tenant (IMPORTANTE: usado como chave de cache!)
        date_start: Data início do filtro (opcional)
        date_end: Data fim do filtro (opcional)

    Returns:
        pd.DataFrame: Conversas do tenant
    """
    # IMPORTANTE: Configurar RLS DENTRO da função para garantir cache correto por tenant
    engine = get_database_engine()
    set_rls_context(engine, tenant_id, tenant_id)  # Usar tenant_id como user_id temporário

    # Query base (RLS filtra automaticamente por tenant_id)
    query = """
        SELECT
            id,
            conversation_id,
            display_id as conversation_display_id,
            inbox_id,
            inbox_name,
            contact_id,  -- [FASE 7.2 - NOVO: Para contar leads únicos]
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
            message_compiled as conversa_compilada,
            -- FASE 8: Colunas de Análise de Remarketing
            tipo_conversa,
            analise_ia,
            sugestao_disparo,
            score_prioridade,
            dados_extraidos_ia,
            metadados_analise_ia,
            analisado_em
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


def get_total_leads_count(tenant_id):
    """
    Retorna contagem TOTAL de leads únicos do tenant (SEM filtro de data)
    Para exibir no card de métricas

    DEFINIÇÃO DE LEAD: Contatos com is_lead=TRUE (probabilidade IA >= 2)
    Não inclui contatos que apenas entraram em contato mas não foram qualificados pela IA

    Args:
        tenant_id: ID do tenant

    Returns:
        int: Número de leads únicos (contatos com is_lead=TRUE)
    """
    engine = get_database_engine()

    # IMPORTANTE: Filtro explícito de tenant_id necessário (RLS não está filtrando sozinho)
    query = text("""
        SELECT COUNT(DISTINCT contact_id) as total_leads
        FROM conversations_analytics
        WHERE tenant_id = :tenant_id
          AND is_lead = TRUE
          AND contact_id IS NOT NULL
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id}).fetchone()
        return result[0] if result else 0


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

    # [FASE 7.2 - CORREÇÃO: Contar CONTATOS ÚNICOS como leads, não conversas]
    # Problema: estava contando conversas (394), não pessoas únicas (1306)
    # Solução: usar contact_id único para contar leads
    if 'contact_id' in df.columns:
        leads_df = df[df['is_lead'] == True]
        unique_leads = leads_df['contact_id'].nunique() if not leads_df.empty else 0
    else:
        unique_leads = len(df[df['is_lead'] == True])  # Fallback

    # Métricas Existentes
    metrics = {
        'total_contacts': total,
        'unique_contacts': unique_contacts,  # NOVO: contatos únicos
        'ai_conversations': len(df[df['has_human_intervention'] == False]) if 'has_human_intervention' in df.columns else len(df[df['bot_messages'] > 0]),
        'human_conversations': len(df[df['has_human_intervention'] == True]) if 'has_human_intervention' in df.columns else 0,
        'leads': unique_leads,  # [FASE 7.2 - ALTERADO: contatos únicos, não conversas]
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


def render_kpis(metrics, total_leads_no_filter=None):
    """
    Renderiza KPIs principais (cards de métricas)

    Args:
        metrics: Dict com métricas calculadas (do período filtrado)
        total_leads_no_filter: Total de leads únicos SEM filtro de data (opcional)
    """
    # Linha 1: Métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Contatos", format_number(metrics['total_contacts']))

    with col2:
        # [FASE 7.2 - CORREÇÃO FINAL: Mostrar leads TOTAIS sem filtro de data]
        # Se total_leads_no_filter for fornecido, usar ele (ignora filtro de data)
        # Caso contrário, usar do dataframe filtrado
        leads_count = total_leads_no_filter if total_leads_no_filter is not None else metrics['leads']
        st.metric("Leads", format_number(leads_count))

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

def format_conversation_readable(message_compiled_json, contact_name="Lead"):
    """
    Formata a conversa compilada (JSON) em formato legível de chat
    [FASE 7.2 - ADAPTADO do single-tenant para multi-tenant]

    Args:
        message_compiled_json: String JSON ou objeto Python com as mensagens
        contact_name: Nome do contato (padrão: "Lead")

    Returns:
        String formatada como chat legível
    """
    import json

    if not message_compiled_json:
        return "Conversa vazia"

    # Se for string JSON, converter para objeto Python
    if isinstance(message_compiled_json, str):
        try:
            messages = json.loads(message_compiled_json)
        except:
            return message_compiled_json
    else:
        messages = message_compiled_json

    if not messages or not isinstance(messages, list):
        return "Conversa vazia"

    formatted_lines = []

    for msg in messages:
        # Pular mensagens do sistema (message_type 2 ou 3)
        if msg.get('message_type') in [2, 3]:
            continue

        # Pular mensagens privadas
        if msg.get('private', False):
            continue

        text = msg.get('text', '')
        if text is None:
            text = ''
        text = text.strip()
        if not text:
            continue

        sender = msg.get('sender', 'Unknown')
        sender_name_from_msg = msg.get('sender_name', '')  # Nome do atendente se houver
        sent_at = msg.get('sent_at')

        # Determinar quem enviou (GENÉRICO para multi-tenant)
        if sender == 'Contact':
            sender_name = f"Lead ({contact_name})"
        elif sender == 'AgentBot':
            sender_name = "Bot (IA)"
        elif sender == 'User':
            # Atendente humano - mostrar nome se disponível
            if sender_name_from_msg:
                sender_name = f"Atendente ({sender_name_from_msg})"
            else:
                sender_name = "Atendente"
        elif sender == 'Agent':
            sender_name = "Atendente"
        elif sender is None or sender == 'Bot':
            sender_name = "Bot (IA)"
        else:
            sender_name = sender

        # Formatar data/hora
        if sent_at:
            try:
                # Parse ISO format
                dt = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                # Converter UTC para SP (UTC-3)
                dt_sp = dt - timedelta(hours=3)
                date_str = dt_sp.strftime('%d/%m/%Y %H:%M')
            except:
                date_str = sent_at
        else:
            date_str = "Data desconhecida"

        # Adicionar linha formatada
        formatted_lines.append(f"{sender_name}: {text}")
        formatted_lines.append(f"Enviado: {date_str}")
        formatted_lines.append("")  # Linha em branco entre mensagens

    return "\n".join(formatted_lines) if formatted_lines else "Conversa vazia"


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

    # === PAGINAÇÃO === [FASE 7.2 - NOVO]
    # Inicializar estado de paginação
    if 'leads_page' not in st.session_state:
        st.session_state.leads_page = 1

    # Configuração de paginação
    LEADS_PER_PAGE = 50
    total_leads = len(leads_df)
    total_pages = (total_leads + LEADS_PER_PAGE - 1) // LEADS_PER_PAGE  # Arredonda para cima

    # Garantir que a página atual está dentro dos limites
    if st.session_state.leads_page > total_pages and total_pages > 0:
        st.session_state.leads_page = total_pages
    if st.session_state.leads_page < 1:
        st.session_state.leads_page = 1

    # Calcular offset
    offset = (st.session_state.leads_page - 1) * LEADS_PER_PAGE

    # Paginar os dados
    leads_paginated = leads_df.iloc[offset:offset + LEADS_PER_PAGE].copy()

    # === HEADER COM PAGINAÇÃO ===
    col_info, col_nav = st.columns([3, 2])

    with col_info:
        start_record = offset + 1
        end_record = min(offset + LEADS_PER_PAGE, total_leads)
        st.info(f"📊 Mostrando **{start_record}-{end_record}** de **{total_leads}** leads | Página **{st.session_state.leads_page}** de **{total_pages}**")

    with col_nav:
        # Controles de navegação
        col_prev, col_page_input, col_next = st.columns([1, 2, 1])

        with col_prev:
            if st.button("◀️ Anterior", disabled=(st.session_state.leads_page == 1), use_container_width=True):
                st.session_state.leads_page -= 1
                st.rerun()

        with col_page_input:
            # Input direto de página
            page_input = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.leads_page,
                step=1,
                key="page_input",
                label_visibility="collapsed",
                help="Ir para página específica"
            )
            if page_input != st.session_state.leads_page:
                st.session_state.leads_page = page_input
                st.rerun()

        with col_next:
            if st.button("Próximo ▶️", disabled=(st.session_state.leads_page >= total_pages), use_container_width=True):
                st.session_state.leads_page += 1
                st.rerun()

    st.divider()

    # === PREPARAR DADOS DA TABELA === [FASE 7.2]
    # Selecionar colunas genéricas multi-tenant (incluindo conversa_compilada) [FASE 6]
    # FASE 7: Remover colunas LEAD, CRM, VISITA, SCORE e CLASSIFICAÇÃO IA (2025-11-13)
    # FASE 7.1: Adicionar Primeira/Última Conversa, remover Data (2025-11-13)
    # FASE 7.2: Adicionar Conversa Completa formatada, remover prévia e expanders (2025-11-13)
    display_df = leads_paginated[[
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'inbox_name',
        'primeiro_contato',  # [FASE 7.1 - NOVO]
        'ultimo_contato',    # [FASE 7.1 - NOVO]
        'nome_mapeado_bot',
        'conversa_compilada'  # [FASE 6 - NOVO]
    ]].copy()

    # Formatar conversa completa (igual single-tenant) [FASE 7.2 - NOVO]
    display_df['conversa_formatada'] = display_df.apply(
        lambda row: format_conversation_readable(row['conversa_compilada'], row['contact_name'] or "Lead"),
        axis=1
    )

    # Selecionar colunas para visualização
    display_df_view = display_df[[
        'conversation_display_id',
        'contact_name',
        'contact_phone',
        'inbox_name',
        'primeiro_contato',
        'ultimo_contato',
        'nome_mapeado_bot',
        'conversa_formatada'  # [FASE 7.2 - NOVO: Conversa completa substituindo prévia]
    ]].copy()

    display_df_view.columns = [
        'ID',
        'Nome',
        'Telefone',
        'Inbox',
        'Primeira Conversa',  # [FASE 7.1 - NOVO]
        'Última Conversa',    # [FASE 7.1 - NOVO]
        'Nome Mapeado',
        'Conversa Completa'  # [FASE 7.2 - NOVO: Coluna completa na tabela]
    ]

    # REMOVIDO (FASE 7): Formatação de colunas booleanas (Lead, Visita, CRM)
    # REMOVIDO (FASE 7): Formatação de Score IA
    # REMOVIDO (FASE 7.2): Expanders de conversas completas (agora na tabela)

    # Exibir tabela com conversa completa
    st.dataframe(
        display_df_view,
        use_container_width=True,
        hide_index=True,
        height=600,  # Altura maior para acomodar conversas completas
        column_config={
            "Conversa Completa": st.column_config.TextColumn(
                "Conversa Completa",
                width="large",
                help="Conversa completa formatada como chat"
            )
        }
    )

    # REMOVIDO: Modal de Análise IA Detalhada (específico AllpFit)
    # Ver: src/multi_tenant/dashboards/_archived/allpfit_specific_functions.py → render_allpfit_ai_analysis_modal()


# ============================================================================
# ANÁLISE DE REMARKETING [FASE 8]
# ============================================================================

def calculate_inactivity_hours(ultimo_contato):
    """
    Calcula horas de inatividade desde última mensagem

    Args:
        ultimo_contato: Timestamp da última mensagem

    Returns:
        float: Horas de inatividade (ou None se não disponível)
    """
    if pd.isna(ultimo_contato):
        return None

    now = datetime.now()
    if isinstance(ultimo_contato, str):
        ultimo_contato = pd.to_datetime(ultimo_contato)

    delta = now - ultimo_contato
    return delta.total_seconds() / 3600


def format_inactivity_time(horas):
    """
    Formata tempo de inatividade de forma legível

    Args:
        horas: Horas de inatividade

    Returns:
        str: Tempo formatado (ex: "2d 5h", "1sem")
    """
    if pd.isna(horas) or horas is None:
        return "-"

    if horas < 24:
        return f"{int(horas)}h"
    elif horas < 168:  # < 7 dias
        dias = int(horas // 24)
        horas_rest = int(horas % 24)
        return f"{dias}d {horas_rest}h"
    elif horas < 720:  # < 30 dias
        semanas = int(horas // 168)
        return f"{semanas}sem"
    else:  # 30+ dias
        meses = int(horas // 720)
        return f"{meses}mes"


def get_remarketing_status_badge(row):
    """
    Retorna badge de status de análise de remarketing

    Args:
        row: Linha do DataFrame com dados do lead

    Returns:
        str: Badge formatado
    """
    # Lead com análise completa
    if pd.notna(row.get('analisado_em')):
        return '✅ Analisado'

    # Calcular horas de inatividade
    horas_inativo = calculate_inactivity_hours(row.get('ultimo_contato'))

    if horas_inativo is None:
        return '⚠️ Sem data'

    # Lead inativo 24h+ (aguardando análise)
    if horas_inativo >= 24:
        return '⏳ Aguardando Análise'

    # Lead ativo (<24h)
    horas_restantes = int(24 - horas_inativo)
    return f'🔄 Ativo (análise em {horas_restantes}h)'


def format_tipo_remarketing_badge(tipo):
    """
    Formata tipo de remarketing como badge colorido

    Args:
        tipo: Tipo de remarketing

    Returns:
        str: Badge formatado
    """
    badges = {
        'REMARKETING_RECENTE': '🟢 Recente (24-48h)',
        'REMARKETING_MEDIO': '🟡 Médio (48h-7d)',
        'REMARKETING_FRIO': '🔴 Frio (7d+)',
    }
    return badges.get(tipo, '-')


def format_score_numerico(score):
    """
    Formata score de prioridade como número (0-5)

    Args:
        score: Score de 0 a 5

    Returns:
        str: Score numérico formatado ou '-' se inválido
    """
    if pd.isna(score) or score is None:
        return '-'

    score = int(score)
    if score < 0 or score > 5:
        return '-'

    return str(score)


def render_remarketing_analysis_section(df, tenant_id):
    """
    Renderiza seção de Análise de Remarketing (FASE 8)

    Features:
    - Cards de resumo (Analisados, Aguardando 24h, Ativos)
    - Filtro por tipo de remarketing
    - Tabela paginada com checkboxes de seleção
    - Botões de disparo (individual, selecionados, todos)
    - Expanders sincronizados com página atual

    Args:
        df: DataFrame com conversas (já filtrado)
        tenant_id: ID do tenant
    """
    st.subheader("🤖 Análise de Remarketing (Leads Inativos 24h+)")

    if df.empty:
        st.info("ℹ️ Nenhum dado disponível para análise de remarketing")
        return

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        st.info("ℹ️ Nenhum lead encontrado no período selecionado")
        return

    # Calcular tempo de inatividade para todos os leads
    leads_df['horas_inativo'] = leads_df['ultimo_contato'].apply(calculate_inactivity_hours)

    # Classificar leads
    analisados = len(leads_df[leads_df['analisado_em'].notna()])
    aguardando_24h = len(leads_df[(leads_df['horas_inativo'] >= 24) & (leads_df['analisado_em'].isna())])
    ativos = len(leads_df[leads_df['horas_inativo'] < 24])

    # === CARDS DE RESUMO ===
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "✅ Analisados",
            format_number(analisados),
            help="Leads inativos 24h+ com análise de remarketing"
        )

    with col2:
        st.metric(
            "⏳ Aguardando 24h",
            format_number(aguardando_24h),
            help="Leads inativos 24h+ sem análise (serão analisados no próximo ETL)"
        )

    with col3:
        st.metric(
            "🔄 Ativos",
            format_number(ativos),
            help="Leads com última msg < 24h (janela de follow-up manual)"
        )

    st.divider()

    # === FILTROS: TIPO E SCORE ===
    col_filter_tipo, col_filter_score, col_btn = st.columns([2, 1.5, 1.5])

    with col_filter_tipo:
        tipo_filter = st.multiselect(
            "🎯 Filtrar por Tipo de Remarketing:",
            options=['REMARKETING_RECENTE', 'REMARKETING_MEDIO', 'REMARKETING_FRIO'],
            default=[],
            format_func=lambda x: {
                'REMARKETING_RECENTE': '🟢 Recente (24-48h)',
                'REMARKETING_MEDIO': '🟡 Médio (48h-7d)',
                'REMARKETING_FRIO': '🔴 Frio (7d+)'
            }.get(x, x),
            key="tipo_remarketing_filter",
            help="Filtrar leads analisados por tipo de remarketing"
        )

    with col_filter_score:
        score_filter = st.slider(
            "⭐ Score Mínimo:",
            min_value=0,
            max_value=5,
            value=0,
            step=1,
            key="score_remarketing_filter",
            help="Filtrar por score de prioridade (0 = todos, 1-5 = mínimo)"
        )

    with col_btn:
        # Botão "Analisar Pendentes" (futuro - FASE 8.4)
        if aguardando_24h > 0:
            st.button(
                f"🤖 Analisar {aguardando_24h} Pendentes (24h+)",
                use_container_width=True,
                disabled=True,
                help="Em breve: Análise sob demanda de leads pendentes"
            )
        else:
            st.success("✅ Todos os leads inativos (24h+) foram analisados!")

    st.divider()

    # === APLICAR FILTROS ===
    leads_display = leads_df.copy()

    # Filtro por tipo
    if tipo_filter:
        leads_display = leads_display[leads_display['tipo_conversa'].isin(tipo_filter)]

    # Filtro por score mínimo
    if score_filter > 0:
        leads_display = leads_display[leads_display['score_prioridade'] >= score_filter]

    # === FILTRAR APENAS LEADS ANALISADOS ===
    leads_analisados = leads_display[leads_display['analisado_em'].notna()].copy()

    if leads_analisados.empty:
        st.info("ℹ️ Nenhum lead analisado encontrado")
        return

    # Ordenar por inatividade (mais recentes primeiro)
    leads_analisados = leads_analisados.sort_values('ultimo_contato', ascending=False)

    # Adicionar colunas formatadas
    leads_analisados['status_badge'] = leads_analisados.apply(get_remarketing_status_badge, axis=1)
    leads_analisados['tipo_badge'] = leads_analisados['tipo_conversa'].apply(format_tipo_remarketing_badge)
    leads_analisados['inatividade_formatada'] = leads_analisados['horas_inativo'].apply(format_inactivity_time)
    leads_analisados['score_visual'] = leads_analisados['score_prioridade'].apply(format_score_numerico)

    # === PAGINAÇÃO ===
    # Inicializar estado de paginação
    if 'remarketing_page' not in st.session_state:
        st.session_state.remarketing_page = 1

    # Configuração
    LEADS_PER_PAGE = 20
    total_leads = len(leads_analisados)
    total_pages = (total_leads + LEADS_PER_PAGE - 1) // LEADS_PER_PAGE

    # Garantir que página está dentro dos limites
    if st.session_state.remarketing_page > total_pages and total_pages > 0:
        st.session_state.remarketing_page = total_pages
    if st.session_state.remarketing_page < 1:
        st.session_state.remarketing_page = 1

    # Calcular offset
    offset = (st.session_state.remarketing_page - 1) * LEADS_PER_PAGE

    # Paginar
    leads_paginated = leads_analisados.iloc[offset:offset + LEADS_PER_PAGE].copy()

    # Inicializar seleção global (persiste entre páginas)
    if 'selected_remarketing_leads' not in st.session_state:
        st.session_state.selected_remarketing_leads = set()

    # === ABAS PRINCIPAIS ===
    tab1, tab2, tab3 = st.tabs(["📊 Tabela de Leads", "🔍 Análise Detalhada", "📤 Disparo"])

    # ========================================
    # ABA 1: TABELA DE LEADS
    # ========================================
    with tab1:
        # Checkbox "Selecionar todos" (página atual)
        col_select_all, col_info_selected = st.columns([1, 3])

        with col_select_all:
            # Verificar se TODOS da página atual estão selecionados
            page_ids = set(leads_paginated['conversation_id'].tolist())
            all_page_selected = page_ids.issubset(st.session_state.selected_remarketing_leads)

            select_all_page = st.checkbox(
                "Selecionar todos (página)",
                value=all_page_selected,
                key="select_all_remarketing_page",
                help="Selecionar/desselecionar todos os leads da página atual"
            )

            # Atualizar seleção
            if select_all_page:
                st.session_state.selected_remarketing_leads.update(page_ids)
            else:
                # Só desmarcar se o checkbox foi desmarcado pelo usuário
                if all_page_selected:
                    st.session_state.selected_remarketing_leads -= page_ids

        with col_info_selected:
            num_selected = len(st.session_state.selected_remarketing_leads)
            if num_selected > 0:
                st.caption(f"✅ **{num_selected}** lead(s) selecionado(s) (todas as páginas)")
            else:
                st.caption("ℹ️ Nenhum lead selecionado")

        st.divider()

        # === CABEÇALHO DA TABELA ===
        col_check_h, col_id_h, col_nome_h, col_tel_h, col_tipo_h, col_inativ_h, col_score_h = st.columns([0.5, 1, 2, 1.5, 2, 1, 0.8])

        with col_check_h:
            st.markdown("**☑️**")
        with col_id_h:
            st.markdown("**ID**")
        with col_nome_h:
            st.markdown("**Nome do Lead**")
        with col_tel_h:
            st.markdown("**Telefone**")
        with col_tipo_h:
            st.markdown("**Tipo de Remarketing**")
        with col_inativ_h:
            st.markdown("**Inatividade**")
        with col_score_h:
            st.markdown("**Score**")

        st.divider()

        # === LINHAS DA TABELA ===
        for idx, row in leads_paginated.iterrows():
            col_check, col_id, col_nome, col_tel, col_tipo, col_inativ, col_score = st.columns([0.5, 1, 2, 1.5, 2, 1, 0.8])

            conv_id = row['conversation_id']

            with col_check:
                # Checkbox individual
                is_selected = conv_id in st.session_state.selected_remarketing_leads
                selected = st.checkbox(
                    "Selecionar",
                    value=is_selected,
                    key=f"check_remarketing_{conv_id}",
                    label_visibility="collapsed",
                    help="Selecionar/desselecionar este lead para disparo"
                )

                # Atualizar seleção
                if selected:
                    st.session_state.selected_remarketing_leads.add(conv_id)
                else:
                    st.session_state.selected_remarketing_leads.discard(conv_id)

            with col_id:
                st.markdown(f"**#{row['conversation_display_id']}**")

            with col_nome:
                st.markdown(row['contact_name'])

            with col_tel:
                st.markdown(f"`{row['contact_phone']}`")

            with col_tipo:
                st.markdown(row['tipo_badge'])

            with col_inativ:
                st.markdown(row['inatividade_formatada'])

            with col_score:
                st.markdown(f"**{row['score_visual']}**/5")

        st.divider()

        # === CONTROLES DE PAGINAÇÃO ===
        col_info, col_nav = st.columns([3, 2])

        with col_info:
            start_record = offset + 1
            end_record = min(offset + LEADS_PER_PAGE, total_leads)
            st.info(f"📊 Mostrando **{start_record}-{end_record}** de **{total_leads}** leads | Página **{st.session_state.remarketing_page}** de **{total_pages}**")

        with col_nav:
            col_prev, col_page_input, col_next = st.columns([1, 2, 1])

            with col_prev:
                if st.button("◀️ Anterior", disabled=(st.session_state.remarketing_page == 1), use_container_width=True, key="remarketing_prev"):
                    st.session_state.remarketing_page -= 1
                    st.rerun()

            with col_page_input:
                page_input = st.number_input(
                    "Página de remarketing",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.remarketing_page,
                    step=1,
                    key="remarketing_page_input",
                    label_visibility="collapsed",
                    help="Ir para página específica"
                )
                if page_input != st.session_state.remarketing_page:
                    st.session_state.remarketing_page = page_input
                    st.rerun()

            with col_next:
                if st.button("Próximo ▶️", disabled=(st.session_state.remarketing_page >= total_pages), use_container_width=True, key="remarketing_next"):
                    st.session_state.remarketing_page += 1
                    st.rerun()

    # ========================================
    # ABA 2: ANÁLISE DETALHADA
    # ========================================
    with tab2:
        st.info(f"📋 Mostrando análise detalhada dos **{len(leads_paginated)}** leads da página atual")

        for idx, row in leads_paginated.iterrows():
            with st.expander(
                f"💬 {row['contact_name']} (ID: #{row['conversation_display_id']}) - Score: {row['score_visual']}/5",
                expanded=False
            ):
                col_info, col_score = st.columns([3, 1])

                with col_info:
                    st.markdown(f"**📞 Telefone:** {row['contact_phone']}")
                    st.markdown(f"**⏰ Inatividade:** {row['inatividade_formatada']}")
                    st.markdown(f"**🎯 Tipo:** {row['tipo_badge']}")

                with col_score:
                    st.markdown(f"**⭐ Score:** {row['score_visual']}/5")
                    if pd.notna(row['analisado_em']):
                        st.caption(f"Analisado em: {row['analisado_em'].strftime('%d/%m %H:%M')}")

                st.divider()

                # Análise IA
                if pd.notna(row['analise_ia']):
                    st.markdown("**📝 Análise da IA:**")
                    st.info(row['analise_ia'])

                # Dados extraídos
                if pd.notna(row['dados_extraidos_ia']):
                    st.markdown("**📊 Dados Extraídos da Conversa:**")
                    import json
                    try:
                        dados = json.loads(row['dados_extraidos_ia']) if isinstance(row['dados_extraidos_ia'], str) else row['dados_extraidos_ia']

                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.markdown(f"- **Interesse mencionado:** {dados.get('interesse_mencionado', 'Não mencionado')}")
                            st.markdown(f"- **Nível de urgência:** {dados.get('urgencia', 'Não mencionado')}")
                        with col_d2:
                            objecoes = dados.get('objecoes', [])
                            st.markdown(f"- **Objeções levantadas:** {', '.join(objecoes) if objecoes else 'Nenhuma'}")
                    except:
                        st.caption("⚠️ Erro ao processar dados extraídos")

                # Sugestão de disparo
                if pd.notna(row['sugestao_disparo']):
                    st.markdown("**💬 Sugestão de Mensagem de Remarketing:**")
                    st.success(row['sugestao_disparo'])

                    # Botões de ação individual
                    col_copy, col_send = st.columns(2)

                    with col_copy:
                        st.button(
                            "📋 Copiar Sugestão",
                            key=f"copy_sugestao_{row['conversation_id']}",
                            disabled=True,
                            use_container_width=True,
                            help="Em breve: Copiar sugestão para clipboard"
                        )

                    with col_send:
                        st.button(
                            "📤 Disparar para este Lead",
                            key=f"send_individual_{row['conversation_id']}",
                            disabled=True,
                            use_container_width=True,
                            help="Em breve: Disparar mensagem diretamente para este lead"
                        )

                # Metadados (tokens e custo)
                if pd.notna(row['metadados_analise_ia']):
                    st.markdown("---")
                    st.markdown("**📊 Metadados da Análise:**")
                    try:
                        metadados = json.loads(row['metadados_analise_ia']) if isinstance(row['metadados_analise_ia'], str) else row['metadados_analise_ia']

                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.metric("Tokens Usados", format_number(metadados.get('tokens_total', 0)))
                        with col_m2:
                            custo = metadados.get('custo_brl', 0)
                            st.metric("Custo", f"R$ {custo:.4f}")
                        with col_m3:
                            st.metric("Modelo", metadados.get('modelo', 'N/A'))
                    except:
                        st.caption("⚠️ Erro ao processar metadados")

    # ========================================
    # ABA 3: DISPARO
    # ========================================
    with tab3:
        st.markdown("### 📤 Envio de Mensagens de Remarketing")

        num_selected = len(st.session_state.selected_remarketing_leads)

        # Info sobre seleção
        if num_selected > 0:
            st.success(f"✅ **{num_selected}** lead(s) selecionado(s) na tabela (todas as páginas)")
        else:
            st.warning("⚠️ Nenhum lead selecionado. Volte para a aba **Tabela de Leads** para selecionar leads.")

        st.divider()

        # Botões de disparo
        st.markdown("#### Opções de Disparo:")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            st.button(
                f"📤 Disparar para {num_selected} Selecionado(s)",
                use_container_width=True,
                disabled=True,
                help=f"Em breve: Disparar mensagens para os {num_selected} lead(s) selecionado(s) na tabela"
            )

        with col_btn2:
            st.button(
                f"📤 Disparar para TODOS ({total_leads})",
                use_container_width=True,
                disabled=True,
                help=f"Em breve: Disparar mensagens para TODOS os {total_leads} leads analisados (com confirmação)"
            )

        st.divider()

        # Gerenciar seleção
        st.markdown("#### Gerenciar Seleção:")

        col_clear, col_info_disp = st.columns([1, 3])

        with col_clear:
            if st.button("🗑️ Limpar Seleção", use_container_width=True):
                st.session_state.selected_remarketing_leads = set()
                st.rerun()

        with col_info_disp:
            if num_selected > 0:
                st.caption(f"💡 Use este botão para limpar os {num_selected} lead(s) selecionado(s)")
            else:
                st.caption("ℹ️ Selecione leads na aba **Tabela de Leads** antes de disparar")

        st.divider()

        # Informações adicionais
        st.markdown("#### ℹ️ Sobre o Disparo:")
        st.info("""
        **Como funciona:**
        1. Selecione os leads desejados na aba **Tabela de Leads** usando os checkboxes
        2. Volte para esta aba e escolha a opção de disparo
        3. As mensagens sugeridas pela IA serão enviadas automaticamente via WhatsApp

        **Status:** Esta funcionalidade será implementada em breve por Hyago
        """)


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
    # IMPORTANTE: Inicializar ANTES de detectar mudança de tenant
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

    # === DETECTAR MUDANÇA DE TENANT E RESETAR FILTROS === [BUGFIX]
    # Quando admin troca de tenant, os filtros do tenant anterior persistem
    # causando queries com 0 resultados (inboxes/status inexistentes)
    if 'last_viewed_tenant_id' not in st.session_state:
        st.session_state.last_viewed_tenant_id = display_tenant_id

    # Detectar mudança de tenant (comparação ocorre APÓS inicialização)
    if st.session_state.last_viewed_tenant_id != display_tenant_id:
        # Mudou de tenant - Resetar TODOS os filtros e estados
        st.session_state.filter_nome = ""
        st.session_state.filter_telefone = ""
        st.session_state.filter_inboxes = []
        st.session_state.filter_status_list = []
        st.session_state.filter_classificacao = []
        st.session_state.filter_score_min = 0.0
        # Resetar paginação
        if 'leads_page' in st.session_state:
            st.session_state.leads_page = 1
        if 'remarketing_page' in st.session_state:
            st.session_state.remarketing_page = 1
        # Resetar seleções de remarketing
        if 'selected_remarketing_leads' in st.session_state:
            st.session_state.selected_remarketing_leads = set()
        # IMPORTANTE: Limpar cache do Streamlit para forçar reload dos dados
        st.cache_data.clear()
        # Atualizar tenant atual
        st.session_state.last_viewed_tenant_id = display_tenant_id

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
            value=datetime.now() - timedelta(days=365),  # [FASE 7.2 - ALTERADO: 1 ano padrão para ver mais dados]
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
    # [FASE 7.2 - CORREÇÃO FINAL: Buscar total de leads SEM filtro de data]
    total_leads_all_time = get_total_leads_count(display_tenant_id)

    # Calcular métricas do período filtrado
    metrics = calculate_metrics(df)

    # Renderizar KPIs com total de leads SEM filtro
    render_kpis(metrics, total_leads_no_filter=total_leads_all_time)

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

    # === ANÁLISE DE REMARKETING === [FASE 8 - NOVO]
    render_remarketing_analysis_section(df, display_tenant_id)

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