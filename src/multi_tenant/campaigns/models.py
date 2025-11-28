"""
Models - Dataclasses para o módulo de Campanhas
===============================================

Define as estruturas de dados usadas no sistema de campanhas:
- Campaign: Configuração de uma campanha de remarketing
- CampaignLead: Lead associado a uma campanha com variáveis geradas
- CampaignExport: Registro de exportação CSV

Autor: Isaac (via Claude Code)
Data: 2025-11-26
Atualizado: 2025-11-26 - Adicionado suporte a tipos de campanha flexíveis
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any, List


# =============================================================================
# ENUMS
# =============================================================================

class CampaignType(str, Enum):
    """Tipos de campanha disponíveis"""
    PROMOTIONAL = "promotional"     # Promoções, descontos, ofertas
    REENGAGEMENT = "reengagement"   # Reconquistar leads inativos
    EVENT = "event"                 # Eventos, webinars, convites
    SURVEY = "survey"               # Pesquisas, NPS, feedback
    INFORMATIVE = "informative"     # Comunicados, novidades, avisos
    CUSTOM = "custom"               # Contexto livre personalizado

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        """Retorna label amigável para exibição"""
        labels = {
            "promotional": "Promocional",
            "reengagement": "Reengajamento",
            "event": "Evento/Convite",
            "survey": "Pesquisa/Feedback",
            "informative": "Informativo",
            "custom": "Personalizado"
        }
        return labels.get(self.value, self.value)

    @property
    def icon(self) -> str:
        """Retorna emoji para exibição"""
        icons = {
            "promotional": "💰",
            "reengagement": "🔄",
            "event": "📅",
            "survey": "📋",
            "informative": "📢",
            "custom": "✏️"
        }
        return icons.get(self.value, "📝")

    @property
    def description(self) -> str:
        """Retorna descrição do tipo"""
        descriptions = {
            "promotional": "Descontos, ofertas especiais, vendas",
            "reengagement": "Reconquistar leads inativos que não fecharam",
            "event": "Webinars, aulas, palestras, workshops",
            "survey": "NPS, satisfação, opinião do cliente",
            "informative": "Novidades, avisos, mudanças, comunicados",
            "custom": "Defina seu próprio contexto livremente"
        }
        return descriptions.get(self.value, "")


class CampaignTone(str, Enum):
    """Tons de mensagem disponíveis"""
    URGENT = "urgente"              # Criar senso de escassez/tempo limitado
    FRIENDLY = "amigavel"           # Tom leve e descontraído
    PROFESSIONAL = "profissional"   # Formal mas acolhedor
    EMPATHETIC = "empatico"         # Demonstrar compreensão e cuidado
    EXCITED = "animado"             # Entusiasmado e convidativo
    GRATEFUL = "agradecido"         # Valorizar o cliente
    CURIOUS = "curioso"             # Despertar interesse
    EXCLUSIVE = "exclusivo"         # Fazer o cliente se sentir especial
    DIRECT = "direto"               # Objetivo e sem rodeios

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        """Retorna label amigável para exibição"""
        labels = {
            "urgente": "Urgente",
            "amigavel": "Amigável",
            "profissional": "Profissional",
            "empatico": "Empático",
            "animado": "Animado",
            "agradecido": "Agradecido",
            "curioso": "Curioso",
            "exclusivo": "Exclusivo",
            "direto": "Direto"
        }
        return labels.get(self.value, self.value)

    @property
    def icon(self) -> str:
        """Retorna emoji para exibição"""
        icons = {
            "urgente": "🔥",
            "amigavel": "😊",
            "profissional": "💼",
            "empatico": "💚",
            "animado": "🎉",
            "agradecido": "🙏",
            "curioso": "🤔",
            "exclusivo": "⭐",
            "direto": "📌"
        }
        return icons.get(self.value, "📝")

    @property
    def description(self) -> str:
        """Retorna descrição do tom"""
        descriptions = {
            "urgente": "Criar senso de escassez/tempo limitado",
            "amigavel": "Tom leve e descontraído",
            "profissional": "Formal mas acolhedor",
            "empatico": "Demonstrar compreensão e cuidado",
            "animado": "Entusiasmado e convidativo",
            "agradecido": "Valorizar o cliente",
            "curioso": "Despertar interesse",
            "exclusivo": "Fazer o cliente se sentir especial",
            "direto": "Objetivo e sem rodeios"
        }
        return descriptions.get(self.value, "")


class CampaignStatus(str, Enum):
    """Status possíveis de uma campanha"""
    DRAFT = "draft"       # Rascunho - não processa leads
    ACTIVE = "active"     # Ativa - processa leads
    PAUSED = "paused"     # Pausada temporariamente
    ENDED = "ended"       # Encerrada

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        """Retorna label amigável para exibição"""
        labels = {
            "draft": "Rascunho",
            "active": "Ativa",
            "paused": "Pausada",
            "ended": "Encerrada"
        }
        return labels.get(self.value, self.value)

    @property
    def icon(self) -> str:
        """Retorna emoji para exibição"""
        icons = {
            "draft": "📝",
            "active": "🟢",
            "paused": "⏸️",
            "ended": "⏹️"
        }
        return icons.get(self.value, "❓")


class LeadStatus(str, Enum):
    """Status possíveis de um lead em uma campanha"""
    PENDING = "pending"         # Aguardando processamento
    PROCESSING = "processing"   # Em processamento pela IA
    PROCESSED = "processed"     # Variáveis geradas com sucesso
    EXPORTED = "exported"       # Já foi exportado em CSV
    ERROR = "error"             # Erro na geração
    SKIPPED = "skipped"         # Pulado por regra de negócio

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        """Retorna label amigável para exibição"""
        labels = {
            "pending": "Pendente",
            "processing": "Processando",
            "processed": "Processado",
            "exported": "Exportado",
            "error": "Erro",
            "skipped": "Pulado"
        }
        return labels.get(self.value, self.value)

    @property
    def icon(self) -> str:
        """Retorna emoji para exibição"""
        icons = {
            "pending": "⏳",
            "processing": "🔄",
            "processed": "✅",
            "exported": "📤",
            "error": "❌",
            "skipped": "⏭️"
        }
        return icons.get(self.value, "❓")


@dataclass
class Campaign:
    """
    Representa uma campanha de remarketing.

    Attributes:
        id: ID único da campanha
        tenant_id: ID do tenant dono da campanha
        name: Nome da campanha (ex: "Black Friday 2025")
        slug: Identificador URL-friendly
        description: Descrição opcional
        campaign_type: Tipo da campanha (promotional, reengagement, etc.)
        tone: Tom da mensagem (urgente, amigavel, profissional, etc.)
        briefing: Texto livre descrevendo o objetivo e contexto da campanha
        template_text: Template META/WhatsApp com {{1}}, {{2}}, {{3}}
        template_variable_count: Quantidade de variáveis no template
        promotional_context: Contexto estruturado JSON para a IA (campos específicos por tipo)
        start_date: Data de início da campanha
        end_date: Data de fim da campanha
        status: Status atual (draft, active, paused, ended)
        leads_total: Total de leads na campanha
        leads_processed: Leads processados com sucesso
        leads_exported: Leads já exportados em CSV
        total_cost_brl: Custo total em reais
        last_export_at: Data da última exportação
        last_export_count: Quantidade de leads na última exportação
        created_at: Data de criação
        updated_at: Data de última atualização
        created_by: ID do usuário que criou
    """
    # Identificação
    id: Optional[int] = None
    tenant_id: int = 0
    name: str = ""
    slug: str = ""
    description: Optional[str] = None

    # Tipo e Tom da Campanha (NOVO)
    campaign_type: CampaignType = CampaignType.PROMOTIONAL
    tone: CampaignTone = CampaignTone.PROFESSIONAL

    # Briefing - Texto livre com objetivo/contexto da campanha (NOVO)
    briefing: Optional[str] = None

    # Template
    template_text: str = ""
    template_variable_count: int = 3

    # Contexto Estruturado (JSON) - campos específicos por tipo
    promotional_context: Dict[str, Any] = field(default_factory=dict)

    # Período
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Status
    status: CampaignStatus = CampaignStatus.DRAFT

    # Métricas
    leads_total: int = 0
    leads_processed: int = 0
    leads_exported: int = 0
    total_cost_brl: float = 0.0

    # Última exportação
    last_export_at: Optional[datetime] = None
    last_export_count: int = 0

    # Auditoria
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    def __post_init__(self):
        """Validações e conversões após inicialização"""
        # Converter status string para enum se necessário
        if isinstance(self.status, str):
            self.status = CampaignStatus(self.status)

        # Converter campaign_type string para enum se necessário
        if isinstance(self.campaign_type, str):
            try:
                self.campaign_type = CampaignType(self.campaign_type)
            except ValueError:
                self.campaign_type = CampaignType.CUSTOM

        # Converter tone string para enum se necessário
        if isinstance(self.tone, str):
            try:
                self.tone = CampaignTone(self.tone)
            except ValueError:
                self.tone = CampaignTone.PROFESSIONAL

        # Garantir que promotional_context é dict
        if self.promotional_context is None:
            self.promotional_context = {}

    @property
    def is_active(self) -> bool:
        """Verifica se a campanha está ativa"""
        return self.status == CampaignStatus.ACTIVE

    @property
    def is_editable(self) -> bool:
        """Verifica se a campanha pode ser editada"""
        return self.status in (CampaignStatus.DRAFT, CampaignStatus.PAUSED)

    @property
    def can_process_leads(self) -> bool:
        """Verifica se pode processar leads"""
        return self.status == CampaignStatus.ACTIVE

    @property
    def can_export(self) -> bool:
        """Verifica se pode exportar CSV"""
        return self.leads_processed > 0

    @property
    def progress_percentage(self) -> float:
        """Retorna percentual de progresso (leads processados / total)"""
        if self.leads_total == 0:
            return 0.0
        return round((self.leads_processed / self.leads_total) * 100, 1)

    @property
    def period_display(self) -> str:
        """Retorna período formatado para exibição"""
        if self.start_date and self.end_date:
            return f"{self.start_date.strftime('%d/%m')} - {self.end_date.strftime('%d/%m/%Y')}"
        return "Período não definido"

    def render_preview(self, var1: str = "", var2: str = "", var3: str = "") -> str:
        """
        Renderiza preview da mensagem com variáveis substituídas.

        Args:
            var1: Valor para {{1}}
            var2: Valor para {{2}}
            var3: Valor para {{3}}

        Returns:
            Mensagem com variáveis substituídas
        """
        preview = self.template_text
        preview = preview.replace("{{1}}", var1 or "{{1}}")
        preview = preview.replace("{{2}}", var2 or "{{2}}")
        preview = preview.replace("{{3}}", var3 or "{{3}}")
        return preview

    @property
    def type_display(self) -> str:
        """Retorna tipo formatado para exibição com ícone"""
        return f"{self.campaign_type.icon} {self.campaign_type.label}"

    @property
    def tone_display(self) -> str:
        """Retorna tom formatado para exibição com ícone"""
        return f"{self.tone.icon} {self.tone.label}"

    def get_full_context_for_ai(self) -> str:
        """
        Monta o contexto completo para a IA processar.
        Combina tipo, tom, briefing e detalhes estruturados.

        Returns:
            String formatada com todo o contexto da campanha
        """
        lines = []

        # Tipo e tom
        lines.append(f"TIPO DE CAMPANHA: {self.campaign_type.label}")
        lines.append(f"DESCRIÇÃO DO TIPO: {self.campaign_type.description}")
        lines.append(f"TOM DA MENSAGEM: {self.tone.label} - {self.tone.description}")
        lines.append("")

        # Briefing (se houver)
        if self.briefing:
            lines.append("BRIEFING/OBJETIVO DA CAMPANHA:")
            lines.append(self.briefing)
            lines.append("")

        # Detalhes estruturados (se houver)
        if self.promotional_context:
            lines.append("DETALHES ESPECÍFICOS:")
            for key, value in self.promotional_context.items():
                if value:  # Só incluir se tiver valor
                    # Formatar chave para exibição
                    key_display = key.replace("_", " ").title()
                    lines.append(f"- {key_display}: {value}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "campaign_type": str(self.campaign_type),
            "tone": str(self.tone),
            "briefing": self.briefing,
            "template_text": self.template_text,
            "template_variable_count": self.template_variable_count,
            "promotional_context": self.promotional_context,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": str(self.status),
            "leads_total": self.leads_total,
            "leads_processed": self.leads_processed,
            "leads_exported": self.leads_exported,
            "total_cost_brl": self.total_cost_brl,
            "last_export_at": self.last_export_at.isoformat() if self.last_export_at else None,
            "last_export_count": self.last_export_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        """Cria instância a partir de dicionário"""
        # Converter datas se forem strings
        if isinstance(data.get("start_date"), str):
            data["start_date"] = date.fromisoformat(data["start_date"])
        if isinstance(data.get("end_date"), str):
            data["end_date"] = date.fromisoformat(data["end_date"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if isinstance(data.get("last_export_at"), str):
            data["last_export_at"] = datetime.fromisoformat(data["last_export_at"])

        return cls(**data)


@dataclass
class CampaignLead:
    """
    Representa um lead associado a uma campanha.

    Attributes:
        id: ID único do registro
        campaign_id: ID da campanha
        conversation_id: ID da conversa no Chatwoot
        contact_phone: Telefone do contato
        contact_name: Nome do contato
        var1: Variável {{1}} - tipicamente primeiro nome
        var2: Variável {{2}} - contexto personalizado
        var3: Variável {{3}} - oferta/CTA
        message_preview: Preview da mensagem renderizada
        status: Status do processamento
        error_message: Mensagem de erro se status = error
        generation_metadata: Metadados da geração IA
        export_count: Quantas vezes foi exportado
        last_exported_at: Data da última exportação
        created_at: Data de criação
        processed_at: Data do processamento
        updated_at: Data de última atualização
    """
    # Identificação
    id: Optional[int] = None
    campaign_id: int = 0
    conversation_id: int = 0

    # Dados do lead
    contact_phone: str = ""
    contact_name: Optional[str] = None

    # Variáveis geradas pela IA
    var1: Optional[str] = None  # {{1}} - nome
    var2: Optional[str] = None  # {{2}} - contexto
    var3: Optional[str] = None  # {{3}} - oferta

    # Preview
    message_preview: Optional[str] = None

    # Status
    status: LeadStatus = LeadStatus.PENDING
    error_message: Optional[str] = None

    # Metadados da geração
    generation_metadata: Dict[str, Any] = field(default_factory=dict)

    # Exportação
    export_count: int = 0
    last_exported_at: Optional[datetime] = None

    # Timestamps
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validações e conversões após inicialização"""
        if isinstance(self.status, str):
            self.status = LeadStatus(self.status)
        if self.generation_metadata is None:
            self.generation_metadata = {}

    @property
    def is_processed(self) -> bool:
        """Verifica se foi processado com sucesso"""
        return self.status in (LeadStatus.PROCESSED, LeadStatus.EXPORTED)

    @property
    def is_exportable(self) -> bool:
        """Verifica se pode ser exportado"""
        return self.status in (LeadStatus.PROCESSED, LeadStatus.EXPORTED)

    @property
    def has_error(self) -> bool:
        """Verifica se teve erro"""
        return self.status == LeadStatus.ERROR

    @property
    def first_name(self) -> str:
        """Extrai primeiro nome do contact_name"""
        if not self.contact_name:
            return "você"
        return self.contact_name.split()[0]

    @property
    def formatted_phone(self) -> str:
        """Retorna telefone formatado para exibição"""
        phone = "".join(filter(str.isdigit, self.contact_phone))
        if len(phone) == 13:  # 5511999999999
            return f"+{phone[:2]} {phone[2:4]} {phone[4:9]}-{phone[9:]}"
        elif len(phone) == 11:  # 11999999999
            return f"{phone[:2]} {phone[2:7]}-{phone[7:]}"
        return self.contact_phone

    @property
    def csv_phone(self) -> str:
        """Retorna telefone formatado para CSV (apenas números com DDI)"""
        phone = "".join(filter(str.isdigit, self.contact_phone))
        # Adiciona DDI 55 se não tiver
        if len(phone) <= 11:
            phone = "55" + phone
        return phone

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "conversation_id": self.conversation_id,
            "contact_phone": self.contact_phone,
            "contact_name": self.contact_name,
            "var1": self.var1,
            "var2": self.var2,
            "var3": self.var3,
            "message_preview": self.message_preview,
            "status": str(self.status),
            "error_message": self.error_message,
            "generation_metadata": self.generation_metadata,
            "export_count": self.export_count,
            "last_exported_at": self.last_exported_at.isoformat() if self.last_exported_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_csv_row(self) -> Dict[str, str]:
        """
        Converte para formato de linha CSV do Disparador.

        Formato: telefone, nome, variavel_1, variavel_2
        """
        return {
            "telefone": self.csv_phone,
            "nome": self.var1 or self.first_name,
            "variavel_1": self.var2 or "",
            "variavel_2": self.var3 or "",
        }


