"""
Utils - Multi-Tenant ETL V4
============================

Modulo com utilitarios compartilhados do sistema multi-tenant.

Componentes:
- TemplateManager: Gerenciador de templates de remarketing

Fase: 8.1 - Foundation
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

from .template_manager import TemplateManager

__all__ = ['TemplateManager']
