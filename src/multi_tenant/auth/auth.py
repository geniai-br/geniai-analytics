"""
Módulo de autenticação multi-tenant - GeniAI Analytics
Responsável por: login, logout, validação de sessão, gerenciamento de database engine
"""

import os
import bcrypt
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import streamlit as st

# Configurar logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================================================
# DATABASE ENGINE
# ============================================================================

@st.cache_resource
def get_database_engine() -> Engine:
    """
    Retorna engine SQLAlchemy com cache (singleton)

    Credenciais lidas de variáveis de ambiente ou padrões do projeto

    Returns:
        Engine: SQLAlchemy engine conectado ao geniai_analytics
    """
    # Credenciais do banco (conforme DB_DOCUMENTATION.md)
    db_host = os.getenv('LOCAL_DB_HOST', 'localhost')
    db_port = os.getenv('LOCAL_DB_PORT', '5432')
    db_name = os.getenv('LOCAL_DB_NAME', 'geniai_analytics')
    db_user = os.getenv('LOCAL_DB_USER', 'isaac')
    db_password = os.getenv('LOCAL_DB_PASSWORD', 'AllpFit2024@Analytics')

    # Connection string (URL encode password para tratar caracteres especiais)
    from urllib.parse import quote_plus
    password_encoded = quote_plus(db_password)
    database_url = f"postgresql://{db_user}:{password_encoded}@{db_host}:{db_port}/{db_name}"

    # Criar engine
    engine = create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verificar conexão antes de usar
        echo=False
    )

    return engine


def get_etl_engine() -> Engine:
    """
    Retorna engine SQLAlchemy para processos ETL - BYPASS RLS

    Este engine conecta com o usuário 'johan_geniai' (role: etl_service)
    que tem políticas RLS com USING (TRUE), permitindo acesso total
    aos dados SEM necessidade de configurar contexto RLS.

    USO:
    - Processos ETL (sincronização, consolidação, análise)
    - Scripts de manutenção
    - Background jobs
    - Qualquer operação que precise acessar dados de múltiplos tenants

    NÃO USE:
    - No Streamlit/Dashboard (use get_database_engine())
    - Em endpoints expostos ao usuário final

    Returns:
        Engine: SQLAlchemy engine com permissões ETL
    """
    # Credenciais ETL (usuário johan_geniai com role etl_service)
    db_host = os.getenv('LOCAL_DB_HOST', 'localhost')
    db_port = os.getenv('LOCAL_DB_PORT', '5432')
    db_name = os.getenv('LOCAL_DB_NAME', 'geniai_analytics')
    db_user = 'johan_geniai'  # Role: etl_service (bypass RLS)
    db_password = 'vlVMVM6UNz2yYSBlzodPjQvZh'

    # Connection string
    from urllib.parse import quote_plus
    password_encoded = quote_plus(db_password)
    database_url = f"postgresql://{db_user}:{password_encoded}@{db_host}:{db_port}/{db_name}"

    # Criar engine
    engine = create_engine(
        database_url,
        pool_size=10,  # ETL pode precisar de mais conexões
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )

    return engine


# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

def authenticate_user(engine: Engine, email: str, password: str) -> Optional[Dict]:
    """
    Autentica usuário e cria sessão

    Args:
        engine: SQLAlchemy engine
        email: Email do usuário
        password: Senha em texto plano

    Returns:
        Dict com dados da sessão:
        {
            'session_id': UUID,
            'user_id': int,
            'tenant_id': int,
            'email': str,
            'full_name': str,
            'role': str,  # 'super_admin', 'admin', 'client'
            'tenant_name': str,
            'tenant_slug': str,
            'is_active': bool,
        }

        None se autenticação falhar

    Raises:
        Exception: Em caso de erro no banco
    """
    logger.info(f"Tentativa de login: {email}")

    try:
        with engine.connect() as conn:  # Usar connect() com commit explícito
            # Buscar usuário + tenant em uma única query (JOIN)
            query = text("""
                SELECT
                    u.id AS user_id,
                    u.email,
                    u.password_hash,
                    u.full_name,
                    u.role,
                    u.is_active,
                    u.tenant_id,
                    t.name AS tenant_name,
                    t.slug AS tenant_slug,
                    t.status AS tenant_status
                FROM users u
                JOIN tenants t ON u.tenant_id = t.id
                WHERE u.email = :email
                  AND u.deleted_at IS NULL
                  AND t.deleted_at IS NULL
            """)

            result = conn.execute(query, {'email': email}).fetchone()

            if not result:
                logger.warning(f"Login falhou: usuário não encontrado - {email}")
                return None

            # Verificar senha (bcrypt)
            password_hash = result.password_hash
            password_check = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

            if not password_check:
                logger.warning(f"Login falhou: senha incorreta - {email}")
                return None

            # Verificar se usuário está ativo
            if not result.is_active:
                logger.warning(f"Login bloqueado: usuário inativo - {email}")
                raise Exception("Usuário inativo. Entre em contato com o suporte.")

            # Verificar se tenant está ativo
            if result.tenant_status != 'active':
                logger.warning(f"Login bloqueado: tenant suspenso - {email}")
                raise Exception("Acesso suspenso. Entre em contato com o suporte.")

            # Criar sessão
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=24)  # Sessão expira em 24h

            # Obter IP do usuário (se disponível via Streamlit)
            try:
                # Tentar obter IP real (nginx proxy)
                ip_address = st.context.headers.get('X-Forwarded-For',
                             st.context.headers.get('X-Real-IP', None))
            except:
                ip_address = None

            # Obter User-Agent
            try:
                user_agent = st.context.headers.get('User-Agent', None)
            except:
                user_agent = None

            # Inserir sessão no banco
            insert_session = text("""
                INSERT INTO sessions (id, user_id, tenant_id, ip_address, user_agent, expires_at)
                VALUES (:session_id, :user_id, :tenant_id, :ip_address, :user_agent, :expires_at)
            """)

            conn.execute(insert_session, {
                'session_id': session_id,
                'user_id': result.user_id,
                'tenant_id': result.tenant_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'expires_at': expires_at
            })

            # Atualizar last_login
            update_login = text("""
                UPDATE users
                SET last_login = NOW(),
                    last_login_ip = :ip_address,
                    login_count = login_count + 1,
                    failed_login_attempts = 0
                WHERE id = :user_id
            """)

            conn.execute(update_login, {
                'user_id': result.user_id,
                'ip_address': ip_address
            })

            conn.commit()

            # Retornar dados da sessão
            session_data = {
                'session_id': session_id,
                'user_id': result.user_id,
                'tenant_id': result.tenant_id,
                'email': result.email,
                'full_name': result.full_name,
                'role': result.role,
                'tenant_name': result.tenant_name,
                'tenant_slug': result.tenant_slug,
                'is_active': result.is_active,
            }

            logger.info(f"Login bem-sucedido: {email} (user_id={result.user_id}, tenant_id={result.tenant_id}, role={result.role})")

            return session_data

    except Exception as e:
        # Re-lançar exceção para ser tratada pela UI
        logger.error(f"Erro na autenticação para {email}: {str(e)}")
        raise Exception(f"Erro na autenticação: {str(e)}")


