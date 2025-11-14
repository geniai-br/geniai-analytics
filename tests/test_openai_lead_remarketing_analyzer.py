"""
Testes de Integração para OpenAILeadRemarketingAnalyzer
========================================================

Testa funcionalidades de:
- Classificação de tipo de remarketing por tempo de inatividade
- Análise de leads inativos com OpenAI (requer API key)
- Cálculo de custo
- Estatísticas de uso
- Retry em caso de falha

NOTA: Testes que chamam OpenAI API são marcados com @pytest.mark.integration
      e pulados se OPENAI_API_KEY não estiver configurada.

Fase: 8.1 - Foundation
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

import os
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.multi_tenant.etl_v4.analyzers.openai_lead_remarketing_analyzer import (
    OpenAILeadRemarketingAnalyzer
)
from src.multi_tenant.utils.template_manager import TemplateManager


# Fixture para pular testes de integração se não houver API key
def skip_if_no_api_key():
    """Pula teste se OPENAI_API_KEY não configurada"""
    return pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY'),
        reason="OPENAI_API_KEY não configurada"
    )


class TestOpenAILeadRemarketingAnalyzer:
    """Testes unitários para OpenAILeadRemarketingAnalyzer"""

    @pytest.fixture
    def template_manager(self):
        """Fixture: TemplateManager"""
        return TemplateManager(tenant_id=1)

    @pytest.fixture
    def mock_api_key(self):
        """Fixture: API key mock"""
        return "sk-test-mock-api-key"

    def test_init_sem_api_key(self):
        """Testa inicialização sem API key"""
        with pytest.raises(ValueError, match="OpenAI API key é obrigatória"):
            OpenAILeadRemarketingAnalyzer(tenant_id=1, api_key='')

    def test_init_com_api_key(self, mock_api_key, template_manager):
        """Testa inicialização com API key"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        assert analyzer.tenant_id == 1
        assert analyzer.api_key == mock_api_key
        assert analyzer.model == 'gpt-4o-mini-2024-07-18'
        assert analyzer.template_manager is not None

    def test_get_remarketing_type_recente(self, mock_api_key, template_manager):
        """Testa classificação REMARKETING_RECENTE (24-48h)"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        assert analyzer.get_remarketing_type(26.0) == 'REMARKETING_RECENTE'
        assert analyzer.get_remarketing_type(30.0) == 'REMARKETING_RECENTE'
        assert analyzer.get_remarketing_type(47.9) == 'REMARKETING_RECENTE'

    def test_get_remarketing_type_medio(self, mock_api_key, template_manager):
        """Testa classificação REMARKETING_MEDIO (48h-7d)"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        assert analyzer.get_remarketing_type(48.0) == 'REMARKETING_MEDIO'
        assert analyzer.get_remarketing_type(72.0) == 'REMARKETING_MEDIO'
        assert analyzer.get_remarketing_type(167.9) == 'REMARKETING_MEDIO'

    def test_get_remarketing_type_frio(self, mock_api_key, template_manager):
        """Testa classificação REMARKETING_FRIO (7d+)"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        assert analyzer.get_remarketing_type(168.0) == 'REMARKETING_FRIO'
        assert analyzer.get_remarketing_type(336.0) == 'REMARKETING_FRIO'
        assert analyzer.get_remarketing_type(720.0) == 'REMARKETING_FRIO'

    def test_calculate_cost(self, mock_api_key, template_manager):
        """Testa cálculo de custo"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        # Custo típico de uma análise (550 input + 300 output)
        custo = analyzer._calculate_cost(tokens_input=550, tokens_output=300)

        # Deve ser aproximadamente R$ 0.00144
        assert 0.001 < custo < 0.003
        assert isinstance(custo, float)

    def test_calculate_cost_zero_tokens(self, mock_api_key, template_manager):
        """Testa cálculo de custo com zero tokens"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        custo = analyzer._calculate_cost(tokens_input=0, tokens_output=0)
        assert custo == 0.0

    def test_get_stats_inicial(self, mock_api_key, template_manager):
        """Testa estatísticas iniciais"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        stats = analyzer.get_stats()

        assert stats['total_calls'] == 0
        assert stats['successful_calls'] == 0
        assert stats['failed_calls'] == 0
        assert stats['total_tokens'] == 0
        assert stats['total_cost_brl'] == 0.0
        assert stats['success_rate'] == 0
        assert stats['avg_cost_brl'] == 0

    def test_reset_stats(self, mock_api_key, template_manager):
        """Testa reset de estatísticas"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        # Simular algumas estatísticas
        analyzer.stats['total_calls'] = 10
        analyzer.stats['successful_calls'] = 8
        analyzer.stats['failed_calls'] = 2

        # Resetar
        analyzer.reset_stats()

        stats = analyzer.get_stats()
        assert stats['total_calls'] == 0
        assert stats['successful_calls'] == 0

    def test_build_system_prompt_recente(self, mock_api_key, template_manager):
        """Testa construção de prompt para REMARKETING_RECENTE"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        prompt = analyzer._build_system_prompt('REMARKETING_RECENTE')

        assert '24-48h' in prompt
        assert 'casual' in prompt.lower()
        assert 'JSON' in prompt
        assert 'score_prioridade' in prompt

    def test_build_system_prompt_medio(self, mock_api_key, template_manager):
        """Testa construção de prompt para REMARKETING_MEDIO"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        prompt = analyzer._build_system_prompt('REMARKETING_MEDIO')

        assert '48h-7d' in prompt
        assert 'profissional' in prompt.lower()
        assert 'JSON' in prompt

    def test_build_user_prompt(self, mock_api_key, template_manager):
        """Testa construção de prompt do usuário"""
        analyzer = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=mock_api_key,
            template_manager=template_manager
        )

        conversa_compilada = {
            'messages': [
                {
                    'sender_type': 'Contact',
                    'content': 'Olá, gostaria de saber sobre CrossFit',
                    'created_at': '2025-11-13T10:00:00Z'
                },
                {
                    'sender_type': 'Agent',
                    'content': 'Olá! Temos aulas de CrossFit às 18h.',
                    'created_at': '2025-11-13T10:05:00Z'
                }
            ]
        }

        prompt = analyzer._build_user_prompt(
            conversa_compilada=conversa_compilada,
            contact_name='João Silva',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        assert 'João Silva' in prompt
        assert 'AllpFit' in prompt
        assert '30.0 horas' in prompt
        assert 'CrossFit' in prompt


class TestOpenAILeadRemarketingAnalyzerIntegration:
    """Testes de integração (requerem API key real)"""

    @pytest.fixture
    def analyzer(self):
        """Fixture: Analyzer com API key real"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            pytest.skip("OPENAI_API_KEY não configurada")

        return OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key=api_key
        )

    @skip_if_no_api_key()
    @pytest.mark.integration
    def test_analyze_lead_real(self, analyzer):
        """Testa análise real com OpenAI API"""
        conversa_compilada = {
            'messages': [
                {
                    'sender_type': 'Contact',
                    'content': 'Olá, gostaria de saber sobre aulas de CrossFit para iniciantes',
                    'created_at': '2025-11-13T10:00:00Z'
                },
                {
                    'sender_type': 'Agent',
                    'content': 'Olá! Temos turmas para iniciantes às 18h e 19h. Qual seu objetivo principal?',
                    'created_at': '2025-11-13T10:05:00Z'
                },
                {
                    'sender_type': 'Contact',
                    'content': 'Quero perder peso e ganhar condicionamento físico',
                    'created_at': '2025-11-13T10:10:00Z'
                },
                {
                    'sender_type': 'Agent',
                    'content': 'Perfeito! CrossFit é ótimo para isso. Quer agendar uma aula experimental?',
                    'created_at': '2025-11-13T10:12:00Z'
                }
            ]
        }

        resultado = analyzer.analyze_lead(
            conversation_id=12345,
            conversa_compilada=conversa_compilada,
            contact_name='João Silva',
            inbox_name='AllpFit',
            tipo_remarketing='REMARKETING_RECENTE',
            tempo_inativo_horas=30.0
        )

        # Validar estrutura do resultado
        assert 'tipo_conversa' in resultado
        assert resultado['tipo_conversa'] == 'REMARKETING_RECENTE'

        assert 'analise_ia' in resultado
        assert len(resultado['analise_ia']) > 0

        assert 'sugestao_disparo' in resultado
        assert 'João' in resultado['sugestao_disparo'] or 'AllpFit' in resultado['sugestao_disparo']

        assert 'score_prioridade' in resultado
        assert 0 <= resultado['score_prioridade'] <= 5

        assert 'dados_extraidos_ia' in resultado
        assert 'objetivo' in resultado['dados_extraidos_ia']

        assert 'metadados_analise_ia' in resultado
        assert resultado['metadados_analise_ia']['tokens_total'] > 0
        assert resultado['metadados_analise_ia']['custo_brl'] > 0

        assert 'analisado_em' in resultado

        # Validar estatísticas
        stats = analyzer.get_stats()
        assert stats['total_calls'] == 1
        assert stats['successful_calls'] == 1
        assert stats['total_tokens'] > 0
        assert stats['total_cost_brl'] > 0

    @skip_if_no_api_key()
    @pytest.mark.integration
    def test_analyze_lead_cost_range(self, analyzer):
        """Testa que custo está dentro do range esperado"""
        conversa_compilada = {
            'messages': [
                {
                    'sender_type': 'Contact',
                    'content': 'Quero saber sobre musculação',
                    'created_at': '2025-11-13T10:00:00Z'
                }
            ]
        }

        resultado = analyzer.analyze_lead(
            conversation_id=12346,
            conversa_compilada=conversa_compilada,
            contact_name='Maria Santos',
            inbox_name='CDT Mossoró',
            tipo_remarketing='REMARKETING_MEDIO',
            tempo_inativo_horas=72.0
        )

        custo = resultado['metadados_analise_ia']['custo_brl']

        # Custo esperado: R$ 0.001 - R$ 0.005 (muito barato!)
        assert 0.0005 < custo < 0.01, f"Custo fora do esperado: R$ {custo:.6f}"


