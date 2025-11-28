"""
Campaigns Module - Sistema de Campanhas de Disparo
==================================================

Este módulo implementa o sistema de preparação de dados para campanhas
de remarketing via WhatsApp/META, com exportação CSV para sistema de
disparo externo.

Componentes:
    - CampaignService: CRUD de campanhas e leads
    - CampaignVariableGenerator: Geração de variáveis via IA (GPT-4o-mini)
    - CampaignCSVExporter: Exportação CSV compatível com Disparador

Uso básico:
    >>> from src.multi_tenant.campaigns import CampaignService
    >>> service = CampaignService(engine, tenant_id=1)
    >>> campaign = service.create_campaign(name="Black Friday 2025", ...)
    >>> service.process_leads(campaign.id)
    >>> csv_data = service.export_csv(campaign.id)

Autor: Isaac (via Claude Code)
Data: 2025-11-26
Versão: 1.0
"""

from .models import (
    Campaign,
    CampaignLead,
    CampaignExport,
    CampaignStatus,
    CampaignType,
    CampaignTone,
    LeadStatus,
)
from .service import CampaignService
from .variable_generator import CampaignVariableGenerator
from .csv_exporter import CampaignCSVExporter

__all__ = [
    # Models
    "Campaign",
    "CampaignLead",
    "CampaignExport",
    # Enums
    "CampaignStatus",
    "CampaignType",
    "CampaignTone",
    "LeadStatus",
    # Services
    "CampaignService",
    "CampaignVariableGenerator",
    "CampaignCSVExporter",
]

__version__ = "1.1.0"