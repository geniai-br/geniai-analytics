"""
Analyzers Module - ETL V4 Multi-Tenant
=======================================

Módulo de analyzers para detecção de leads, visitas e conversões.

Arquitetura:
- BaseAnalyzer: Interface abstrata
- RegexAnalyzer: Análise por keywords/regex (gratuito, 80% accuracy)
- OpenAIAnalyzer: Análise por IA (GPT-4o-mini, 95% accuracy)

Uso:
    from src.multi_tenant.etl_v4.analyzers import AnalyzerFactory

    # Criar analyzer baseado em config
    analyzer = AnalyzerFactory.create_analyzer(
        tenant_id=1,
        use_openai=True,
        openai_api_key="sk-..."
    )

    # Analisar DataFrame
    df_analyzed = analyzer.analyze_dataframe(df)

Fase: 5.6 - OpenAI Integration
Autor: Isaac (via Claude Code)
Data: 2025-11-09
"""

from .base_analyzer import BaseAnalyzer, AnalyzerFactory
from .regex_analyzer import RegexAnalyzer, add_lead_analysis
from .openai_analyzer import OpenAIAnalyzer, add_openai_analysis

__all__ = [
    'BaseAnalyzer',
    'AnalyzerFactory',
    'RegexAnalyzer',
    'OpenAIAnalyzer',
    'add_lead_analysis',
    'add_openai_analysis',
]
