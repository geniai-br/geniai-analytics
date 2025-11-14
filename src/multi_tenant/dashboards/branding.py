"""
Branding Module - Dashboard Cliente
====================================

Aplica personalização visual dinâmica por tenant:
- Logo customizado
- Cores primária/secundária/accent
- CSS customizado
- Favicon

Fase: 4 - Dashboard Cliente Avançado
Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
import streamlit as st
from sqlalchemy import text
from typing import Dict, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_tenant_branding(engine, tenant_id: int) -> Optional[Dict]:
    """
    Busca configurações de branding do tenant.

    Args:
        engine: SQLAlchemy engine
        tenant_id: ID do tenant

    Returns:
        Dict com configurações de branding ou None
    """
    query = text("""
        SELECT
            logo_url,
            favicon_url,
            primary_color,
            secondary_color,
            accent_color,
            custom_css,
            dashboard_config
        FROM tenant_configs
        WHERE tenant_id = :tenant_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id}).fetchone()

            if result:
                return {
                    'logo_url': result.logo_url,
                    'favicon_url': result.favicon_url,
                    'primary_color': result.primary_color,
                    'secondary_color': result.secondary_color,
                    'accent_color': result.accent_color,
                    'custom_css': result.custom_css,
                    'dashboard_config': result.dashboard_config or {},
                }
            else:
                logger.warning(f"Branding não encontrado para tenant {tenant_id}, usando defaults")
                return get_default_branding()

    except Exception as e:
        logger.error(f"Erro ao buscar branding: {e}")
        return get_default_branding()


def get_default_branding() -> Dict:
    """
    Retorna branding padrão caso tenant não tenha configuração.

    Returns:
        Dict com branding default
    """
    return {
        'logo_url': None,
        'favicon_url': None,
        'primary_color': '#1E40AF',     # Azul padrão
        'secondary_color': '#10B981',   # Verde padrão
        'accent_color': '#F59E0B',      # Laranja padrão
        'custom_css': None,
        'dashboard_config': {},
    }


