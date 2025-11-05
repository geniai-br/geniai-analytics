"""
Dashboards multi-tenant - GeniAI Analytics
Fase 2
"""

from .login_page import show_login_page
from .admin_panel import show_admin_panel
from .client_dashboard import show_client_dashboard

__all__ = [
    'show_login_page',
    'show_admin_panel',
    'show_client_dashboard',
]
