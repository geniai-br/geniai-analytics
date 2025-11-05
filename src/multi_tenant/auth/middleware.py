"""
Middleware de proteção de rotas e configuração RLS
Fase 2 - GeniAI Analytics
"""

import streamlit as st
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from .auth import validate_session, get_database_engine


# ============================================================================
# MIDDLEWARE DE AUTENTICAÇÃO
# ============================================================================

def require_authentication() -> Dict:
    """
    Middleware para proteger páginas que requerem autenticação

    Verifica se:
    1. Usuário tem sessão ativa no st.session_state
    2. Sessão é válida no banco (não expirada)
    3. Configura RLS context automaticamente

    Returns:
        Dict: Dados da sessão (user_id, tenant_id, role, etc.)

    Stops:
        st.stop() se não autenticado ou sessão inválida (redireciona para login)
    """
    # Verificar se existe sessão no session_state
    if 'session_id' not in st.session_state or 'authenticated' not in st.session_state:
        # Não autenticado - redirecionar para login
        st.error("🔒 Você precisa fazer login para acessar esta página.")
        st.info("💡 Redirecionando para a tela de login...")

        # Limpar session_state
        clear_session_state()

        st.stop()

    # Obter session_id
    session_id = st.session_state.get('session_id')

    # Validar sessão no banco
    engine = get_database_engine()
    session_data = validate_session(engine, session_id)

    if not session_data:
        # Sessão inválida ou expirada
        st.error("⏰ Sua sessão expirou. Faça login novamente.")
        st.info("💡 Por segurança, sessões expiram após 24 horas de inatividade.")

        # Limpar session_state
        clear_session_state()

        st.stop()

    # Configurar RLS context para o tenant do usuário
    set_rls_context(engine, session_data['tenant_id'], session_data['user_id'])

    # Armazenar dados da sessão no session_state (cache)
    st.session_state['user'] = session_data

    return session_data


# ============================================================================
# CONFIGURAÇÃO RLS (ROW-LEVEL SECURITY)
# ============================================================================

def set_rls_context(engine: Engine, tenant_id: int, user_id: int) -> None:
    """
    Configura variáveis de sessão PostgreSQL para Row-Level Security

    Estas variáveis são usadas pelas políticas RLS para filtrar automaticamente
    os dados retornados pelas queries.

    Args:
        engine: SQLAlchemy engine
        tenant_id: ID do tenant (usado para filtrar dados)
        user_id: ID do usuário (usado para logs e auditoria)

    Example:
        # Após configurar:
        set_rls_context(engine, tenant_id=1, user_id=3)

        # Qualquer SELECT será automaticamente filtrado:
        SELECT * FROM conversations_analytics;
        -- PostgreSQL adiciona internamente: WHERE tenant_id = 1

        # Admins (role super_admin) veem tudo (política RLS permite)
    """
    try:
        with engine.connect() as conn:
            # Configurar variáveis de sessão do PostgreSQL
            conn.execute(text("SET app.current_tenant_id = :tid"), {'tid': tenant_id})
            conn.execute(text("SET app.current_user_id = :uid"), {'uid': user_id})
            conn.commit()

    except Exception as e:
        # Em caso de erro, apenas logar (não deve quebrar a aplicação)
        print(f"⚠️ Erro ao configurar RLS context: {e}")


# ============================================================================
# CONTROLE DE ACESSO POR ROLE
# ============================================================================

def require_admin() -> Dict:
    """
    Middleware para páginas que requerem role admin ou super_admin

    Returns:
        Dict: Dados da sessão

    Stops:
        st.stop() se usuário não for admin
    """
    session = require_authentication()

    if session['role'] not in ['admin', 'super_admin']:
        st.error("🚫 Acesso negado. Área exclusiva para administradores.")
        st.info("💡 Entre em contato com o suporte se você precisa de acesso administrativo.")
        st.stop()

    return session


def require_super_admin() -> Dict:
    """
    Middleware para páginas que requerem role super_admin

    Returns:
        Dict: Dados da sessão

    Stops:
        st.stop() se usuário não for super_admin
    """
    session = require_authentication()

    if session['role'] != 'super_admin':
        st.error("🚫 Acesso negado. Área exclusiva para super administradores.")
        st.stop()

    return session


# ============================================================================
# UTILITÁRIOS
# ============================================================================

def clear_session_state():
    """
    Limpa todos os dados de autenticação do session_state

    Usado em:
    - Logout
    - Sessão expirada
    - Erro de autenticação
    """
    keys_to_clear = [
        'authenticated',
        'session_id',
        'user',
        'selected_tenant_id',  # Admin: tenant selecionado
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def is_authenticated() -> bool:
    """
    Verifica se usuário está autenticado (sem forçar redirect)

    Returns:
        bool: True se autenticado, False caso contrário
    """
    if 'authenticated' not in st.session_state:
        return False

    if 'session_id' not in st.session_state:
        return False

    # Validar sessão no banco
    try:
        engine = get_database_engine()
        session_id = st.session_state.get('session_id')
        session_data = validate_session(engine, session_id)

        return session_data is not None
    except Exception:
        return False


def get_current_user() -> Optional[Dict]:
    """
    Retorna dados do usuário autenticado (ou None se não autenticado)

    Returns:
        Dict: Dados do usuário ou None
    """
    if not is_authenticated():
        return None

    return st.session_state.get('user')


def get_current_tenant_id() -> Optional[int]:
    """
    Retorna tenant_id do usuário autenticado

    Returns:
        int: tenant_id ou None
    """
    user = get_current_user()
    if user:
        return user.get('tenant_id')
    return None


def can_access_tenant(tenant_id: int) -> bool:
    """
    Verifica se usuário atual pode acessar dados de um tenant específico

    Args:
        tenant_id: ID do tenant

    Returns:
        bool: True se pode acessar, False caso contrário

    Regras:
    - super_admin: pode acessar qualquer tenant
    - admin (tenant_id=0): pode acessar qualquer tenant
    - cliente: só pode acessar seu próprio tenant
    """
    user = get_current_user()
    if not user:
        return False

    # Super admin e admin GeniAI (tenant_id=0) podem acessar tudo
    if user['role'] in ['super_admin', 'admin'] and user['tenant_id'] == 0:
        return True

    # Cliente só pode acessar seu próprio tenant
    return user['tenant_id'] == tenant_id