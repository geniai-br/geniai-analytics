"""
ETL V4 - Multi-Tenant
====================

Pipeline de ETL para sincronização de conversas do Chatwoot para o banco multi-tenant.

Módulos:
    - extractor: Extração de dados do banco remoto Chatwoot
    - transformer: Transformação e normalização de dados
    - loader: Carregamento (UPSERT) no banco local
    - watermark_manager: Controle de sincronização incremental
    - pipeline: Orquestrador Extract → Transform → Load

Autor: Isaac (via Claude Code)
Data: 2025-11-06
Fase: 3 - ETL Multi-Tenant
"""

__version__ = "4.0.0"
__author__ = "Isaac"
__status__ = "Development"
