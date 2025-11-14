"""
Template Manager - Sistema de Remarketing Multi-Tenant
=======================================================

Gerencia templates de mensagens de remarketing baseados em tempo de inatividade.

Tipos de Templates:
- REMARKETING_RECENTE (24-48h): Tom casual, lembrete suave
- REMARKETING_MEDIO (48h-7d): Tom profissional, reengajamento
- REMARKETING_FRIO (7+ dias): Tom formal, resgate

Suporta variáveis dinâmicas:
- {nome}: Nome do lead
- {objetivo}: Objetivo mencionado
- {interesse}: Interesse específico
- {tempo_inativo}: Tempo formatado (ex: "2 dias")
- {inbox}: Nome do inbox

Fase: 8.1 - Foundation
Relacionado: docs/private/checkpoints/FASE8_ANALISE_OPENAI.md
Autor: Isaac (via Claude Code)
Data: 2025-11-14
"""

import logging
from typing import Dict, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Gerenciador de templates de remarketing com suporte a variáveis dinâmicas.

    IMPORTANTE: Templates são GENÉRICOS e NÃO mencionam promoções/ofertas
    específicas que não controlamos. Foco em informações e suporte.
    """

    def __init__(self, tenant_id: int, custom_templates: Optional[Dict[str, str]] = None):
        """
        Inicializa o Template Manager.

        Args:
            tenant_id: ID do tenant
            custom_templates: Templates customizados por tenant (opcional)
        """
        self.tenant_id = tenant_id
        self.custom_templates = custom_templates or {}

        logger.info(f"TemplateManager inicializado para tenant {tenant_id}")

    def get_template(self, tipo_remarketing: str) -> str:
        """
        Retorna template baseado no tipo de remarketing.

        Args:
            tipo_remarketing: REMARKETING_RECENTE, MEDIO ou FRIO

        Returns:
            Template de mensagem
        """
        # Verificar se tenant tem template customizado
        if tipo_remarketing in self.custom_templates:
            return self.custom_templates[tipo_remarketing]

        # Templates padrão (genéricos)
        templates = {
            'REMARKETING_RECENTE': self._get_template_recente(),
            'REMARKETING_MEDIO': self._get_template_medio(),
            'REMARKETING_FRIO': self._get_template_frio(),
        }

        return templates.get(tipo_remarketing, self._get_template_generico())

    def _get_template_recente(self) -> str:
        """
        Template para leads inativos 24-48h.

        Tom: Casual, amigável
        Estratégia: Lembrete suave, retomar conversa
        """
        return """Oi {nome}! 😊

Vi que você demonstrou interesse em {interesse} há pouco tempo. Ficou com alguma dúvida?

Ainda tenho informações que podem te ajudar na decisão. Me avisa se quiser conversar!

{inbox}"""

    def _get_template_medio(self) -> str:
        """
        Template para leads inativos 48h-7d.

        Tom: Profissional, direto
        Estratégia: Reengajamento, verificar interesse contínuo
        """
        return """Oi {nome}!

Vi que você perguntou sobre {interesse} há alguns dias. Ainda tem interesse?

Gostaria de saber se posso te passar mais informações ou tirar alguma dúvida.

{inbox}"""

    def _get_template_frio(self) -> str:
        """
        Template para leads inativos 7+ dias.

        Tom: Formal, respeitoso
        Estratégia: Resgate, oferecer suporte
        """
        return """Olá {nome},

Notamos seu interesse em {interesse} há {tempo_inativo}.

Gostaria de verificar se ainda tem interesse ou se posso ajudar com alguma informação adicional.

Estou à disposição.

Atenciosamente,
{inbox}"""

    def _get_template_generico(self) -> str:
        """
        Template genérico (fallback).

        Usado quando tipo de remarketing não é reconhecido.
        """
        return """Oi {nome}!

Vi sua conversa conosco há {tempo_inativo} e gostaria de saber se ainda tem interesse.

Estou à disposição para tirar qualquer dúvida! 😊

