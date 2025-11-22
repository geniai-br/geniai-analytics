"""
Utils - Multi-Tenant ETL V4
============================

Modulo com utilitarios compartilhados do sistema multi-tenant.

Componentes:
- TemplateManager: Gerenciador de templates de remarketing
- RateLimiter: Controle global de taxa de requisições OpenAI
- CostTracker: Rastreamento de custos por tenant/dia/mês
- ETL Schedule: Cálculo de próxima execução ETL

Fase: 8.1 - Foundation
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

from .template_manager import TemplateManager
from .rate_limiter import RateLimiter, get_rate_limiter
from .cost_tracker import CostTracker, get_cost_tracker
from .etl_schedule import get_next_etl_time, format_etl_countdown

__all__ = [
    'TemplateManager',
    'RateLimiter',
    'get_rate_limiter',
    'CostTracker',
    'get_cost_tracker',
    'get_next_etl_time',
    'format_etl_countdown',
]
