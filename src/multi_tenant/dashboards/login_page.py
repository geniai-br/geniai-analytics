"""
Tela de Login - Multi-Tenant
Fase 2 - GeniAI Analytics
Design: Tema dark profissional com centralização perfeita (azul #1E90FF + laranja #FF8C00)
"""

import streamlit as st
import re
from pathlib import Path
import sys

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import authenticate_user, get_database_engine


# ============================================================================
# VALIDAÇÃO
# ============================================================================

def validate_email(email: str) -> bool:
    """
    Valida formato básico de email

    Args:
        email: String do email

    Returns:
        bool: True se válido, False caso contrário
    """
    if not email:
        return False

    # Regex simples para validar email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ============================================================================
# CSS CUSTOMIZADO - TEMA DARK PROFISSIONAL
# ============================================================================

def apply_login_css():
    """Aplica CSS customizado para a tela de login (tema dark profissional)"""
    st.markdown("""
        <style>
        /* ===== RESET E REMOÇÃO DE ESPAÇOS CINZAS ===== */

        /* Remover TODOS os elementos do Streamlit que criam espaços */
        #root > div:nth-child(1) > div > div > div > div > section > div {
            padding-top: 0 !important;
        }

        header {
            visibility: hidden !important;
            height: 0 !important;
            display: none !important;
        }

        .main > div {
            padding-top: 0 !important;
        }

        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }

        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] {
            gap: 0 !important;
        }

        /* Background e estilo principal */
        .main {
            padding: 0 !important;
        }

        .stApp {
            background-color: #0E1117;
        }

        /* Remover toolbar e footer */
        .stDeployButton {
            display: none !important;
        }

        footer {
            display: none !important;
        }

        /* ===== CONTAINER DE CENTRALIZAÇÃO PERFEITA ===== */

        .login-wrapper {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 100vh !important;
            width: 100% !important;
            background: linear-gradient(135deg, #0E1117 0%, #1A1F2E 100%);
            padding: 2rem;
        }

        /* ===== CARD DE LOGIN ===== */

        .login-container {
            background: linear-gradient(145deg, #1A1F2E 0%, #262B3D 100%);
            border-radius: 20px;
            padding: 3rem 2.5rem;
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.6),
                0 0 0 1px rgba(30, 144, 255, 0.1);
            max-width: 450px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            animation: slideIn 0.4s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* ===== LOGO E TÍTULO ===== */

        .login-logo {
            text-align: center;
            margin-bottom: 2.5rem;
        }

        .login-logo-icon {
            font-size: 3.5rem;
            margin-bottom: 1rem;
            display: block;
            background: linear-gradient(135deg, #1E90FF 0%, #FF8C00 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: glow 2s ease-in-out infinite;
        }

        @keyframes glow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }

        .login-title {
            color: #FFFFFF;
            font-size: 2rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }

        .login-subtitle {
            color: #B0B8C4;
            font-size: 0.95rem;
            text-align: center;
            margin-bottom: 2.5rem;
            font-weight: 400;
        }

        /* ===== INPUTS ===== */

        .stTextInput {
            margin-bottom: 1.5rem;
        }

        .stTextInput > label {
            color: #B0B8C4 !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            margin-bottom: 0.5rem !important;
            display: block !important;
            letter-spacing: 0.3px;
        }

        .stTextInput input {
            background-color: #0E1117 !important;
            color: #FFFFFF !important;
            border: 2px solid #262B3D !important;
            border-radius: 10px !important;
            padding: 0.9rem 1rem !important;
            font-size: 0.95rem !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
        }

        .stTextInput input:focus {
            border-color: #1E90FF !important;
            box-shadow: 0 0 0 3px rgba(30, 144, 255, 0.15) !important;
            background-color: #151A23 !important;
        }

        .stTextInput input::placeholder {
            color: #6C757D !important;
            opacity: 1 !important;
        }

        /* ===== BOTÃO DE LOGIN ===== */

        .stButton {
            margin-top: 1rem;
        }

        .stButton > button {
            background: linear-gradient(135deg, #1E90FF 0%, #1560A0 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.85rem 2rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(30, 144, 255, 0.3) !important;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #1560A0 0%, #0E4A7A 100%) !important;
            box-shadow: 0 6px 20px rgba(30, 144, 255, 0.5) !important;
            transform: translateY(-2px) !important;
        }

        .stButton > button:active {
            transform: translateY(0) !important;
        }

        /* ===== MENSAGENS (SUCCESS/ERROR) ===== */

        .stAlert {
            border-radius: 10px !important;
            border: none !important;
            padding: 1rem 1.2rem !important;
            margin: 1rem 0 !important;
        }

        /* ===== CREDENCIAIS DE DEV ===== */

        .dev-credentials {
            background: linear-gradient(135deg, #262B3D 0%, #1A1F2E 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
            border-left: 4px solid #FF8C00;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }

        .dev-credentials-title {
            color: #FF8C00;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .dev-credentials-section {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .dev-credentials-section:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }

        .dev-credentials-role {
            color: #FFFFFF;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .dev-credentials-item {
            color: #B0B8C4;
            font-size: 0.8rem;
            margin: 0.3rem 0;
            font-family: 'Courier New', monospace;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .dev-credentials-icon {
            opacity: 0.7;
        }

        /* ===== FOOTER ===== */

        .login-footer {
            text-align: center;
            color: #6C757D;
            font-size: 0.8rem;
            margin-top: 2.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-weight: 500;
        }

        /* ===== SPINNER CUSTOMIZADO ===== */

        .stSpinner > div {
            border-top-color: #1E90FF !important;
        }

        /* ===== RESPONSIVIDADE ===== */

        @media (max-width: 768px) {
            .login-container {
                padding: 2rem 1.5rem;
                margin: 1rem;
            }

            .login-title {
                font-size: 1.6rem;
            }

            .login-logo-icon {
                font-size: 3rem;
            }
        }

        /* ===== ANIMAÇÕES SUAVES ===== */

        * {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        </style>
    """, unsafe_allow_html=True)


