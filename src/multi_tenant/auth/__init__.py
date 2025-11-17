"""
Módulo de autenticação multi-tenant
Fase 2 - GeniAI Analytics
"""

from .auth import (
    authenticate_user,
    validate_session,
    logout_user,
    get_database_engine,
    get_etl_engine,
)

from .middleware import (
    require_authentication,
    set_rls_context,
)

__all__ = [
    'authenticate_user',
    'validate_session',
    'logout_user',
    'get_database_engine',
    'get_etl_engine',
    'require_authentication',
    'set_rls_context',
]