def apply_branding(branding: Dict, tenant_name: str = "Analytics"):
    """
    Aplica branding ao dashboard Streamlit.

    Args:
        branding: Dict com configurações de branding
        tenant_name: Nome do tenant para exibir
    """
    # CSS customizado com cores do tenant
    css = f"""
    <style>
    /* ========================================
       VARIÁVEIS DE COR DO TENANT
       ======================================== */
    :root {{
        --primary-color: {branding['primary_color']};
        --secondary-color: {branding['secondary_color']};
        --accent-color: {branding['accent_color']};
    }}

    /* ========================================
       HEADER E TÍTULO
       ======================================== */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}

    h1 {{
        color: {branding['primary_color']} !important;
        font-weight: 600;
    }}

    h2, h3 {{
        color: {branding['secondary_color']} !important;
    }}

    /* ========================================
       BOTÕES
       ======================================== */
    .stButton > button {{
        background-color: {branding['primary_color']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }}

    .stButton > button:hover {{
        background-color: {branding['secondary_color']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }}

    /* ========================================
       MÉTRICAS (KPI CARDS)
       ======================================== */
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg,
            {branding['primary_color']}15 0%,
            {branding['secondary_color']}15 100%);
        padding: 1rem;
        border-radius: 12px;
        border-left: 4px solid {branding['primary_color']};
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 500;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 2rem;
        font-weight: 700;
        color: {branding['primary_color']};
    }}

    /* ========================================
       GRÁFICOS
       ======================================== */
    .js-plotly-plot .plotly {{
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}

    /* ========================================
       TABELAS
       ======================================== */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}

    /* Cabeçalho da tabela */
    thead tr th {{
        background-color: {branding['primary_color']} !important;
        color: white !important;
        font-weight: 600;
    }}

    /* Linhas alternadas */
    tbody tr:nth-child(even) {{
        background-color: {branding['primary_color']}08;
    }}

    /* ========================================
       SIDEBAR
       ======================================== */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg,
            {branding['primary_color']}10 0%,
            {branding['secondary_color']}10 100%);
    }}

    [data-testid="stSidebar"] .block-container {{
        padding-top: 2rem;
    }}

    /* ========================================
       DIVISORES
       ======================================== */
    hr {{
        border-color: {branding['primary_color']}30;
        margin: 2rem 0;
    }}

    /* ========================================
       INPUTS E SELECT BOXES
       ======================================== */
    .stSelectbox > div > div {{
        border-color: {branding['primary_color']}50;
    }}

    .stSelectbox > div > div:focus-within {{
        border-color: {branding['primary_color']};
        box-shadow: 0 0 0 1px {branding['primary_color']};
    }}

    .stDateInput > div > div {{
        border-color: {branding['primary_color']}50;
    }}

    .stDateInput > div > div:focus-within {{
        border-color: {branding['primary_color']};
    }}

    /* ========================================
       EXPANDER
       ======================================== */
    .streamlit-expanderHeader {{
        background-color: {branding['primary_color']}10;
        border-radius: 8px;
        font-weight: 600;
    }}

    /* ========================================
       MENSAGENS (INFO, SUCCESS, WARNING, ERROR)
       ======================================== */
    .stAlert {{
        border-radius: 8px;
    }}

    /* ========================================
       LOADING SPINNER
       ======================================== */
    .stSpinner > div {{
        border-top-color: {branding['primary_color']} !important;
    }}

    /* ========================================
       SCROLLBAR CUSTOMIZADA
       ======================================== */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}

    ::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 10px;
    }}

    ::-webkit-scrollbar-thumb {{
        background: {branding['primary_color']};
        border-radius: 10px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {branding['secondary_color']};
    }}

    /* ========================================
       CSS CUSTOMIZADO DO TENANT
       ======================================== */
    {branding.get('custom_css', '')}
    </style>
    """

    # Aplicar CSS
    st.markdown(css, unsafe_allow_html=True)

    # Logo do tenant (se disponível)
    if branding.get('logo_url'):
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
                <img src="{branding['logo_url']}"
                     alt="{tenant_name} Logo"
                     style="max-height: 80px; max-width: 300px; object-fit: contain;">
            </div>
            """,
            unsafe_allow_html=True
        )

    logger.info(f"Branding aplicado para tenant: {tenant_name}")


def render_header_with_logo(
    tenant_name: str,
    user_name: str,
    role: str,
    logo_url: Optional[str] = None,
    show_back_button: bool = False,
    show_logout_button: bool = True
) -> Optional[str]:
    """
    Renderiza header personalizado com logo e informações do usuário.

    Args:
        tenant_name: Nome do tenant
        user_name: Nome do usuário logado
        role: Role do usuário
        logo_url: URL do logo (opcional)
        show_back_button: Se mostra botão voltar
        show_logout_button: Se mostra botão sair

    Returns:
        str: Ação do usuário ('back', 'logout', None)
    """
    action = None

    # Container para header
    header_cols = st.columns([1, 6, 1])

    with header_cols[0]:
        if show_back_button:
            if st.button("← Voltar", use_container_width=True, key="header_back"):
                action = 'back'

    with header_cols[1]:
        # Logo centralizado (se disponível)
        if logo_url:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <img src="{logo_url}"
                         alt="{tenant_name}"
                         style="max-height: 60px; margin-bottom: 0.5rem;">
                </div>
                """,
                unsafe_allow_html=True
            )

        # Título e info do usuário
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h1 style="margin: 0;">📊 {tenant_name}</h1>
                <p style="color: #64748b; margin-top: 0.5rem;">
                    👤 {user_name} · {role}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with header_cols[2]:
        if show_logout_button:
            if st.button("🚪 Sair", use_container_width=True, key="header_logout"):
                action = 'logout'

    st.divider()

    return action


# ============================================================================
# TESTE LOCAL
# ============================================================================

if __name__ == "__main__":
    # Teste de branding
    test_branding = {
        'logo_url': 'https://via.placeholder.com/300x80/FF6B35/FFFFFF?text=AllpFit',
        'favicon_url': None,
        'primary_color': '#FF6B35',
        'secondary_color': '#1E90FF',
        'accent_color': '#00CED1',
        'custom_css': '/* Custom CSS aqui */',
        'dashboard_config': {},
    }

    st.set_page_config(
        page_title="Teste Branding",
        page_icon="🎨",
        layout="wide"
    )

    apply_branding(test_branding, tenant_name="AllpFit CrossFit")

    render_header_with_logo(
        tenant_name="AllpFit CrossFit",
        user_name="Isaac Santos",
        role="Admin",
        logo_url=test_branding['logo_url']
    )

    # Teste de componentes
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Contatos", "1.099")

    with col2:
        st.metric("Leads", "313", delta="+28%")

    with col3:
        st.metric("Visitas", "555", delta="+50%")

    with col4:
        st.metric("Conversões", "72", delta="+6%")

    st.divider()

    # Botões
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("📊 Ver Relatório")
    with col2:
        st.button("📥 Exportar CSV")
    with col3:
        st.button("🔄 Atualizar")

    st.success("Branding aplicado com sucesso!")
    st.info("Este é um teste do módulo de branding")
    st.warning("Atenção: teste em andamento")