{inbox}"""

    def format_tempo_inativo(self, horas: float) -> str:
        """
        Formata tempo de inatividade de forma legível.

        Args:
            horas: Horas de inatividade

        Returns:
            Tempo formatado (ex: "2 dias", "1 semana", "26 horas")
        """
        if horas < 48:
            return f"{int(horas)} horas"
        elif horas < 168:  # < 7 dias
            dias = int(horas / 24)
            return f"{dias} dias" if dias > 1 else "1 dia"
        else:  # 7+ dias
            semanas = int(horas / 168)
            if semanas == 1:
                return "1 semana"
            elif semanas < 4:
                return f"{semanas} semanas"
            else:
                meses = int(semanas / 4)
                return f"{meses} meses" if meses > 1 else "1 mês"

    def generate_remarketing_message(
        self,
        tipo_remarketing: str,
        dados_extraidos: Dict[str, Any],
        contact_name: str,
        inbox_name: str,
        tempo_inativo_horas: float
    ) -> str:
        """
        Gera mensagem de remarketing personalizada baseada em template.

        Args:
            tipo_remarketing: Tipo de remarketing (RECENTE, MEDIO, FRIO)
            dados_extraidos: Dados extraídos pela IA
            contact_name: Nome do contato
            inbox_name: Nome do inbox
            tempo_inativo_horas: Horas de inatividade

        Returns:
            Mensagem de remarketing personalizada
        """
        # Obter template
        template = self.get_template(tipo_remarketing)

        # Preparar variáveis
        nome = contact_name or 'você'
        objetivo = dados_extraidos.get('objetivo', 'nossos serviços')
        interesse = dados_extraidos.get('interesse_especifico', objetivo)
        tempo_inativo = self.format_tempo_inativo(tempo_inativo_horas)
        inbox = inbox_name or 'Equipe'

        # Sanitizar variáveis (evitar valores muito longos)
        if len(objetivo) > 100:
            objetivo = objetivo[:100] + '...'
        if len(interesse) > 100:
            interesse = interesse[:100] + '...'

        # Aplicar variáveis no template
        try:
            mensagem = template.format(
                nome=nome,
                objetivo=objetivo,
                interesse=interesse,
                tempo_inativo=tempo_inativo,
                inbox=inbox
            )
        except KeyError as e:
            logger.warning(
                f"Variável ausente no template: {e}. "
                f"Usando template genérico."
            )
            # Fallback para template genérico
            template_generico = self._get_template_generico()
            mensagem = template_generico.format(
                nome=nome,
                objetivo=objetivo,
                interesse=interesse,
                tempo_inativo=tempo_inativo,
                inbox=inbox
            )

        return mensagem.strip()

    def validate_template(self, template: str) -> tuple[bool, Optional[str]]:
        """
        Valida se um template é válido.

        Args:
            template: Template a validar

        Returns:
            Tupla (válido, mensagem_erro)
        """
        # Verificar se template não está vazio
        if not template or not template.strip():
            return False, "Template vazio"

        # Verificar variáveis suportadas
        variaveis_suportadas = {
            'nome', 'objetivo', 'interesse', 'tempo_inativo', 'inbox'
        }

        # Extrair variáveis do template
        import re
        variaveis_encontradas = set(re.findall(r'\{(\w+)\}', template))

        # Verificar variáveis não suportadas
        variaveis_invalidas = variaveis_encontradas - variaveis_suportadas
        if variaveis_invalidas:
            return False, f"Variáveis inválidas: {', '.join(variaveis_invalidas)}"

        # Verificar tamanho razoável
        if len(template) > 1000:
            return False, "Template muito longo (max 1000 caracteres)"

        return True, None

    def set_custom_template(self, tipo_remarketing: str, template: str) -> bool:
        """
        Define template customizado para um tipo de remarketing.

        Args:
            tipo_remarketing: Tipo de remarketing
            template: Template customizado

        Returns:
            True se template foi definido com sucesso
        """
        # Validar template
        valido, erro = self.validate_template(template)
        if not valido:
            logger.error(
                f"Template inválido para {tipo_remarketing}: {erro}"
            )
            return False

        # Salvar template customizado
        self.custom_templates[tipo_remarketing] = template
        logger.info(
            f"Template customizado definido para tenant {self.tenant_id} - "
            f"Tipo: {tipo_remarketing}"
        )

        return True

    def get_all_templates(self) -> Dict[str, str]:
        """
        Retorna todos os templates disponíveis (padrão + customizados).

        Returns:
            Dict com todos os templates
        """
        templates = {
            'REMARKETING_RECENTE': self.get_template('REMARKETING_RECENTE'),
            'REMARKETING_MEDIO': self.get_template('REMARKETING_MEDIO'),
            'REMARKETING_FRIO': self.get_template('REMARKETING_FRIO'),
            'GENERICO': self._get_template_generico(),
        }

        return templates

    def preview_template(
        self,
        tipo_remarketing: str,
        nome: str = "João Silva",
        objetivo: str = "CrossFit",
        interesse: str = "aulas de CrossFit",
        tempo_inativo_horas: float = 30.0,
        inbox_name: str = "AllpFit"
    ) -> str:
        """
        Gera preview de template com dados de exemplo.

        Args:
            tipo_remarketing: Tipo de remarketing
            nome: Nome de exemplo
            objetivo: Objetivo de exemplo
            interesse: Interesse de exemplo
            tempo_inativo_horas: Horas de exemplo
            inbox_name: Inbox de exemplo

        Returns:
            Preview da mensagem
        """
        template = self.get_template(tipo_remarketing)
        tempo_inativo = self.format_tempo_inativo(tempo_inativo_horas)

        mensagem = template.format(
            nome=nome,
            objetivo=objetivo,
            interesse=interesse,
            tempo_inativo=tempo_inativo,
            inbox=inbox_name
        )

        return mensagem.strip()
