"""
Painel Admin - Multi-Tenant
Fase 2 - GeniAI Analytics
Permite admins GeniAI selecionarem qual cliente visualizar
"""

import streamlit as st
from pathlib import Path
import sys
from sqlalchemy import text

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import get_database_engine, logout_user
from multi_tenant.auth.middleware import clear_session_state


# ============================================================================
# QUERIES DE DADOS
# ============================================================================

def get_active_tenants():
    """
    Retorna lista de tenants ativos (exceto GeniAI Admin)

    Returns:
        list[dict]: Lista de tenants com estatísticas
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            t.id,
            t.name,
            t.slug,
            t.inbox_ids,
            t.status,
            t.plan,
            t.created_at,
            (SELECT COUNT(*) FROM users WHERE tenant_id = t.id AND deleted_at IS NULL) AS user_count,
            (SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = t.id) AS conversation_count,
            (SELECT COUNT(DISTINCT contact_id) FROM conversations_analytics WHERE tenant_id = t.id AND contact_id IS NOT NULL) AS lead_count,
            (SELECT MAX(etl_updated_at) FROM conversations_analytics WHERE tenant_id = t.id) AS last_sync
        FROM tenants t
        WHERE t.deleted_at IS NULL
          AND t.id != 0  -- Excluir GeniAI Admin
        ORDER BY t.name
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        tenants = []

        for row in result:
            tenants.append({
                'id': row.id,
                'name': row.name,
                'slug': row.slug,
                'inbox_ids': row.inbox_ids,
                'status': row.status,
                'plan': row.plan,
                'created_at': row.created_at,
                'user_count': row.user_count or 0,
                'conversation_count': row.conversation_count or 0,
                'lead_count': row.lead_count or 0,
                'last_sync': row.last_sync,
            })

        return tenants


def get_global_metrics():
    """
    Retorna métricas agregadas de todos os clientes

    Returns:
        dict: Métricas globais
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            (SELECT COUNT(*) FROM tenants WHERE status = 'active' AND id != 0) AS active_tenants,
            (SELECT COUNT(*) FROM conversations_analytics) AS total_conversations,
            (SELECT COUNT(DISTINCT contact_id) FROM conversations_analytics WHERE contact_id IS NOT NULL) AS total_leads,
            (SELECT COUNT(*) FROM conversations_analytics WHERE status = 1) AS total_visits
        FROM tenants
        LIMIT 1
    """)

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

        if result:
            return {
                'active_tenants': result.active_tenants or 0,
                'total_conversations': result.total_conversations or 0,
                'total_leads': result.total_leads or 0,
                'total_visits': result.total_visits or 0,
            }

        return {
            'active_tenants': 0,
            'total_conversations': 0,
            'total_leads': 0,
            'total_visits': 0,
        }


# ============================================================================
# COMPONENTES UI
# ============================================================================

def render_global_metrics(metrics):
    """
    Renderiza métricas globais (overview)

    Args:
        metrics: Dict com métricas agregadas
    """
    st.subheader("📊 Overview Geral")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Clientes Ativos", metrics['active_tenants'])

    with col2:
        st.metric("Conversas Totais", f"{metrics['total_conversations']:,}".replace(',', '.'))

    with col3:
        st.metric("Leads Totais", f"{metrics['total_leads']:,}".replace(',', '.'))

    with col4:
        # Calcular taxa de conversão
        if metrics['total_conversations'] > 0:
            conversion_rate = (metrics['total_leads'] / metrics['total_conversations']) * 100
            st.metric("Taxa Conversão", f"{conversion_rate:.1f}%")
        else:
            st.metric("Taxa Conversão", "0%")


def render_tenant_card(tenant):
    """
    Renderiza card de um cliente

    Args:
        tenant: Dict com dados do tenant
    """
    with st.container():
        # Cabeçalho do card
        col1, col2 = st.columns([3, 1])

        with col1:
            # Nome e status
            status_emoji = "✅" if tenant['status'] == 'active' else "⚠️"
            st.markdown(f"### {status_emoji} {tenant['name']}")
            st.caption(f"Slug: `{tenant['slug']}` | Plano: **{tenant['plan']}**")

        with col2:
            # Botão Ver Dashboard
            if st.button("📊 Ver Dashboard", key=f"dash_{tenant['id']}", use_container_width=True):
                # Armazenar tenant selecionado
                st.session_state['selected_tenant_id'] = tenant['id']
                st.rerun()

        # Métricas do card
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Inboxes", len(tenant['inbox_ids']))

        with col2:
            st.metric("Usuários", tenant['user_count'])

        with col3:
            st.metric("Conversas", f"{tenant['conversation_count']:,}".replace(',', '.'))

        with col4:
            st.metric("Leads", f"{tenant['lead_count']:,}".replace(',', '.'))

        # Última sincronização
        if tenant['last_sync']:
            from datetime import datetime, timedelta

            # Converter UTC para SP
            last_sync_sp = tenant['last_sync'] - timedelta(hours=3)
            sync_str = last_sync_sp.strftime('%d/%m/%Y %H:%M')

            st.caption(f"📅 Última Sincronização: {sync_str}")
        else:
            st.caption("📅 Última Sincronização: Nenhuma")

        st.divider()


# ============================================================================
# TELA PRINCIPAL
# ============================================================================

def show_admin_panel(session):
    """
    Painel de administração GeniAI

    Permite:
    - Ver overview geral (métricas agregadas)
    - Listar todos os clientes
    - Selecionar um cliente para visualizar dashboard

    Args:
        session: Dados da sessão (user_id, tenant_id, role, etc.)
    """

    # Header
    col1, col2 = st.columns([5, 1])

    with col1:
        st.title("🎛️ Painel Admin GeniAI")
        st.caption(f"Bem-vindo, {session['full_name']} | {session['role']}")

    with col2:
        if st.button("🚪 Sair", use_container_width=True):
            engine = get_database_engine()
            logout_user(engine, session['session_id'])
            clear_session_state()
            st.rerun()

    st.divider()

    # Carregar dados
    with st.spinner("🔄 Carregando dados..."):
        metrics = get_global_metrics()
        tenants = get_active_tenants()

    # Overview Geral
    render_global_metrics(metrics)

    st.divider()

    # Lista de Clientes
    st.subheader("👥 Clientes")

    if not tenants:
        st.info("ℹ️ Nenhum cliente cadastrado ainda.")
        st.markdown("""
            **Próximos passos:**
            - Adicionar clientes na Fase 5 (Dashboard Admin completo)
            - Por enquanto, apenas visualização dos clientes existentes
        """)
    else:
        # Renderizar cards dos clientes
        for tenant in tenants:
            render_tenant_card(tenant)

    st.divider()

    # Gerenciamento (placeholder - Fase 5)
    st.subheader("⚙️ Gerenciamento")
    st.info("🚧 Gerenciar clientes (adicionar, editar, remover) será implementado na Fase 5")


# ============================================================================
# TESTES LOCAIS
# ============================================================================

if __name__ == "__main__":
    # Configurar página
    st.set_page_config(
        page_title="Painel Admin - GeniAI",
        page_icon="🎛️",
        layout="wide"
    )

    # Aplicar CSS do config.py
    from app.config import apply_custom_css
    apply_custom_css()

    # Simular sessão de admin (para teste local)
    if 'user' not in st.session_state:
        st.session_state['user'] = {
            'user_id': 1,
            'tenant_id': 0,
            'full_name': 'Administrador GeniAI',
            'role': 'super_admin',
            'session_id': 'test-session-id',
        }

    session = st.session_state['user']
    show_admin_panel(session)
