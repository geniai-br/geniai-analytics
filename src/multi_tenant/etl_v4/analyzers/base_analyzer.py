"""
Base Analyzer - ETL V4 Multi-Tenant
====================================

Interface abstrata para analyzers de conversas.
Permite múltiplas estratégias de análise (Regex, OpenAI, etc) com fallback automático.

Pattern: Adapter Pattern
Fase: 5.6 - OpenAI Integration
Autor: Isaac (via Claude Code)
Data: 2025-11-09
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Interface abstrata para analyzers de conversas.

    Todos os analyzers (Regex, OpenAI, etc) devem implementar esta interface.
    """

    def __init__(self, tenant_id: int):
        """
        Inicializa o analyzer.

        Args:
            tenant_id: ID do tenant
        """
        self.tenant_id = tenant_id
        self.analyzer_name = self.__class__.__name__
        logger.info(f"{self.analyzer_name} inicializado para tenant {tenant_id}")

    @abstractmethod
    def analyze_conversation(
        self,
        message_text: Optional[str],
        status: Optional[str] = None,
        has_human_intervention: bool = False,
        **kwargs
    ) -> Dict[str, any]:
        """
        Analisa uma única conversa e retorna classificações.

        Args:
            message_text: Texto compilado da conversa
            status: Status da conversa (open, resolved, pending)
            has_human_intervention: Se teve intervenção humana
            **kwargs: Argumentos adicionais específicos do analyzer

        Returns:
            Dict com:
                - is_lead: bool
                - visit_scheduled: bool
                - crm_converted: bool
                - ai_probability_label: str ('Alto', 'Médio', 'Baixo', 'N/A')
                - ai_probability_score: float (0-100)
                - lead_keywords_found: List[str] (opcional, para regex)
                - visit_keywords_found: List[str] (opcional, para regex)
                - conversion_keywords_found: List[str] (opcional, para regex)
                - nome_mapeado_bot: str (opcional, para OpenAI)
                - condicao_fisica: str (opcional, para OpenAI)
                - objetivo: str (opcional, para OpenAI)
                - analise_ia: str (opcional, para OpenAI)
                - sugestao_disparo: str (opcional, para OpenAI)
                - probabilidade_conversao: int (opcional, para OpenAI: 0-5)
        """
        pass

    @abstractmethod
    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa um DataFrame completo de conversas.

        Args:
            df: DataFrame com colunas:
                - message_compiled (texto das mensagens)
                - status (opcional)
                - has_human_intervention (opcional)

        Returns:
            DataFrame com colunas de análise adicionadas
        """
        pass

    def get_statistics(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Calcula estatísticas de conversão.

        Args:
            df: DataFrame com análises feitas

        Returns:
            Dict com estatísticas
        """
        if df.empty:
            return {
                'total_conversations': 0,
                'total_leads': 0,
                'total_visits': 0,
                'total_conversions': 0,
                'conversion_rate': 0.0,
                'visit_rate': 0.0,
                'lead_rate': 0.0,
                'analyzer': self.analyzer_name,
            }

        total = len(df)
        leads = df['is_lead'].sum() if 'is_lead' in df.columns else 0
        visits = df['visit_scheduled'].sum() if 'visit_scheduled' in df.columns else 0
        conversions = df['crm_converted'].sum() if 'crm_converted' in df.columns else 0

        return {
            'total_conversations': total,
            'total_leads': int(leads),
            'total_visits': int(visits),
            'total_conversions': int(conversions),
            'conversion_rate': round((conversions / total * 100) if total > 0 else 0, 2),
            'visit_rate': round((visits / leads * 100) if leads > 0 else 0, 2),
            'lead_rate': round((leads / total * 100) if total > 0 else 0, 2),
            'analyzer': self.analyzer_name,
        }

    def _score_to_label(self, score: float) -> str:
        """
        Converte score numérico (0-100) em label qualitativo.

        Args:
            score: Score 0-100

        Returns:
            str: 'Alto', 'Médio', 'Baixo', 'N/A'
        """
        if score >= 70:
            return 'Alto'
        elif score >= 40:
            return 'Médio'
        elif score > 0:
            return 'Baixo'
        else:
            return 'N/A'

    def _openai_probability_to_score(self, prob: int) -> float:
        """
        Converte probabilidade OpenAI (0-5) para score (0-100).

        Args:
            prob: Probabilidade OpenAI (0-5)

        Returns:
            float: Score 0-100

        Mapping:
            0 (Nula) -> 0
            1 (Muito Baixa) -> 20
            2 (Baixa) -> 40
            3 (Média) -> 60
            4 (Alta) -> 80
            5 (Altíssima) -> 100
        """
        mapping = {
            0: 0,
            1: 20,
            2: 40,
            3: 60,
            4: 80,
            5: 100,
        }
        return float(mapping.get(prob, 0))


class AnalyzerFactory:
    """
    Factory para criar analyzers baseado em configuração do tenant.
    """

    @staticmethod
    def create_analyzer(tenant_id: int, use_openai: bool = False, openai_api_key: Optional[str] = None) -> BaseAnalyzer:
        """
        Cria o analyzer apropriado baseado na configuração.

        Args:
            tenant_id: ID do tenant
            use_openai: Se deve usar OpenAI (default: False = Regex)
            openai_api_key: Chave da API OpenAI (requerida se use_openai=True)

        Returns:
            BaseAnalyzer: Instância do analyzer (RegexAnalyzer ou OpenAIAnalyzer)

        Raises:
            ValueError: Se use_openai=True mas openai_api_key não fornecida

        Example:
            >>> # Usar Regex (default)
            >>> analyzer = AnalyzerFactory.create_analyzer(tenant_id=1)
            >>>
            >>> # Usar OpenAI
            >>> analyzer = AnalyzerFactory.create_analyzer(
            ...     tenant_id=1,
            ...     use_openai=True,
            ...     openai_api_key="sk-..."
            ... )
        """
        if use_openai:
            if not openai_api_key:
                logger.warning(f"OpenAI solicitada para tenant {tenant_id} mas API key não fornecida. "
                              f"Fallback para RegexAnalyzer.")
                use_openai = False

        if use_openai:
            try:
                from .openai_analyzer import OpenAIAnalyzer
                logger.info(f"Criando OpenAIAnalyzer para tenant {tenant_id}")
                return OpenAIAnalyzer(tenant_id=tenant_id, api_key=openai_api_key)
            except ImportError as e:
                logger.error(f"Erro ao importar OpenAIAnalyzer: {e}. Fallback para RegexAnalyzer.")
                use_openai = False
            except Exception as e:
                logger.error(f"Erro ao criar OpenAIAnalyzer: {e}. Fallback para RegexAnalyzer.")
                use_openai = False

        # Fallback ou escolha padrão: RegexAnalyzer
        from .regex_analyzer import RegexAnalyzer
        logger.info(f"Criando RegexAnalyzer para tenant {tenant_id}")
        return RegexAnalyzer(tenant_id=tenant_id)
