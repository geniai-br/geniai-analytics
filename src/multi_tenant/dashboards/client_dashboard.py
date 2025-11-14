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
            -- Colunas OpenAI (FASE 5.6)
            nome_mapeado_bot,
            condicao_fisica,
            objetivo,
            probabilidade_conversao,
            analise_ia,
            sugestao_disparo
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
    Prepara dados de leads por dia para gráfico

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

    # Linha 2: Funil de conversão (visual)
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


def render_leads_chart(leads_by_day):
    """
    Renderiza gráfico de leads por dia

    Args:
        leads_by_day: DataFrame com leads agrupados por dia
    """
    if leads_by_day.empty:
        st.info("ℹ️ Nenhum lead para exibir no período selecionado")
        return

    # Usar Streamlit native chart (simples e rápido)
    st.subheader("📈 Leads por Dia")
    st.bar_chart(leads_by_day.set_index('Data')['Leads'], use_container_width=True)


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


def render_quality_metrics(metrics, df):
    """
    Renderiza métricas de qualidade (IA%, Resolução%, Tempo Resposta)
    [FASE 5.5 - NOVA FUNÇÃO]

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


def render_leads_table(df, tenant_name, date_start, date_end):
    """
    Renderiza tabela de leads com botão de exportação e modal de análise IA

    Args:
        df: DataFrame com conversas
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

    # Filtrar apenas leads
    leads_df = df[df['is_lead'] == True].copy()

    if leads_df.empty:
        st.info("ℹ️ Nenhum lead encontrado no período selecionado")
        return

    # Selecionar colunas relevantes (+ OpenAI FASE 5.6)
    # Criar cópia para exibição e manter dados completos para modal
    display_df = leads_df[[
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
    ]].copy()

    # Renomear colunas
    display_df.columns = [
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

    # Formatar colunas booleanas
    display_df['Lead'] = display_df['Lead'].apply(lambda x: '✅' if x else '❌')
    display_df['Visita'] = display_df['Visita'].apply(lambda x: '✅' if x else '❌')
    display_df['CRM'] = display_df['CRM'].apply(lambda x: '✅' if x else '❌')

    # Formatar score
    display_df['Score IA'] = display_df['Score IA'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")

    # Exibir tabela
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # === MODAL DE ANÁLISE IA DETALHADA === [FASE 5.6 - NOVO]
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
        # Filtro por Inbox
        tenant_inboxes = get_tenant_inboxes(display_tenant_id)

        # Opções do selectbox: "Todas as Inboxes" + inboxes do tenant
        inbox_options = ["Todas as Inboxes"] + [inbox['name'] for inbox in tenant_inboxes]

        # Inicializar valor padrão apenas uma vez
        if 'inbox_filter' not in st.session_state:
            st.session_state['inbox_filter'] = "Todas as Inboxes"

        # Selectbox com key direto (sem gerenciar index manualmente)
        selected_inbox_name = st.selectbox(
            "Inbox",
            options=inbox_options,
            key="inbox_filter"
        )

        # Converter nome para ID (se não for "Todas")
        selected_inbox_id = None
        if selected_inbox_name != "Todas as Inboxes":
            for inbox in tenant_inboxes:
                if inbox['name'] == selected_inbox_name:
                    selected_inbox_id = inbox['id']
                    break

    # === FILTROS OPENAI === [FASE 5.6 - NOVO]
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

    # Botão atualizar
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    # Indicador visual de filtro ativo
    active_filters = []
    if selected_inbox_id is not None:
        active_filters.append(f"Inbox: {selected_inbox_name}")
    if filter_openai:
        active_filters.append("Com Análise IA")
    if filter_high_prob:
        active_filters.append("Prob 4-5")
    if filter_visit:
        active_filters.append("Visita Agendada")
    if filter_classification != "Todas":
        active_filters.append(f"Classificação: {filter_classification}")

    if active_filters:
        st.info(f"🔍 **Filtros ativos:** {' | '.join(active_filters)}")

    st.divider()

    # === CARREGAR DADOS ===
    with st.spinner("🔄 Carregando dados..."):
        df = load_conversations(display_tenant_id, date_start, date_end, inbox_filter=selected_inbox_id)

    if df.empty:
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

    # === APLICAR FILTROS OPENAI === [FASE 5.6]
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

    # Usar dataframe filtrado para o restante do dashboard
    df = df_filtered

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados")
        st.info("💡 **Dica:** Tente remover alguns filtros para ver mais resultados")
        st.stop()

    # === MÉTRICAS ===
    metrics = calculate_metrics(df)
    render_kpis(metrics)

    st.divider()

    # === MÉTRICAS DE QUALIDADE === [FASE 5.5 - NOVO]
    render_quality_metrics(metrics, df)

    st.divider()

    # === GRÁFICOS ===
    st.subheader("📊 Análise de Leads")

    # Linha 1: Leads por dia (largura completa)
    leads_by_day = prepare_leads_by_day(df)
    render_leads_chart(leads_by_day)

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
    render_leads_table(df, tenant_name, date_start, date_end)

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