# ============================================================================
# TELA DE LOGIN
# ============================================================================

def show_login_page():
    """
    Tela de login moderna com tema dark profissional

    Features:
    - Centralização perfeita vertical e horizontal (flexbox)
    - Validação de campos vazios
    - Feedback visual (success, error)
    - Animação de sucesso (balloons)
    - Credenciais de DEV visíveis (apenas em dev)
    - Design moderno e limpo
    - Sem espaços cinzas no topo
    """

    # Aplicar CSS customizado
    apply_login_css()

    # Espaçamento para centralizar verticalmente
    st.markdown("<br><br><br>", unsafe_allow_html=True)

    # Container centralizado
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo e título
        st.markdown("""
            <div class="login-logo">
                <span class="login-logo-icon">🔐</span>
                <div class="login-title">GeniAI Analytics</div>
                <div class="login-subtitle">Sistema Multi-Tenant</div>
            </div>
        """, unsafe_allow_html=True)

        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            # Email
            email = st.text_input(
                "Email",
                placeholder="seu@email.com",
                key="login_email"
            )

            # Senha
            password = st.text_input(
                "Senha",
                type="password",
                placeholder="Digite sua senha",
                key="login_password"
            )

            # Botão de submit
            submit = st.form_submit_button("Entrar", use_container_width=True)

            # Processar login
            if submit:
                # Validar campos vazios
                if not email or not password:
                    st.error("❌ Preencha todos os campos")
                    st.stop()

                # Validar formato de email
                if not validate_email(email):
                    st.error("❌ Formato de email inválido")
                    st.stop()

                # Tentar autenticar
                try:
                    with st.spinner("Autenticando..."):
                        engine = get_database_engine()
                        session_data = authenticate_user(engine, email, password)

                        if session_data:
                            # Login bem-sucedido!

                            # Salvar dados no session_state
                            st.session_state['authenticated'] = True
                            st.session_state['session_id'] = session_data['session_id']
                            st.session_state['user'] = session_data

                            # Feedback visual
                            st.success(f"✅ Bem-vindo, {session_data['full_name']}!")
                            st.balloons()

                            # Redirecionar imediatamente
                            st.rerun()

                        else:
                            # Credenciais incorretas
                            st.error("Email ou senha incorretos")

                except Exception as e:
                    # Erro genérico (ex: usuário inativo, tenant suspenso)
                    error_msg = str(e)

                    if "inativo" in error_msg.lower():
                        st.error("Sua conta está inativa. Entre em contato com o suporte.")
                    elif "suspenso" in error_msg.lower():
                        st.error("Acesso temporariamente suspenso. Entre em contato.")
                    else:
                        st.error(f"Erro: {error_msg}")

        # Credenciais de DEV (apenas em desenvolvimento)
        show_dev_credentials()

        # Footer
        st.markdown(
            '<div class="login-footer">Powered by GeniAI © 2025</div>',
            unsafe_allow_html=True
        )


# ============================================================================
# CREDENCIAIS DE DEV
# ============================================================================

def show_dev_credentials():
    """
    Exibe credenciais de desenvolvimento (apenas em modo DEV)

    Útil para testar rapidamente sem precisar lembrar as credenciais
    """
    import os

    # Verificar se está em modo DEV
    environment = os.getenv('ENVIRONMENT', 'development')

    if environment == 'development':
        # Usar componentes nativos do Streamlit
        st.markdown("---")
        st.markdown("### 💡 Credenciais de DEV")

        # Super Admin
        with st.container():
            st.markdown("**Super Admin GeniAI**")
            st.code("📧 admin@geniai.com.br", language=None)
            st.code("🔑 senha123", language=None)

        st.markdown("")

        # Admin AllpFit
        with st.container():
            st.markdown("**Admin AllpFit**")
            st.code("📧 isaac@allpfit.com.br", language=None)
            st.code("🔑 senha123", language=None)

        st.markdown("")

        # Cliente AllpFit
        with st.container():
            st.markdown("**Cliente AllpFit**")
            st.code("📧 visualizador@allpfit.com.br", language=None)
            st.code("🔑 senha123", language=None)


# ============================================================================
# TESTES LOCAIS
# ============================================================================

if __name__ == "__main__":
    # Configurar página
    st.set_page_config(
        page_title="Login - GeniAI Analytics",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # Mostrar login
    show_login_page()
