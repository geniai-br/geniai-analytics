"""
Testes Unitários para TemplateManager
======================================

Testa funcionalidades de:
- Geração de templates por tipo de remarketing
- Aplicação de variáveis dinâmicas
- Formatação de tempo de inatividade
- Validação de templates customizados
- Preview de templates

Fase: 8.1 - Foundation
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

import pytest
from src.multi_tenant.utils.template_manager import TemplateManager


class TestTemplateManager:
    """Testes para TemplateManager"""

    @pytest.fixture
    def template_manager(self):
        """Fixture: TemplateManager com tenant padrão"""
        return TemplateManager(tenant_id=1)

    def test_init(self, template_manager):
        """Testa inicialização do TemplateManager"""
        assert template_manager.tenant_id == 1
        assert template_manager.custom_templates == {}

    def test_get_template_recente(self, template_manager):
        """Testa template REMARKETING_RECENTE"""
        template = template_manager.get_template('REMARKETING_RECENTE')

        assert '{nome}' in template
        assert '{interesse}' in template
        assert '{inbox}' in template
        assert '😊' in template  # Tom casual
        assert len(template) > 0

    def test_get_template_medio(self, template_manager):
        """Testa template REMARKETING_MEDIO"""
        template = template_manager.get_template('REMARKETING_MEDIO')

        assert '{nome}' in template
        assert '{interesse}' in template
        assert '{inbox}' in template
        assert 'dias' in template.lower()
        assert len(template) > 0

    def test_get_template_frio(self, template_manager):
        """Testa template REMARKETING_FRIO"""
        template = template_manager.get_template('REMARKETING_FRIO')

        assert '{nome}' in template
        assert '{interesse}' in template
        assert '{tempo_inativo}' in template
        assert '{inbox}' in template
        assert 'Atenciosamente' in template or 'disposição' in template.lower()
        assert len(template) > 0

    def test_format_tempo_inativo_horas(self, template_manager):
        """Testa formatação de tempo em horas"""
        assert template_manager.format_tempo_inativo(26) == "26 horas"
        assert template_manager.format_tempo_inativo(30) == "30 horas"

    def test_format_tempo_inativo_dias(self, template_manager):
        """Testa formatação de tempo em dias"""
        assert template_manager.format_tempo_inativo(48) == "2 dias"
        assert template_manager.format_tempo_inativo(72) == "3 dias"
        assert template_manager.format_tempo_inativo(24) == "1 dia"

    def test_format_tempo_inativo_semanas(self, template_manager):
        """Testa formatação de tempo em semanas"""
        assert template_manager.format_tempo_inativo(168) == "1 semana"
        assert template_manager.format_tempo_inativo(336) == "2 semanas"
        assert template_manager.format_tempo_inativo(504) == "3 semanas"

    def test_format_tempo_inativo_meses(self, template_manager):
        """Testa formatação de tempo em meses"""
        # 4 semanas = 1 mês
        assert template_manager.format_tempo_inativo(672) == "1 mês"
        # 8 semanas = 2 meses
        assert template_manager.format_tempo_inativo(1344) == "2 meses"

    def test_generate_remarketing_message_recente(self, template_manager):
        """Testa geração de mensagem REMARKETING_RECENTE"""
        dados_extraidos = {
            'objetivo': 'Perda de peso',
            'interesse_especifico': 'CrossFit'
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_RECENTE',
            dados_extraidos=dados_extraidos,
            contact_name='João Silva',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        assert 'João Silva' in mensagem or 'João' in mensagem
        assert 'CrossFit' in mensagem
        assert 'AllpFit' in mensagem
        assert len(mensagem) > 0
        assert '{' not in mensagem  # Todas variáveis aplicadas

    def test_generate_remarketing_message_medio(self, template_manager):
        """Testa geração de mensagem REMARKETING_MEDIO"""
        dados_extraidos = {
            'objetivo': 'Condicionamento físico',
            'interesse_especifico': 'Musculação'
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_MEDIO',
            dados_extraidos=dados_extraidos,
            contact_name='Maria Santos',
            inbox_name='CDT Mossoró',
            tempo_inativo_horas=96.0
        )

        assert 'Maria' in mensagem
        assert 'Musculação' in mensagem
        assert 'CDT Mossoró' in mensagem
        assert len(mensagem) > 0
        assert '{' not in mensagem

    def test_generate_remarketing_message_frio(self, template_manager):
        """Testa geração de mensagem REMARKETING_FRIO"""
        dados_extraidos = {
            'objetivo': 'Emagrecimento',
            'interesse_especifico': 'Personal trainer'
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_FRIO',
            dados_extraidos=dados_extraidos,
            contact_name='Pedro Oliveira',
            inbox_name='AllpFit JP Sul',
            tempo_inativo_horas=200.0
        )

        assert 'Pedro' in mensagem
        assert 'Personal trainer' in mensagem
        assert 'AllpFit JP Sul' in mensagem
        assert '1 semana' in mensagem
        assert len(mensagem) > 0
        assert '{' not in mensagem

    def test_generate_remarketing_message_sem_nome(self, template_manager):
        """Testa geração de mensagem sem nome do contato"""
        dados_extraidos = {
            'objetivo': 'CrossFit',
            'interesse_especifico': 'CrossFit'
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_RECENTE',
            dados_extraidos=dados_extraidos,
            contact_name='',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        # Deve usar 'você' como fallback
        assert 'você' in mensagem.lower()
        assert len(mensagem) > 0

    def test_validate_template_valido(self, template_manager):
        """Testa validação de template válido"""
        template = "Oi {nome}! Interesse em {interesse}? {inbox}"

        valido, erro = template_manager.validate_template(template)

        assert valido is True
        assert erro is None

    def test_validate_template_vazio(self, template_manager):
        """Testa validação de template vazio"""
        valido, erro = template_manager.validate_template("")

        assert valido is False
        assert erro == "Template vazio"

    def test_validate_template_variavel_invalida(self, template_manager):
        """Testa validação de template com variável inválida"""
        template = "Oi {nome}! Sua promoção: {desconto_percentual}"

        valido, erro = template_manager.validate_template(template)

        assert valido is False
        assert 'desconto_percentual' in erro

    def test_validate_template_muito_longo(self, template_manager):
        """Testa validação de template muito longo"""
        template = "A" * 1001

        valido, erro = template_manager.validate_template(template)

        assert valido is False
        assert 'muito longo' in erro.lower()

    def test_set_custom_template(self, template_manager):
        """Testa definição de template customizado"""
        template_custom = "Olá {nome}! Seu interesse em {interesse} foi notado. {inbox}"

        sucesso = template_manager.set_custom_template(
            'REMARKETING_RECENTE',
            template_custom
        )

        assert sucesso is True
        assert template_manager.custom_templates['REMARKETING_RECENTE'] == template_custom

    def test_set_custom_template_invalido(self, template_manager):
        """Testa definição de template customizado inválido"""
        sucesso = template_manager.set_custom_template(
            'REMARKETING_RECENTE',
            ''
        )

        assert sucesso is False

    def test_get_all_templates(self, template_manager):
        """Testa obtenção de todos os templates"""
        templates = template_manager.get_all_templates()

        assert 'REMARKETING_RECENTE' in templates
        assert 'REMARKETING_MEDIO' in templates
        assert 'REMARKETING_FRIO' in templates
        assert 'GENERICO' in templates
        assert len(templates) == 4

    def test_preview_template(self, template_manager):
        """Testa preview de template com dados de exemplo"""
        preview = template_manager.preview_template(
            tipo_remarketing='REMARKETING_RECENTE',
            nome='João Silva',
            objetivo='CrossFit',
            interesse='aulas de CrossFit',
            tempo_inativo_horas=30.0,
            inbox_name='AllpFit'
        )

        assert 'João Silva' in preview
        assert 'CrossFit' in preview
        assert 'AllpFit' in preview
        assert len(preview) > 0
        assert '{' not in preview

    def test_sanitizacao_objetivo_longo(self, template_manager):
        """Testa sanitização de objetivo muito longo"""
        objetivo_longo = "A" * 150
        dados_extraidos = {
            'objetivo': objetivo_longo,
            'interesse_especifico': objetivo_longo
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_RECENTE',
            dados_extraidos=dados_extraidos,
            contact_name='João',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        # Objetivo deve ser truncado
        assert '...' in mensagem
        assert len(mensagem) < len(objetivo_longo) * 2  # Não deve explodir tamanho

    def test_custom_template_sobrescreve_padrao(self, template_manager):
        """Testa que template customizado sobrescreve padrão"""
        template_original = template_manager.get_template('REMARKETING_RECENTE')
        template_custom = "Template customizado: {nome}, {interesse}, {inbox}"

        template_manager.set_custom_template('REMARKETING_RECENTE', template_custom)
        template_novo = template_manager.get_template('REMARKETING_RECENTE')

        assert template_novo != template_original
        assert template_novo == template_custom


class TestTemplateManagerEdgeCases:
    """Testes de casos extremos para TemplateManager"""

    @pytest.fixture
    def template_manager(self):
        return TemplateManager(tenant_id=99)

    def test_tipo_remarketing_desconhecido(self, template_manager):
        """Testa comportamento com tipo de remarketing desconhecido"""
        template = template_manager.get_template('TIPO_INVALIDO')

        # Deve retornar template genérico
        assert len(template) > 0
        assert '{nome}' in template

    def test_dados_extraidos_vazios(self, template_manager):
        """Testa geração com dados extraídos vazios"""
        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_RECENTE',
            dados_extraidos={},
            contact_name='João',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        # Deve usar valores padrão
        assert 'nossos serviços' in mensagem.lower() or 'joão' in mensagem.lower()
        assert len(mensagem) > 0

    def test_tempo_inativo_zero(self, template_manager):
        """Testa formatação com tempo inativo zero"""
        tempo = template_manager.format_tempo_inativo(0)
        assert tempo == "0 horas"

    def test_tempo_inativo_negativo(self, template_manager):
        """Testa formatação com tempo inativo negativo"""
        # Não deveria acontecer, mas testar comportamento
        tempo = template_manager.format_tempo_inativo(-10)
        assert isinstance(tempo, str)

    def test_tenant_id_diferente(self):
        """Testa criação com diferentes tenant IDs"""
        tm1 = TemplateManager(tenant_id=1)
        tm2 = TemplateManager(tenant_id=999)

        assert tm1.tenant_id != tm2.tenant_id
        assert tm1.get_template('REMARKETING_RECENTE') == tm2.get_template('REMARKETING_RECENTE')

    def test_nome_com_caracteres_especiais(self, template_manager):
        """Testa nome com caracteres especiais"""
        dados_extraidos = {
            'objetivo': 'CrossFit',
            'interesse_especifico': 'CrossFit'
        }

        mensagem = template_manager.generate_remarketing_message(
            tipo_remarketing='REMARKETING_RECENTE',
            dados_extraidos=dados_extraidos,
            contact_name='José da Silva Júnior',
            inbox_name='AllpFit',
            tempo_inativo_horas=30.0
        )

        assert 'José' in mensagem
        assert len(mensagem) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