@dataclass
class CampaignExport:
    """
    Representa um registro de exportação CSV.

    Attributes:
        id: ID único do registro
        campaign_id: ID da campanha
        file_name: Nome do arquivo exportado
        leads_count: Quantidade de leads exportados
        file_size_bytes: Tamanho do arquivo em bytes
        exported_by: ID do usuário que exportou
        exported_at: Data/hora da exportação
        metadata: Metadados da exportação
        notes: Notas opcionais
    """
    # Identificação
    id: Optional[int] = None
    campaign_id: int = 0

    # Dados da exportação
    file_name: str = ""
    leads_count: int = 0
    file_size_bytes: Optional[int] = None

    # Quem exportou
    exported_by: Optional[int] = None
    exported_at: Optional[datetime] = None

    # Metadados
    metadata: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    def __post_init__(self):
        """Validações após inicialização"""
        if self.metadata is None:
            self.metadata = {}

    @property
    def file_size_display(self) -> str:
        """Retorna tamanho do arquivo formatado"""
        if not self.file_size_bytes:
            return "N/A"
        if self.file_size_bytes < 1024:
            return f"{self.file_size_bytes} B"
        elif self.file_size_bytes < 1024 * 1024:
            return f"{self.file_size_bytes / 1024:.1f} KB"
        else:
            return f"{self.file_size_bytes / (1024 * 1024):.1f} MB"

    @property
    def exported_at_display(self) -> str:
        """Retorna data de exportação formatada"""
        if not self.exported_at:
            return "N/A"
        return self.exported_at.strftime("%d/%m/%Y %H:%M")

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "file_name": self.file_name,
            "leads_count": self.leads_count,
            "file_size_bytes": self.file_size_bytes,
            "exported_by": self.exported_by,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
            "metadata": self.metadata,
            "notes": self.notes,
        }