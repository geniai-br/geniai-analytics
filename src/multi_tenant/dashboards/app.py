"""
App Principal - Multi-Tenant
Fase 2 - GeniAI Analytics

Entry point da aplicação com roteamento inteligente baseado no role do usuário

Fluxos:
- Super Admin/Admin GeniAI (tenant_id=0) → Painel Admin → Dashboard específico
- Cliente (tenant_id≠0) → Dashboard direto
"""

import streamlit as st
from pathlib import Path
import sys

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth.middleware import require_authentication, is_authenticated
from multi_tenant.dashboards.login_page import show_login_page, apply_login_css
from multi_tenant.dashboards.admin_panel import show_admin_panel
from multi_tenant.dashboards.client_dashboard import show_client_dashboard
from app.config import apply_custom_css


# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

def configure_page():
    """Configura a página do Streamlit"""
    st.set_page_config(
        page_title="Analytics GeniAI - Multi-Tenant",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )


# ============================================================================
# ROUTER PRINCIPAL
# ============================================================================

def main():
    """
    App principal - Router

    Lógica de roteamento:
    1. Verifica autenticação
    2. Se não autenticado → Login
    3. Se autenticado:
       a. Super Admin/Admin GeniAI (tenant_id=0) → Painel Admin ou Dashboard selecionado
       b. Cliente (tenant_id≠0) → Dashboard direto
    """

    # Configurar página
    configure_page()

    # ========================================
    # STEP 1: VERIFICAR AUTENTICAÇÃO
    # ========================================

    authenticated = is_authenticated()

    # DEBUG temporário
    if 'authenticated' in st.session_state:
        st.sidebar.write(f"DEBUG: session_state.authenticated = {st.session_state['authenticated']}")
    if 'session_id' in st.session_state:
        st.sidebar.write(f"DEBUG: session_state.session_id = {st.session_state['session_id'][:8]}...")
    st.sidebar.write(f"DEBUG: is_authenticated() = {authenticated}")

    if not authenticated:
        # Não autenticado → Mostrar login
        apply_login_css()
        show_login_page()
        return

    # ========================================
    # STEP 2: VALIDAR SESSÃO E OBTER DADOS
    # ========================================

    try:
        session = require_authentication()
    except Exception as e:
        # Erro na autenticação (sessão inválida, etc)
        st.error(f"❌ Erro: {str(e)}")
        st.info("💡 Faça login novamente")

        # Limpar session_state
        from multi_tenant.auth.middleware import clear_session_state
        clear_session_state()

        st.stop()

    # Aplicar CSS tema dark
    apply_custom_css()

    # ========================================
    # STEP 3: DECIDIR O QUE MOSTRAR (ROUTER)
    # ========================================

    # CASO 1: Super Admin ou Admin GeniAI (tenant_id = 0)
    if session['role'] in ['super_admin', 'admin'] and session['tenant_id'] == 0:

        # Verificar se selecionou um cliente específico
        if 'selected_tenant_id' in st.session_state:
            # Mostrar dashboard do cliente selecionado
            tenant_id = st.session_state['selected_tenant_id']
            show_client_dashboard(session, tenant_id=tenant_id)

        else:
            # Mostrar painel admin (seleção de clientes)
            show_admin_panel(session)

    # CASO 2: Cliente (qualquer role em tenant != 0)
    else:
        # Ir direto para dashboard do seu tenant
        show_client_dashboard(session)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()