# ============================================================================
# VALIDAÇÃO DE SESSÃO
# ============================================================================

def validate_session(engine: Engine, session_id: str) -> Optional[Dict]:
    """
    Valida sessão existente e retorna dados do usuário + tenant

    Args:
        engine: SQLAlchemy engine
        session_id: UUID da sessão

    Returns:
        Dict com dados da sessão (mesmo formato de authenticate_user)
        None se sessão inválida ou expirada
    """
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT
                    s.id AS session_id,
                    s.expires_at,
                    u.id AS user_id,
                    u.email,
                    u.full_name,
                    u.role,
                    u.is_active,
                    u.tenant_id,
                    t.name AS tenant_name,
                    t.slug AS tenant_slug,
                    t.status AS tenant_status
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                JOIN tenants t ON s.tenant_id = t.id
                WHERE s.id = :session_id
                  AND s.expires_at > NOW()
                  AND u.deleted_at IS NULL
                  AND t.deleted_at IS NULL
            """)

            result = conn.execute(query, {'session_id': session_id}).fetchone()

            if not result:
                return None

            # Verificar se usuário ainda está ativo
            if not result.is_active:
                return None

            # Verificar se tenant ainda está ativo
            if result.tenant_status != 'active':
                return None

            # Retornar dados da sessão
            return {
                'session_id': result.session_id,
                'user_id': result.user_id,
                'tenant_id': result.tenant_id,
                'email': result.email,
                'full_name': result.full_name,
                'role': result.role,
                'tenant_name': result.tenant_name,
                'tenant_slug': result.tenant_slug,
                'is_active': result.is_active,
            }

    except Exception as e:
        logger.error(f"Erro ao validar sessão: {e}")
        return None


# ============================================================================
# LOGOUT
# ============================================================================

def logout_user(engine: Engine, session_id: str) -> bool:
    """
    Destrói sessão (logout)

    Args:
        engine: SQLAlchemy engine
        session_id: UUID da sessão

    Returns:
        bool: True se logout bem-sucedido, False caso contrário
    """
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM sessions WHERE id = :session_id")
            result = conn.execute(query, {'session_id': session_id})
            conn.commit()

            if result.rowcount > 0:
                logger.info(f"Logout realizado com sucesso: session_id={session_id[:8]}...")

            return result.rowcount > 0

    except Exception as e:
        logger.error(f"Erro ao fazer logout: {e}")
        return False


# ============================================================================
# UTILITÁRIOS
# ============================================================================

def clear_expired_sessions(engine: Engine) -> int:
    """
    Remove sessões expiradas do banco (pode ser executado periodicamente)

    Args:
        engine: SQLAlchemy engine

    Returns:
        int: Número de sessões removidas
    """
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM sessions WHERE expires_at < NOW()")
            result = conn.execute(query)
            conn.commit()

            if result.rowcount > 0:
                logger.info(f"Sessões expiradas removidas: {result.rowcount}")

            return result.rowcount

    except Exception as e:
        logger.error(f"Erro ao limpar sessões expiradas: {e}")
        return 0


def check_database_connection() -> bool:
    """
    Verifica se a conexão com o banco está funcionando

    Returns:
        bool: True se conectado, False caso contrário
    """
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Erro na conexão com banco: {e}")
        return False