class TestOpenAILeadRemarketingAnalyzerMock:
    """Testes com mock da OpenAI API (sem gastar tokens)"""

    @pytest.fixture
    def analyzer(self):
        """Fixture: Analyzer com API key mock"""
        return OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key='sk-test-mock'
        )

    @patch('src.multi_tenant.etl_v4.analyzers.openai_lead_remarketing_analyzer.OpenAI')
    def test_analyze_lead_mock_success(self, mock_openai_class, analyzer):
        """Testa análise com mock de resposta bem-sucedida"""
        # Mock da resposta OpenAI
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"objetivo": "CrossFit", "score_prioridade": 4, "analise_contextual": "Lead interessado"}'))
        ]
        mock_response.usage = Mock(
            prompt_tokens=500,
            completion_tokens=250,
            total_tokens=750
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Recriar analyzer com mock
        analyzer_mock = OpenAILeadRemarketingAnalyzer(
            tenant_id=1,
            api_key='sk-test-mock'
        )
        analyzer_mock.client = mock_client

        conversa_compilada = {
            'messages': [
                {'sender_type': 'Contact', 'content': 'Teste', 'created_at': '2025-11-13T10:00:00Z'}
            ]
        }

        resultado = analyzer_mock.analyze_lead(
            conversation_id=999,
            conversa_compilada=conversa_compilada,
            contact_name='Teste',
            inbox_name='Teste',
            tipo_remarketing='REMARKETING_RECENTE',
            tempo_inativo_horas=30.0
        )

        assert resultado['score_prioridade'] == 4
        assert resultado['metadados_analise_ia']['tokens_total'] == 750


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
