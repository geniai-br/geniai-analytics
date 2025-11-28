"""
Campaigns Page - Gerenciamento de Campanhas de Disparo
======================================================

Interface para criação, edição e gerenciamento de campanhas de remarketing.
Parte da Fase 10 - Sistema de Preparação de Dados para Campanhas.

Funcionalidades:
    - Listagem de campanhas do tenant
    - Criação de novas campanhas
    - Edição de campanhas existentes
    - Preview do template renderizado
    - Ativar/Pausar/Encerrar campanhas
    - Visualização de métricas

Autor: Isaac (via Claude Code)
Data: 2025-11-26
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import json

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sqlalchemy import text
from multi_tenant.auth import get_database_engine
from multi_tenant.auth.middleware import set_rls_context
from multi_tenant.campaigns import (
    Campaign,
    CampaignService,
    CampaignCSVExporter,
    CampaignStatus,
    CampaignType,
    CampaignTone,
    LeadStatus,
)

# ============================================================================
# CONSTANTES DE DISPLAY
# ============================================================================

STATUS_DISPLAY = {
    CampaignStatus.DRAFT: {"label": "Rascunho", "color": "#64748b", "icon": "RASCUNHO"},
    CampaignStatus.ACTIVE: {"label": "Ativa", "color": "#10B981", "icon": "ATIVA"},
    CampaignStatus.PAUSED: {"label": "Pausada", "color": "#F59E0B", "icon": "PAUSADA"},
    CampaignStatus.ENDED: {"label": "Encerrada", "color": "#EF4444", "icon": "ENCERRADA"},
}

LEAD_STATUS_DISPLAY = {
    LeadStatus.PENDING: {"label": "Pendente", "color": "#64748b", "icon": "⏳"},
    LeadStatus.PROCESSING: {"label": "Processando", "color": "#3B82F6", "icon": "🔄"},
    LeadStatus.PROCESSED: {"label": "Processado", "color": "#10B981", "icon": "✅"},
    LeadStatus.EXPORTED: {"label": "Exportado", "color": "#8B5CF6", "icon": "📤"},
    LeadStatus.ERROR: {"label": "Erro", "color": "#EF4444", "icon": "❌"},
    LeadStatus.SKIPPED: {"label": "Ignorado", "color": "#9CA3AF", "icon": "⏭️"},
}

# Template padrão sugerido
DEFAULT_TEMPLATE = """Olá, {{1}}.

Vi que {{2}}
Hoje {{3}}
Confirme abaixo!"""

# ============================================================================
# TIPOS DE CAMPANHA E CONFIGURAÇÕES
# ============================================================================

CAMPAIGN_TYPES = {
    "promotional": {
        "label": "💰 Promocional",
        "description": "Descontos, ofertas especiais, vendas",
        "icon": "💰",
        "suggested_template": "Olá, {{1}}.\n\nVi que {{2}}\nHoje {{3}}\nConfirme abaixo!",
        "fields": [
            {"key": "oferta", "label": "Oferta Principal", "placeholder": "Ex: 40% de desconto na matrícula", "required": True},
            {"key": "preco_de", "label": "Preço Original (De)", "placeholder": "Ex: R$ 199/mês"},
            {"key": "preco_por", "label": "Preço Promocional (Por)", "placeholder": "Ex: R$ 119/mês"},
            {"key": "validade", "label": "Validade", "placeholder": "Ex: até domingo, 30/Nov"},
            {"key": "condicoes", "label": "Condições", "placeholder": "Ex: Apenas novos alunos"},
            {"key": "bonus", "label": "Bônus/Extras", "placeholder": "Ex: + 1 mês grátis + kit"},
        ],
        "tones": ["urgente", "amigavel", "profissional"],
        "default_tone": "urgente"
    },
    "reengagement": {
        "label": "🔄 Reengajamento",
        "description": "Reconquistar leads inativos que não fecharam",
        "icon": "🔄",
        "suggested_template": "Oi, {{1}}!\n\n{{2}}\n{{3}}",
        "fields": [
            {"key": "motivo_contato", "label": "Motivo do Contato", "placeholder": "Ex: Sentimos sua falta! / Lembrei de você...", "required": True},
            {"key": "beneficio_voltar", "label": "Benefício de Voltar", "placeholder": "Ex: Aula experimental gratuita"},
            {"key": "diferencial", "label": "O Que Mudou/Novidade", "placeholder": "Ex: Novos horários, nova modalidade"},
            {"key": "facilitador", "label": "Facilitador/Incentivo", "placeholder": "Ex: Sem taxa de matrícula, primeira semana grátis"},
        ],
        "tones": ["empatico", "amigavel", "curioso"],
        "default_tone": "empatico"
    },
    "event": {
        "label": "📅 Evento/Convite",
        "description": "Webinars, aulas, palestras, workshops",
        "icon": "📅",
        "suggested_template": "{{1}}, tudo bem?\n\n{{2}}\n{{3}}",
        "fields": [
            {"key": "nome_evento", "label": "Nome do Evento", "placeholder": "Ex: Workshop de Produtividade", "required": True},
            {"key": "data_hora", "label": "Data e Hora", "placeholder": "Ex: Sábado, 30/Nov às 10h"},
            {"key": "local", "label": "Local/Formato", "placeholder": "Ex: Online via Zoom / Presencial na unidade Centro"},
            {"key": "beneficio", "label": "Por Que Participar", "placeholder": "Ex: Aprenda técnicas exclusivas + certificado"},
            {"key": "vagas", "label": "Vagas/Urgência", "placeholder": "Ex: Apenas 20 vagas / Últimas vagas"},
        ],
        "tones": ["animado", "profissional", "exclusivo"],
        "default_tone": "animado"
    },
    "survey": {
        "label": "📋 Pesquisa/Feedback",
        "description": "NPS, satisfação, opinião do cliente",
        "icon": "📋",
        "suggested_template": "Oi, {{1}}!\n\n{{2}}\n{{3}}",
        "fields": [
            {"key": "objetivo", "label": "Objetivo da Pesquisa", "placeholder": "Ex: Queremos melhorar nosso atendimento", "required": True},
            {"key": "tempo", "label": "Tempo Estimado", "placeholder": "Ex: Leva menos de 2 minutos"},
            {"key": "incentivo", "label": "Incentivo (se houver)", "placeholder": "Ex: Concorra a 1 mês grátis"},
            {"key": "importancia", "label": "Por Que é Importante", "placeholder": "Ex: Sua opinião nos ajuda a melhorar"},
        ],
        "tones": ["amigavel", "agradecido", "profissional"],
        "default_tone": "agradecido"
    },
    "informative": {
        "label": "📢 Informativo",
        "description": "Novidades, avisos, mudanças, comunicados",
        "icon": "📢",
        "suggested_template": "Olá, {{1}}.\n\n{{2}}\n{{3}}",
        "fields": [
            {"key": "assunto", "label": "Assunto Principal", "placeholder": "Ex: Novos horários de funcionamento", "required": True},
            {"key": "detalhes", "label": "Detalhes/Mudanças", "placeholder": "Ex: A partir de dezembro, abrimos aos domingos"},
            {"key": "impacto", "label": "Como Isso Afeta o Cliente", "placeholder": "Ex: Mais opções para você treinar"},
            {"key": "acao", "label": "Ação Esperada (se houver)", "placeholder": "Ex: Agende seu horário pelo app"},
        ],
        "tones": ["profissional", "direto", "amigavel"],
        "default_tone": "profissional"
    },
    "custom": {
        "label": "✏️ Personalizado",
        "description": "Defina seu próprio contexto livremente",
        "icon": "✏️",
        "suggested_template": "Olá, {{1}}.\n\n{{2}}\n{{3}}",
        "fields": [],  # Sem campos pré-definidos
        "tones": ["profissional", "amigavel", "urgente", "empatico", "animado"],
        "default_tone": "profissional"
    }
}

TONE_DESCRIPTIONS = {
    "urgente": "🔥 Urgente - Criar senso de escassez/tempo limitado",
    "amigavel": "😊 Amigável - Tom leve e descontraído",
    "profissional": "💼 Profissional - Formal mas acolhedor",
    "empatico": "💚 Empático - Demonstrar compreensão e cuidado",
    "animado": "🎉 Animado - Entusiasmado e convidativo",
    "agradecido": "🙏 Agradecido - Valorizar o cliente",
    "curioso": "🤔 Curioso - Despertar interesse",
    "exclusivo": "⭐ Exclusivo - Fazer o cliente se sentir especial",
    "direto": "📌 Direto - Objetivo e sem rodeios"
}

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

CAMPAIGNS_CSS = """
<style>
/* Cards de campanha */
.campaign-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}

.campaign-card:hover {
    border-color: #4a5568;
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.campaign-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
}

.campaign-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #fff;
    margin: 0;
}

.campaign-status {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.campaign-meta {
    display: flex;
    gap: 1.5rem;
    color: #a0aec0;
    font-size: 0.875rem;
    margin-bottom: 1rem;
}

.campaign-metrics {
    display: flex;
    gap: 1rem;
    margin-top: 1rem;
}

.metric-box {
    background: rgba(255,255,255,0.05);
    padding: 0.75rem 1rem;
    border-radius: 8px;
    text-align: center;
    flex: 1;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
}

.metric-label {
    font-size: 0.75rem;
    color: #a0aec0;
    text-transform: uppercase;
}

/* Botões de ação */
.action-buttons {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}

/* Preview do template */
.template-preview {
    background: #1a1a2e;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 1rem;
    font-family: monospace;
    white-space: pre-wrap;
    color: #e2e8f0;
}

.template-variable {
    background: #3182ce;
    color: #fff;
    padding: 0.125rem 0.375rem;
    border-radius: 4px;
    font-weight: 600;
}

/* Form sections */
.form-section {
    background: rgba(255,255,255,0.02);
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.form-section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 3rem;
    color: #a0aec0;
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

/* Status badges */
.status-draft { background: #64748b; color: #fff; }
.status-active { background: #10B981; color: #fff; }
.status-paused { background: #F59E0B; color: #000; }
.status-ended { background: #EF4444; color: #fff; }
</style>
"""


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def get_campaign_service(tenant_id: int) -> CampaignService:
    """Retorna instância do CampaignService"""
    engine = get_database_engine()
    return CampaignService(engine, tenant_id)


def format_date_br(d: date) -> str:
    """Formata data no padrão brasileiro"""
    if not d:
        return "-"
    return d.strftime("%d/%m/%Y")


def format_datetime_br(dt: datetime) -> str:
    """Formata datetime no padrão brasileiro"""
    if not dt:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M")


def render_status_badge(status: CampaignStatus) -> str:
    """Renderiza badge de status"""
    info = STATUS_DISPLAY.get(status, {"label": str(status), "color": "#64748b", "icon": "❓"})
    return f"{info['icon']} {info['label']}"


def highlight_template_variables(template: str) -> str:
    """Destaca variáveis no template para exibição"""
    import re
    highlighted = template
    for match in re.findall(r'\{\{\d+\}\}', template):
        highlighted = highlighted.replace(
            match,
            f'<span class="template-variable">{match}</span>'
        )
    return highlighted


# ============================================================================
# COMPONENTES DE UI
# ============================================================================

def render_campaign_card(campaign: Campaign, service: CampaignService):
    """Renderiza card de uma campanha"""
    status_info = STATUS_DISPLAY.get(campaign.status, {"label": str(campaign.status), "color": "#64748b", "icon": "❓"})

    # Obter info do tipo da campanha
    campaign_type_key = "promotional"  # default
    if hasattr(campaign, 'campaign_type') and campaign.campaign_type:
        if hasattr(campaign.campaign_type, 'value'):
            campaign_type_key = campaign.campaign_type.value
        else:
            campaign_type_key = str(campaign.campaign_type)

    type_info = CAMPAIGN_TYPES.get(campaign_type_key, {"label": "Campanha", "icon": "📢"})

    # Container do card
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"### {status_info['icon']} {campaign.name}")
            # Mostrar tipo da campanha logo abaixo do nome
            st.markdown(f"**{type_info['icon']} {type_info['label'].replace(type_info['icon'], '').strip()}**")
            if campaign.description:
                st.caption(campaign.description)

            # Meta info
            meta_cols = st.columns(4)
            with meta_cols[0]:
                st.markdown(f"**Período:** {campaign.period_display}")
            with meta_cols[1]:
                st.markdown(f"**Status:** {status_info['label']}")
            with meta_cols[2]:
                st.markdown(f"**Leads:** {campaign.leads_total}")
            with meta_cols[3]:
                st.markdown(f"**Processados:** {campaign.leads_processed}")

        with col2:
            # Menu de ações
            st.markdown("**Ações**")

            # Botão Ver/Editar
            if st.button("✏️ Editar", key=f"edit_{campaign.id}", use_container_width=True):
                st.session_state['editing_campaign_id'] = campaign.id
                st.session_state['campaigns_view'] = 'edit'
                st.rerun()

            # Botões de status
            if campaign.status == CampaignStatus.DRAFT:
                if st.button("🟢 Ativar", key=f"activate_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.ACTIVE)
                    st.success("Campanha ativada!")
                    st.rerun()

            elif campaign.status == CampaignStatus.ACTIVE:
                if st.button("⏸️ Pausar", key=f"pause_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.PAUSED)
                    st.info("Campanha pausada")
                    st.rerun()

                if st.button("⏹️ Encerrar", key=f"end_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.ENDED)
                    st.warning("Campanha encerrada")
                    st.rerun()

            elif campaign.status == CampaignStatus.PAUSED:
                if st.button("🟢 Reativar", key=f"reactivate_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.ACTIVE)
                    st.success("Campanha reativada!")
                    st.rerun()

                if st.button("⏹️ Encerrar", key=f"end_paused_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.ENDED)
                    st.warning("Campanha encerrada")
                    st.rerun()

            elif campaign.status == CampaignStatus.ENDED:
                if st.button("🔄 Reativar", key=f"reactivate_ended_{campaign.id}", use_container_width=True):
                    service.update_campaign(campaign.id, status=CampaignStatus.ACTIVE)
                    st.success("Campanha reativada!")
                    st.rerun()

        # Botão Gerenciar Leads (sempre disponível)
        st.markdown("---")
        if st.button("👥 Gerenciar Leads", key=f"leads_{campaign.id}", type="primary", use_container_width=True):
            st.session_state['managing_campaign_id'] = campaign.id
            st.session_state['campaigns_view'] = 'leads'
            st.rerun()

        # Métricas
        st.markdown("---")
        metric_cols = st.columns(5)
        with metric_cols[0]:
            st.metric("Total Leads", campaign.leads_total)
        with metric_cols[1]:
            st.metric("Processados", campaign.leads_processed)
        with metric_cols[2]:
            st.metric("Exportados", campaign.leads_exported)
        with metric_cols[3]:
            st.metric("Custo (R$)", f"{campaign.total_cost_brl:.2f}")
        with metric_cols[4]:
            progress = campaign.progress_percentage
            st.metric("Progresso", f"{progress:.0f}%")

        st.markdown("---")


def render_campaign_form(
    service: CampaignService,
    campaign: Campaign = None,
    is_edit: bool = False
):
    """
    Renderiza formulário de criação/edição de campanha com sistema flexível por tipo.

    O formulário é organizado em etapas lógicas:
    1. Identificação + Tipo de Campanha
    2. Briefing da Campanha (obrigatório)
    3. Detalhes Estruturados (campos dinâmicos por tipo)
    4. Tom da Mensagem + Template
    5. Período

    Args:
        service: CampaignService instance
        campaign: Campaign para edição (None para criação)
        is_edit: Se True, é edição; False é criação
    """
    st.markdown("---")

    form_title = "✏️ Editar Campanha" if is_edit else "➕ Nova Campanha"
    st.subheader(form_title)

    # =========================================================================
    # VALORES PADRÃO (para edição ou criação)
    # =========================================================================
    default_name = campaign.name if campaign else ""
    default_description = campaign.description if campaign else ""
    default_template = campaign.template_text if campaign else DEFAULT_TEMPLATE
    default_start = campaign.start_date if campaign else date.today()
    default_end = campaign.end_date if campaign else date.today() + timedelta(days=7)
    default_context = campaign.promotional_context if campaign else {}
    default_briefing = campaign.briefing if campaign else ""

    # Tipo e tom padrão
    default_campaign_type = "promotional"
    default_tone = "profissional"

    if campaign:
        # Extrair tipo do campaign_type (CampaignType enum ou string)
        if hasattr(campaign, 'campaign_type') and campaign.campaign_type:
            if hasattr(campaign.campaign_type, 'value'):
                default_campaign_type = campaign.campaign_type.value
            else:
                default_campaign_type = str(campaign.campaign_type)

        # Extrair tom do tone (CampaignTone enum ou string)
        if hasattr(campaign, 'tone') and campaign.tone:
            if hasattr(campaign.tone, 'value'):
                default_tone = campaign.tone.value
            else:
                default_tone = str(campaign.tone)

    # Índice do tipo selecionado
    type_keys = list(CAMPAIGN_TYPES.keys())
    default_type_index = type_keys.index(default_campaign_type) if default_campaign_type in type_keys else 0

    # =========================================================================
    # ETAPA 1: TIPO DE CAMPANHA (fora do form para reatividade)
    # =========================================================================
    st.markdown("### 1️⃣ Tipo de Campanha")
    st.caption("Selecione o tipo que melhor descreve o objetivo da sua campanha")

    # Opções formatadas para o selectbox
    type_options = [f"{CAMPAIGN_TYPES[k]['label']} - {CAMPAIGN_TYPES[k]['description']}" for k in type_keys]

    selected_type_idx = st.selectbox(
        "Tipo da Campanha *",
        options=range(len(type_options)),
        format_func=lambda i: type_options[i],
        index=default_type_index,
        key="campaign_type_selector",
        help="O tipo define quais campos serão mostrados e como a IA gerará as mensagens"
    )

    selected_type_key = type_keys[selected_type_idx]
    selected_type_config = CAMPAIGN_TYPES[selected_type_key]

    # Info sobre o tipo selecionado
    st.info(f"**{selected_type_config['label']}**: {selected_type_config['description']}")

    # =========================================================================
    # FORM PRINCIPAL
    # =========================================================================
    with st.form(key="campaign_form"):
        # =====================================================================
        # ETAPA 2: IDENTIFICAÇÃO
        # =====================================================================
        st.markdown("### 2️⃣ Identificação")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Nome da Campanha *",
                value=default_name,
                placeholder="Ex: Black Friday 2025",
                help="Nome descritivo para identificar a campanha"
            )
        with col2:
            description = st.text_input(
                "Descrição (opcional)",
                value=default_description or "",
                placeholder="Ex: Promoção de fim de ano para reconquistar leads",
                help="Descrição breve da campanha"
            )

        # =====================================================================
        # ETAPA 3: BRIEFING (CRUCIAL!)
        # =====================================================================
        st.markdown("### 3️⃣ Briefing da Campanha")
        st.caption(
            "**Descreva em texto livre o objetivo e contexto completo da campanha.** "
            "A IA usará este briefing para personalizar as mensagens de cada lead."
        )

        briefing = st.text_area(
            "Briefing *",
            value=default_briefing,
            height=150,
            placeholder="""Exemplo para campanha de Reengajamento:

Queremos reconquistar leads que demonstraram interesse em CrossFit mas não fecharam matrícula.
Muitos mencionaram preocupação com preço ou falta de tempo.

Estamos oferecendo:
- Aula experimental gratuita
- Avaliação física de cortesia
- Horários flexíveis (6h às 22h)
- Desconto de 30% para quem fechar até sexta

O tom deve ser empático, reconhecendo as objeções deles e mostrando que temos soluções.""",
            help="Quanto mais detalhado o briefing, melhor será a personalização das mensagens"
        )

        # =====================================================================
        # ETAPA 4: DETALHES ESTRUTURADOS (DINÂMICO POR TIPO)
        # =====================================================================
        st.markdown("### 4️⃣ Detalhes Estruturados")

        type_fields = selected_type_config.get('fields', [])

        if type_fields:
            st.caption(f"Campos específicos para campanhas **{selected_type_config['label']}**")

            # Renderizar campos em 2 colunas
            field_values = {}
            cols = st.columns(2)

            for i, field in enumerate(type_fields):
                col_idx = i % 2
                with cols[col_idx]:
                    field_key = field['key']
                    field_label = field['label']
                    if field.get('required'):
                        field_label += " *"

                    field_values[field_key] = st.text_input(
                        field_label,
                        value=default_context.get(field_key, ""),
                        placeholder=field.get('placeholder', ''),
                        key=f"field_{field_key}"
                    )
        else:
            # Tipo custom - sem campos pré-definidos
            st.info(
                "Tipo **Personalizado** selecionado. "
                "Use o Briefing acima para descrever todos os detalhes da campanha. "
                "Você também pode adicionar informações extras abaixo."
            )
            field_values = {}

        # Campo adicional sempre disponível
        st.markdown("---")
        informacoes_extras = st.text_area(
            "Informações Extras (opcional)",
            value=default_context.get("informacoes_extras", ""),
            height=80,
            placeholder="Qualquer outra informação relevante para a IA...",
            help="Informações adicionais que não se encaixam nos campos acima"
        )

        # =====================================================================
        # ETAPA 5: TOM DA MENSAGEM
        # =====================================================================
        st.markdown("### 5️⃣ Tom da Mensagem")

        available_tones = selected_type_config.get('tones', list(TONE_DESCRIPTIONS.keys()))
        default_type_tone = selected_type_config.get('default_tone', 'profissional')

        # Se editando, usar o tom salvo; senão usar o padrão do tipo
        tone_to_select = default_tone if is_edit else default_type_tone

        # Encontrar índice do tom
        tone_index = available_tones.index(tone_to_select) if tone_to_select in available_tones else 0

        # Formatar opções de tom
        tone_options = [TONE_DESCRIPTIONS.get(t, t) for t in available_tones]

        selected_tone_idx = st.selectbox(
            "Tom da Mensagem *",
            options=range(len(tone_options)),
            format_func=lambda i: tone_options[i],
            index=tone_index,
            key="tone_selector",
            help="O tom influencia como a IA escreverá as mensagens"
        )

        selected_tone = available_tones[selected_tone_idx]

        # =====================================================================
        # ETAPA 6: TEMPLATE (apenas placeholder - o real fica fora do form)
        # =====================================================================
        st.markdown("### 6️⃣ Template da Mensagem (META/WhatsApp)")
        st.caption("Use {{1}}, {{2}}, {{3}} para as variáveis que serão preenchidas pela IA")
        st.info("⬇️ O campo de Template está logo abaixo do formulário para permitir preview em tempo real")

        # =====================================================================
        # ETAPA 7: PERÍODO
        # =====================================================================
        st.markdown("### 7️⃣ Período da Campanha")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Data de Início *",
                value=default_start,
                help="Quando a campanha começa"
            )
        with col2:
            end_date = st.date_input(
                "Data de Fim *",
                value=default_end,
                help="Quando a campanha termina"
            )

        # =====================================================================
        # BOTÕES
        # =====================================================================
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            submitted = st.form_submit_button(
                "💾 Salvar Campanha",
                type="primary",
                use_container_width=True
            )
        with col2:
            if is_edit:
                cancel = st.form_submit_button(
                    "❌ Cancelar",
                    use_container_width=True
                )
            else:
                cancel = False

    # =========================================================================
    # TEMPLATE COM PREVIEW EM TEMPO REAL (fora do form)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 📝 Template da Mensagem")

    # Sugerir template do tipo selecionado
    suggested_template = selected_type_config.get('suggested_template', DEFAULT_TEMPLATE)

    # Usar template existente se editando, senão sugerido
    template_value = default_template if is_edit else suggested_template

    # Inicializar session_state para o template se necessário
    template_key = "campaign_template_text"
    if template_key not in st.session_state:
        st.session_state[template_key] = template_value

    # Campo de template fora do form - atualiza em tempo real
    template_text = st.text_area(
        "Template *",
        value=st.session_state.get(template_key, template_value),
        height=150,
        help="Template com variáveis {{1}}, {{2}}, {{3}} que serão substituídas pela IA",
        key=template_key
    )

    # Preview em tempo real
    if template_text:
        st.markdown("**Preview em tempo real:**")
        preview_text = template_text.replace(
            "{{1}}", "**[NOME]**"
        ).replace(
            "{{2}}", "**[CONTEXTO PERSONALIZADO]**"
        ).replace(
            "{{3}}", "**[OFERTA/CTA]**"
        )
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; white-space: pre-wrap; font-family: system-ui;">
{preview_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # PROCESSAR SUBMISSÃO
    # =========================================================================
    if submitted:
        # Validações
        errors = []

        if not name or not name.strip():
            errors.append("Nome da campanha é obrigatório")

        if not briefing or not briefing.strip():
            errors.append("Briefing é obrigatório - descreva o objetivo da campanha")

        if not template_text or "{{" not in template_text:
            errors.append("Template deve conter pelo menos uma variável {{N}}")

        if end_date < start_date:
            errors.append("Data de fim deve ser maior ou igual à data de início")

        # Validar campos obrigatórios do tipo
        for field in type_fields:
            if field.get('required') and not field_values.get(field['key'], '').strip():
                errors.append(f"Campo '{field['label']}' é obrigatório")

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
            return

        # Montar promotional_context com campos estruturados
        promotional_context = {}
        for field_key, field_value in field_values.items():
            if field_value and field_value.strip():
                promotional_context[field_key] = field_value.strip()

        if informacoes_extras and informacoes_extras.strip():
            promotional_context["informacoes_extras"] = informacoes_extras.strip()

        # Converter tipo e tom para enums
        campaign_type_enum = CampaignType(selected_type_key)
        tone_enum = CampaignTone(selected_tone)

        try:
            if is_edit and campaign:
                # Atualizar campanha existente
                updated = service.update_campaign(
                    campaign_id=campaign.id,
                    name=name.strip(),
                    description=description if description else None,
                    campaign_type=campaign_type_enum,
                    tone=tone_enum,
                    briefing=briefing.strip(),
                    template_text=template_text,
                    promotional_context=promotional_context,
                    start_date=start_date,
                    end_date=end_date
                )
                st.success(f"✅ Campanha '{updated.name}' atualizada com sucesso!")

                # Limpar estado de edição
                if 'editing_campaign_id' in st.session_state:
                    del st.session_state['editing_campaign_id']
                st.session_state['campaigns_view'] = 'list'
                st.rerun()

            else:
                # Criar nova campanha
                new_campaign = service.create_campaign(
                    name=name.strip(),
                    template_text=template_text,
                    start_date=start_date,
                    end_date=end_date,
                    campaign_type=campaign_type_enum,
                    tone=tone_enum,
                    briefing=briefing.strip(),
                    promotional_context=promotional_context,
                    description=description if description else None
                )
                st.success(f"✅ Campanha '{new_campaign.name}' criada com sucesso!")
                st.session_state['campaigns_view'] = 'list'
                st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao salvar campanha: {str(e)}")

    # Cancelar edição
    if is_edit and cancel:
        if 'editing_campaign_id' in st.session_state:
            del st.session_state['editing_campaign_id']
        st.session_state['campaigns_view'] = 'list'
        st.rerun()


def render_empty_state():
    """Renderiza estado vazio (sem campanhas)"""
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📢</div>
        <h3>Nenhuma campanha encontrada</h3>
        <p>Crie sua primeira campanha de remarketing para começar a exportar leads para o Disparador.</p>
    </div>
    """, unsafe_allow_html=True)


def render_campaigns_list(service: CampaignService, status_filter: str = None):
    """Renderiza lista de campanhas"""

    # Buscar campanhas
    status = None
    if status_filter and status_filter != "Todas":
        status_map = {
            "Rascunho": CampaignStatus.DRAFT,
            "Ativa": CampaignStatus.ACTIVE,
            "Pausada": CampaignStatus.PAUSED,
            "Encerrada": CampaignStatus.ENDED
        }
        status = status_map.get(status_filter)

    campaigns = service.list_campaigns(status=status)

    if not campaigns:
        render_empty_state()
        return

    # Mostrar contagem
    st.caption(f"📊 {len(campaigns)} campanha(s) encontrada(s)")

    # Renderizar cada campanha
    for campaign in campaigns:
        # Obter ícone do tipo da campanha
        campaign_type_key = "promotional"
        if hasattr(campaign, 'campaign_type') and campaign.campaign_type:
            if hasattr(campaign.campaign_type, 'value'):
                campaign_type_key = campaign.campaign_type.value
            else:
                campaign_type_key = str(campaign.campaign_type)
        type_icon = CAMPAIGN_TYPES.get(campaign_type_key, {}).get('icon', '📢')

        with st.expander(
            f"{STATUS_DISPLAY[campaign.status]['icon']} - {type_icon} **{campaign.name}** - {campaign.period_display}",
            expanded=False
        ):
            render_campaign_card(campaign, service)


def render_delete_confirmation(service: CampaignService, campaign_id: int):
    """Renderiza confirmação de exclusão"""
    campaign = service.get_campaign(campaign_id)

    if not campaign:
        st.error("Campanha não encontrada")
        return

    st.warning(f"⚠️ Tem certeza que deseja excluir a campanha **'{campaign.name}'**?")
    st.caption("Esta ação não pode ser desfeita. Todos os leads e exports serão removidos.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Sim, excluir", type="primary", use_container_width=True):
            try:
                service.delete_campaign(campaign_id)
                st.success("Campanha excluída com sucesso!")
                if 'deleting_campaign_id' in st.session_state:
                    del st.session_state['deleting_campaign_id']
                st.session_state['campaigns_view'] = 'list'
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {str(e)}")

    with col2:
        if st.button("❌ Cancelar", use_container_width=True):
            if 'deleting_campaign_id' in st.session_state:
                del st.session_state['deleting_campaign_id']
            st.session_state['campaigns_view'] = 'list'
            st.rerun()


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def show_campaigns_page(session: dict, tenant_id: int = None):
    """
    Página principal de campanhas

    Args:
        session: Dados da sessão do usuário
        tenant_id: ID do tenant (opcional, usa da sessão se não fornecido)
    """
    # Aplicar CSS
    st.markdown(CAMPAIGNS_CSS, unsafe_allow_html=True)

    # Determinar tenant_id
    if tenant_id is None:
        tenant_id = session.get('tenant_id', 0)

    # Header
    st.title("📢 Campanhas de Disparo")
    st.caption("Gerencie campanhas de remarketing para exportação ao Disparador")

    # Inicializar service
    service = get_campaign_service(tenant_id)

    # Inicializar estado da view
    if 'campaigns_view' not in st.session_state:
        st.session_state['campaigns_view'] = 'list'

    # === TOOLBAR ===
    st.markdown("---")

    toolbar_cols = st.columns([1, 1, 2])

    with toolbar_cols[0]:
        if st.button("➕ Nova Campanha", type="primary", use_container_width=True):
            st.session_state['campaigns_view'] = 'create'
            if 'editing_campaign_id' in st.session_state:
                del st.session_state['editing_campaign_id']
            st.rerun()

    with toolbar_cols[1]:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    with toolbar_cols[2]:
        status_filter = st.selectbox(
            "Filtrar por status",
            options=["Todas", "Rascunho", "Ativa", "Pausada", "Encerrada"],
            index=0,
            label_visibility="collapsed"
        )

    st.markdown("---")

    # === VIEWS ===
    current_view = st.session_state.get('campaigns_view', 'list')

    # View: Lista de campanhas
    if current_view == 'list':
        render_campaigns_list(service, status_filter)

    # View: Criar nova campanha
    elif current_view == 'create':
        # Botão voltar
        if st.button("← Voltar para lista"):
            st.session_state['campaigns_view'] = 'list'
            st.rerun()

        render_campaign_form(service, is_edit=False)

    # View: Editar campanha
    elif current_view == 'edit':
        # Botão voltar
        if st.button("← Voltar para lista"):
            if 'editing_campaign_id' in st.session_state:
                del st.session_state['editing_campaign_id']
            st.session_state['campaigns_view'] = 'list'
            st.rerun()

        campaign_id = st.session_state.get('editing_campaign_id')
        if campaign_id:
            campaign = service.get_campaign(campaign_id)
            if campaign:
                render_campaign_form(service, campaign=campaign, is_edit=True)

                # Opção de excluir (apenas se draft ou paused)
                if campaign.status in (CampaignStatus.DRAFT, CampaignStatus.PAUSED):
                    st.markdown("---")
                    st.markdown("#### ⚠️ Zona de Perigo")

                    if st.button("🗑️ Excluir Campanha", type="secondary"):
                        st.session_state['deleting_campaign_id'] = campaign_id
                        st.session_state['campaigns_view'] = 'delete'
                        st.rerun()
            else:
                st.error("Campanha não encontrada")
                st.session_state['campaigns_view'] = 'list'
        else:
            st.error("Nenhuma campanha selecionada para edição")
            st.session_state['campaigns_view'] = 'list'

    # View: Confirmar exclusão
    elif current_view == 'delete':
        campaign_id = st.session_state.get('deleting_campaign_id')
        if campaign_id:
            render_delete_confirmation(service, campaign_id)
        else:
            st.session_state['campaigns_view'] = 'list'
            st.rerun()

    # View: Gerenciar Leads da Campanha
    elif current_view == 'leads':
        campaign_id = st.session_state.get('managing_campaign_id')
        if campaign_id:
            render_leads_management(service, campaign_id)
        else:
            st.session_state['campaigns_view'] = 'list'
            st.rerun()


# ============================================================================
# GERENCIAMENTO DE LEADS
# ============================================================================

def render_leads_management(service: CampaignService, campaign_id: int):
    """Interface para gerenciar leads de uma campanha"""
    campaign = service.get_campaign(campaign_id)

    if not campaign:
        st.error("Campanha não encontrada")
        st.session_state['campaigns_view'] = 'list'
        return

    # Header
    col_back, col_title = st.columns([1, 5])

    with col_back:
        if st.button("← Voltar"):
            if 'managing_campaign_id' in st.session_state:
                del st.session_state['managing_campaign_id']
            st.session_state['campaigns_view'] = 'list'
            st.rerun()

    with col_title:
        type_info = CAMPAIGN_TYPES.get(
            campaign.campaign_type.value if hasattr(campaign.campaign_type, 'value') else str(campaign.campaign_type),
            {"label": "Campanha", "icon": "📢"}
        )
        st.markdown(f"## {type_info['icon']} {campaign.name}")
        st.caption(f"{campaign.description or ''} | Período: {campaign.period_display}")

    # Estatísticas
    stats = service.get_campaign_stats(campaign_id)

    st.markdown("---")

    # Métricas
    metric_cols = st.columns(6)
    with metric_cols[0]:
        st.metric("Total", stats['total'])
    with metric_cols[1]:
        st.metric("Pendentes", stats['pending'])
    with metric_cols[2]:
        st.metric("Processados", stats['processed'])
    with metric_cols[3]:
        st.metric("Exportados", stats['exported'])
    with metric_cols[4]:
        st.metric("Erros", stats['errors'])
    with metric_cols[5]:
        st.metric("Custo IA", f"R$ {stats['total_cost_brl']:.2f}")

    st.markdown("---")

    # Tabs
    tab_add, tab_campaign, tab_process, tab_export, tab_history = st.tabs([
        "➕ Adicionar Leads",
        "📋 Leads na Campanha",
        "🤖 Processar com IA",
        "📥 Exportar CSV",
        "📊 Histórico"
    ])

    with tab_add:
        render_add_leads_tab(service, campaign_id, campaign)

    with tab_campaign:
        render_campaign_leads_tab(service, campaign_id, stats)

    with tab_process:
        render_process_leads_tab(service, campaign_id, campaign, stats)

    with tab_export:
        render_export_tab(service, campaign_id, campaign, stats)

    with tab_history:
        render_export_history_tab(service, campaign_id, stats)


def render_add_leads_tab(service: CampaignService, campaign_id: int, campaign):
    """Tab para adicionar leads - Interface redesenhada para melhor UX"""

    # Constante de paginação
    LEADS_PER_PAGE = 50

    # Inicializar seleção
    if 'selected_leads' not in st.session_state:
        st.session_state['selected_leads'] = set()

    selected_count = len(st.session_state['selected_leads'])

    # =========================================================================
    # BARRA FIXA DE AÇÃO (sempre visível no topo)
    # =========================================================================
    if selected_count > 0:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #10B981 0%, #059669 100%); padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <span style="color: white; font-weight: 600; font-size: 1rem;">
                ✓ {selected_count} lead(s) selecionado(s)
            </span>
        </div>
        """, unsafe_allow_html=True)

        btn_cols = st.columns([2, 1])
        with btn_cols[0]:
            if st.button(f"➕ Adicionar {selected_count} lead(s) à campanha", type="primary", use_container_width=True):
                try:
                    added = service.add_leads_to_campaign(campaign_id, list(st.session_state['selected_leads']))
                    if added > 0:
                        st.success(f"✅ {added} lead(s) adicionados com sucesso!")
                        st.session_state['selected_leads'] = set()
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
        with btn_cols[1]:
            if st.button("✕ Limpar seleção", use_container_width=True):
                st.session_state['selected_leads'] = set()
                st.rerun()

        st.markdown("---")

    # =========================================================================
    # FILTROS (expansível)
    # =========================================================================
    with st.expander("🔍 Filtros de busca", expanded=True):
        filter_cols = st.columns([3, 2, 2, 2])

        with filter_cols[0]:
            search_term = st.text_input(
                "Buscar por nome ou telefone",
                placeholder="Digite para filtrar...",
                key="leads_search",
                label_visibility="collapsed"
            )

        with filter_cols[1]:
            min_score = st.select_slider(
                "Score mínimo",
                options=[0, 30, 50, 70, 80, 90],
                value=50,
                format_func=lambda x: f"{x}%",
                help="Probabilidade de conversão"
            )

        with filter_cols[2]:
            only_remarketing = st.checkbox(
                "🔄 Remarketing",
                False,
                help="Apenas candidatos a recontato"
            )

        with filter_cols[3]:
            only_with_analysis = st.checkbox(
                "🤖 Com análise IA",
                True,
                help="Apenas leads já analisados"
            )

    # =========================================================================
    # BUSCA DE LEADS
    # =========================================================================
    page_key = f"add_leads_page_{campaign_id}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current_page = st.session_state[page_key]
    offset = (current_page - 1) * LEADS_PER_PAGE

    leads, total_count = service.get_eligible_leads(
        campaign_id=campaign_id,
        min_score=min_score,
        only_with_analysis=only_with_analysis,
        only_remarketing=only_remarketing,
        search_term=search_term if search_term else None,
        limit=LEADS_PER_PAGE,
        offset=offset
    )

    total_pages = max(1, (total_count + LEADS_PER_PAGE - 1) // LEADS_PER_PAGE)

    if current_page > total_pages:
        st.session_state[page_key] = total_pages
        current_page = total_pages

    # =========================================================================
    # TOOLBAR: PAGINAÇÃO + SELEÇÃO RÁPIDA
    # =========================================================================
    start_record = offset + 1 if total_count > 0 else 0
    end_record = min(offset + LEADS_PER_PAGE, total_count)

    toolbar_cols = st.columns([2, 1, 1, 1, 2])

    with toolbar_cols[0]:
        st.markdown(f"**{total_count}** leads encontrados")
        st.caption(f"Exibindo {start_record}-{end_record}")

    with toolbar_cols[1]:
        if st.button("◀️", disabled=(current_page == 1), key=f"prev_{campaign_id}", help="Página anterior"):
            st.session_state[page_key] = current_page - 1
            st.rerun()

    with toolbar_cols[2]:
        st.markdown(f"<div style='text-align: center; padding-top: 5px;'><b>{current_page}</b> / {total_pages}</div>", unsafe_allow_html=True)

    with toolbar_cols[3]:
        if st.button("▶️", disabled=(current_page >= total_pages), key=f"next_{campaign_id}", help="Próxima página"):
            st.session_state[page_key] = current_page + 1
            st.rerun()

    with toolbar_cols[4]:
        if st.button("☑️ Selecionar página", use_container_width=True, help="Seleciona todos os leads desta página"):
            st.session_state['selected_leads'].update({l['conversation_id'] for l in leads})
            st.rerun()

    st.markdown("---")

    # =========================================================================
    # LISTA DE LEADS
    # =========================================================================
    if not leads:
        st.info("🔍 Nenhum lead encontrado com os filtros aplicados. Tente ajustar os critérios.")
        return

    # Cabeçalho da tabela
    header_cols = st.columns([0.3, 2.5, 2.5, 0.8, 0.6])
    with header_cols[0]:
        st.caption("")
    with header_cols[1]:
        st.caption("**LEAD**")
    with header_cols[2]:
        st.caption("**INTERESSE / ANÁLISE**")
    with header_cols[3]:
        st.caption("**SCORE**")
    with header_cols[4]:
        st.caption("**INFO**")

    # Lista de leads
    for lead in leads:
        conv_id = lead['conversation_id']
        is_selected = conv_id in st.session_state['selected_leads']
        score = lead['ai_probability_score']

        # Cor de fundo baseada na seleção
        row_style = "background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10B981;" if is_selected else ""

        cols = st.columns([0.3, 2.5, 2.5, 0.8, 0.6])

        with cols[0]:
            if st.checkbox("", value=is_selected, key=f"sel_{conv_id}", label_visibility="collapsed"):
                st.session_state['selected_leads'].add(conv_id)
            else:
                st.session_state['selected_leads'].discard(conv_id)

        with cols[1]:
            st.markdown(f"**{lead['nome_display']}**")
            st.caption(f"📞 {lead['contact_phone']}")

        with cols[2]:
            if lead.get('interesse'):
                st.caption(f"🎯 {lead['interesse'][:50]}...")
            elif lead.get('analise_ia'):
                st.caption(f"💬 {lead['analise_ia'][:50]}...")
            else:
                st.caption("—")

        with cols[3]:
            # Badge colorido para score
            if score >= 80:
                st.markdown(f"<span style='background: #10B981; color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold;'>{score:.0f}%</span>", unsafe_allow_html=True)
            elif score >= 50:
                st.markdown(f"<span style='background: #F59E0B; color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold;'>{score:.0f}%</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='background: #EF4444; color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold;'>{score:.0f}%</span>", unsafe_allow_html=True)

        with cols[4]:
            objecoes = lead.get('objecoes', [])
            if objecoes or lead.get('analise_ia'):
                with st.popover("📋"):
                    if objecoes:
                        st.markdown("**⚠️ Objeções:**")
                        for obj in objecoes:
                            st.markdown(f"• {obj}")
                    if lead.get('analise_ia'):
                        if objecoes:
                            st.markdown("---")
                        st.markdown("**💬 Análise IA:**")
                        st.caption(lead['analise_ia'][:400] + "..." if len(lead.get('analise_ia', '')) > 400 else lead['analise_ia'])
                    if lead.get('precisa_remarketing'):
                        st.markdown("---")
                        st.success("🔄 Recomendado para remarketing")
            else:
                st.caption("—")


def render_campaign_leads_tab(service: CampaignService, campaign_id: int, stats: dict):
    """Tab dos leads na campanha com gerenciamento de ciclo de vida"""
    st.markdown("### Leads na Campanha")

    if stats['total'] == 0:
        st.info("Nenhum lead na campanha. Adicione leads na aba anterior.")
        return

    # Inicializar seleção para ações em lote
    if 'selected_campaign_leads' not in st.session_state:
        st.session_state['selected_campaign_leads'] = set()

    selected_count = len(st.session_state['selected_campaign_leads'])

    # =========================================================================
    # BARRA DE AÇÕES EM LOTE (quando há seleção)
    # =========================================================================
    if selected_count > 0:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #3B82F6 0%, #2563EB 100%); padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <span style="color: white; font-weight: 600;">
                ✓ {selected_count} lead(s) selecionado(s)
            </span>
        </div>
        """, unsafe_allow_html=True)

        action_cols = st.columns([1, 1, 1, 1])

        with action_cols[0]:
            if st.button("↩️ Voltar p/ Processado", key="batch_to_processed", use_container_width=True,
                        help="Permite re-exportar estes leads"):
                reset_count = service.reset_leads_batch(
                    lead_ids=list(st.session_state['selected_campaign_leads']),
                    campaign_id=campaign_id,
                    new_status=LeadStatus.PROCESSED,
                    clear_variables=False,
                    reason="Reset manual em lote para reexportação"
                )
                st.success(f"✅ {reset_count} leads voltaram para Processado!")
                st.session_state['selected_campaign_leads'] = set()
                st.rerun()

        with action_cols[1]:
            if st.button("🔄 Regenerar Variáveis", key="batch_regenerate", use_container_width=True,
                        help="Volta para Pendente e regenera variáveis com IA"):
                regen_count = service.mark_leads_for_regeneration(
                    lead_ids=list(st.session_state['selected_campaign_leads']),
                    campaign_id=campaign_id,
                    keep_history=True
                )
                st.success(f"✅ {regen_count} leads marcados para regeneração!")
                st.session_state['selected_campaign_leads'] = set()
                st.rerun()

        with action_cols[2]:
            if st.button("🗑️ Remover da Campanha", key="batch_remove", use_container_width=True):
                for lid in st.session_state['selected_campaign_leads']:
                    service.remove_lead_from_campaign(campaign_id, lid)
                st.warning(f"Removidos {selected_count} leads da campanha")
                st.session_state['selected_campaign_leads'] = set()
                st.rerun()

        with action_cols[3]:
            if st.button("✕ Limpar seleção", key="batch_clear", use_container_width=True):
                st.session_state['selected_campaign_leads'] = set()
                st.rerun()

        st.markdown("---")

    # =========================================================================
    # FILTROS
    # =========================================================================
    filter_cols = st.columns([2, 1, 1])

    with filter_cols[0]:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "Pendentes", "Processados", "Exportados", "Erros"],
            label_visibility="collapsed"
        )

    with filter_cols[1]:
        show_exported = st.checkbox("Incluir já exportados", value=True, help="Mostra leads que já foram exportados")

    status_map = {
        "Pendentes": LeadStatus.PENDING,
        "Processados": LeadStatus.PROCESSED,
        "Exportados": LeadStatus.EXPORTED,
        "Erros": LeadStatus.ERROR
    }

    leads = service.get_campaign_leads(
        campaign_id,
        status=status_map.get(status_filter),
        limit=100
    )

    # Filtrar exportados se necessário
    if not show_exported and status_filter == "Todos":
        leads = [l for l in leads if l.status != LeadStatus.EXPORTED]

    with filter_cols[2]:
        if st.button("☑️ Selecionar página", use_container_width=True):
            for lead in leads:
                st.session_state['selected_campaign_leads'].add(lead.id)
            st.rerun()

    st.markdown(f"**{len(leads)}** leads")

    # =========================================================================
    # CABEÇALHO DA LISTA
    # =========================================================================
    header_cols = st.columns([0.3, 2, 1.5, 0.8, 0.8, 1.2])
    with header_cols[0]:
        st.caption("")
    with header_cols[1]:
        st.caption("**LEAD**")
    with header_cols[2]:
        st.caption("**VARIÁVEIS**")
    with header_cols[3]:
        st.caption("**STATUS**")
    with header_cols[4]:
        st.caption("**EXPORTS**")
    with header_cols[5]:
        st.caption("**AÇÕES**")

    # =========================================================================
    # LISTA DE LEADS
    # =========================================================================
    for lead in leads:
        is_selected = lead.id in st.session_state['selected_campaign_leads']

        # Ícones por status
        status_icons = {
            LeadStatus.PENDING: ("⏳", "#F59E0B"),
            LeadStatus.PROCESSING: ("🔄", "#3B82F6"),
            LeadStatus.PROCESSED: ("✅", "#10B981"),
            LeadStatus.EXPORTED: ("📤", "#8B5CF6"),
            LeadStatus.ERROR: ("❌", "#EF4444"),
            LeadStatus.SKIPPED: ("⏭️", "#9CA3AF"),
        }
        icon, color = status_icons.get(lead.status, ("❓", "#64748b"))

        cols = st.columns([0.3, 2, 1.5, 0.8, 0.8, 1.2])

        with cols[0]:
            if st.checkbox("", value=is_selected, key=f"sel_lead_{lead.id}", label_visibility="collapsed"):
                st.session_state['selected_campaign_leads'].add(lead.id)
            else:
                st.session_state['selected_campaign_leads'].discard(lead.id)

        with cols[1]:
            st.markdown(f"**{lead.contact_name or 'Sem nome'}**")
            st.caption(f"📞 {lead.contact_phone}")

        with cols[2]:
            if lead.var1:
                st.caption(f"{{{{1}}}}: {lead.var1[:25]}...")
            elif lead.status == LeadStatus.PENDING:
                st.caption("_Aguardando processamento_")
            elif lead.status == LeadStatus.ERROR:
                st.caption(f"⚠️ {(lead.error_message or 'Erro')[:30]}")
            else:
                st.caption("—")

        with cols[3]:
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{icon} {lead.status.value}</span>", unsafe_allow_html=True)

        with cols[4]:
            # Contador de exportações
            if lead.export_count > 0:
                st.markdown(f"<span style='background: #8B5CF6; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem;'>{lead.export_count}x</span>", unsafe_allow_html=True)
            else:
                st.caption("—")

        with cols[5]:
            # Botões de ação individuais
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                # Ações baseadas no status
                if lead.status == LeadStatus.EXPORTED:
                    if st.button("↩️", key=f"reset_{lead.id}", help="Voltar para Processado (permite re-exportar)"):
                        service.reset_lead_status(lead.id, LeadStatus.PROCESSED, reason="Reset manual")
                        st.rerun()
                elif lead.status in [LeadStatus.PROCESSED, LeadStatus.EXPORTED]:
                    if st.button("🔄", key=f"regen_{lead.id}", help="Regenerar variáveis com IA"):
                        service.reset_lead_status(lead.id, LeadStatus.PENDING, clear_variables=True, reason="Regeneração manual")
                        st.rerun()

            with btn_col2:
                if st.button("🗑️", key=f"rm_{lead.id}", help="Remover da campanha"):
                    service.remove_lead_from_campaign(campaign_id, lead.id)
                    st.rerun()

        # Expander com detalhes (opcional)
        if lead.var1 or lead.var2 or lead.var3 or lead.message_preview:
            with st.expander(f"📋 Ver detalhes de {lead.contact_name or 'Lead'}", expanded=False):
                detail_cols = st.columns(2)
                with detail_cols[0]:
                    st.markdown("**Variáveis geradas:**")
                    if lead.var1:
                        st.markdown(f"**{{{{1}}}}:** {lead.var1}")
                    if lead.var2:
                        st.markdown(f"**{{{{2}}}}:** {lead.var2}")
                    if lead.var3:
                        st.markdown(f"**{{{{3}}}}:** {lead.var3}")

                with detail_cols[1]:
                    st.markdown("**Info de exportação:**")
                    st.text(f"Exportado: {lead.export_count}x")
                    if lead.last_exported_at:
                        st.text(f"Última: {lead.last_exported_at.strftime('%d/%m/%Y %H:%M')}")

                    # Mostrar histórico de resets se existir
                    history = service.get_lead_history(lead.id)
                    if history:
                        st.markdown("**Histórico de alterações:**")
                        for h in history[:3]:  # Últimos 3
                            st.caption(f"• {h.get('from_status')} → {h.get('to_status')} ({h.get('reason', 'N/A')})")

                if lead.message_preview:
                    st.markdown("---")
                    st.markdown("**Preview da mensagem:**")
                    st.code(lead.message_preview, language=None)


def render_process_leads_tab(service: CampaignService, campaign_id: int, campaign, stats: dict):
    """
    Tab para processar leads com IA - Interface Profissional

    Características:
    - Progress bar em tempo real
    - Estimativa de tempo restante
    - Feedback visual por lead processado
    - Possibilidade de reprocessar erros
    - Estatísticas de custo
    """
    st.markdown("### 🤖 Processar Leads com IA")

    # =========================================================================
    # ESTADO: NENHUM LEAD
    # =========================================================================
    if stats['total'] == 0:
        st.info("📋 Adicione leads à campanha primeiro na aba **➕ Adicionar Leads**.")
        return

    # =========================================================================
    # ESTADO: TODOS PROCESSADOS
    # =========================================================================
    if stats['pending'] == 0 and stats['errors'] == 0:
        st.success("✅ Todos os leads foram processados com sucesso!")
        st.markdown(f"""
        **Resumo:**
        - ✅ Processados: **{stats['processed']}**
        - 📤 Exportados: **{stats['exported']}**
        - 💰 Custo total: **R$ {stats['total_cost_brl']:.2f}**
        """)
        st.info("👉 Agora você pode exportar os leads na aba **📥 Exportar CSV**")
        return

    # =========================================================================
    # CARDS DE STATUS
    # =========================================================================
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 2rem; font-weight: bold; color: #F59E0B;">⏳ {stats['pending']}</div>
            <div style="color: #94a3b8; font-size: 0.875rem;">Pendentes</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 2rem; font-weight: bold; color: #10B981;">✅ {stats['processed']}</div>
            <div style="color: #94a3b8; font-size: 0.875rem;">Processados</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 2rem; font-weight: bold; color: #EF4444;">❌ {stats['errors']}</div>
            <div style="color: #94a3b8; font-size: 0.875rem;">Erros</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================================
    # ESTIMATIVAS
    # =========================================================================
    pending_count = stats['pending']
    error_count = stats['errors']

    # Custo estimado (média de ~900 tokens por lead = ~R$ 0.003)
    cost_per_lead = 0.003
    estimated_cost = pending_count * cost_per_lead

    # Tempo estimado (~2.5 segundos por lead incluindo rate limit)
    time_per_lead = 2.5
    estimated_time_seconds = pending_count * time_per_lead
    estimated_time_min = estimated_time_seconds / 60

    st.markdown(f"""
    **📊 Estimativas para {pending_count} leads pendentes:**
    - ⏱️ Tempo estimado: **~{estimated_time_min:.1f} minutos** ({time_per_lead}s por lead)
    - 💰 Custo estimado: **~R$ {estimated_cost:.2f}** (~R$ 0,003 por lead)
    """)

    # =========================================================================
    # CONTEXTO DA CAMPANHA (EXPANSÍVEL)
    # =========================================================================
    with st.expander("📝 Ver contexto que a IA usará", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Tipo:** {campaign.campaign_type.icon} {campaign.campaign_type.label}")
            st.markdown(f"**Tom:** {campaign.tone.icon} {campaign.tone.label}")
        with col2:
            if campaign.briefing:
                st.markdown("**Briefing:**")
                st.caption(campaign.briefing[:300] + "..." if len(campaign.briefing or "") > 300 else campaign.briefing)

        if campaign.promotional_context:
            st.markdown("**Detalhes:**")
            for k, v in campaign.promotional_context.items():
                st.caption(f"• {k}: {v}")

    st.markdown("---")

    # =========================================================================
    # CONTROLES DE PROCESSAMENTO
    # =========================================================================
    st.markdown("### ▶️ Iniciar Processamento")

    # Seleção de quantidade
    max_batch = min(pending_count, 50)  # Máximo 50 por vez
    default_batch = min(pending_count, 10)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Se só tem 1 lead, não precisa de slider
        if max_batch <= 1:
            batch_size = max_batch
            st.info(f"📝 Será processado {batch_size} lead")
        else:
            batch_size = st.slider(
                "Quantidade de leads a processar",
                min_value=1,
                max_value=max_batch,
                value=default_batch,
                help="Recomendamos processar em lotes de 10-20 para melhor controle"
            )

    with col2:
        batch_cost = batch_size * cost_per_lead
        batch_time_min = batch_size * time_per_lead / 60
        st.markdown(f"""
        <div style="padding-top: 1.5rem;">
            ⏱️ ~{batch_time_min:.1f} min<br>
            💰 ~R$ {batch_cost:.2f}
        </div>
        """, unsafe_allow_html=True)

    # Botão principal
    if st.button(f"🚀 Processar {batch_size} lead(s)", type="primary", use_container_width=True):
        process_leads_with_progress(service, campaign_id, campaign, batch_size)

    # =========================================================================
    # REPROCESSAR ERROS (SE HOUVER)
    # =========================================================================
    if error_count > 0:
        st.markdown("---")
        st.markdown("### 🔄 Reprocessar Leads com Erro")
        st.warning(f"⚠️ {error_count} lead(s) falharam no processamento anterior.")

        if st.button(f"🔄 Reprocessar {error_count} lead(s) com erro", use_container_width=True):
            # Resetar status dos erros para pending
            reset_count = service.reset_error_leads(campaign_id)
            if reset_count > 0:
                st.success(f"✅ {reset_count} leads resetados para reprocessamento!")
                st.rerun()
            else:
                st.info("Nenhum lead para resetar.")


def process_leads_with_progress(service: CampaignService, campaign_id: int, campaign, batch_size: int):
    """
    Processa leads com IA mostrando progresso em tempo real.

    Características:
    - Progress bar visual
    - Status por lead processado
    - Estimativa de tempo restante
    - Tratamento de erros
    - Resumo final com custos
    """
    from multi_tenant.campaigns import CampaignVariableGenerator
    import os
    import time

    # =========================================================================
    # VALIDAR API KEY
    # =========================================================================
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        st.error("❌ **OPENAI_API_KEY não configurada!**")
        st.info("Configure a variável de ambiente OPENAI_API_KEY para usar o processamento com IA.")
        return

    # =========================================================================
    # BUSCAR LEADS PENDENTES
    # =========================================================================
    pending_leads = service.get_pending_leads(campaign_id, limit=batch_size)
    if not pending_leads:
        st.warning("⚠️ Nenhum lead pendente para processar.")
        return

    total_leads = len(pending_leads)

    # =========================================================================
    # INICIALIZAR GERADOR
    # =========================================================================
    try:
        engine = get_database_engine()
        generator = CampaignVariableGenerator(
            openai_api_key=api_key,
            engine=engine,
            tenant_id=service.tenant_id,
            model="gpt-4o-mini",
            temperature=0.7
        )
    except Exception as e:
        st.error(f"❌ Erro ao inicializar gerador de IA: {str(e)}")
        return

    # =========================================================================
    # UI DE PROGRESSO
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🔄 Processando...")

    # Containers para atualização em tempo real
    progress_bar = st.progress(0)
    status_container = st.empty()
    current_lead_container = st.empty()
    results_container = st.container()

    # Estatísticas
    processed_count = 0
    error_count = 0
    total_cost = 0.0
    total_tokens = 0
    start_time = time.time()

    # Lista de resultados para exibição
    results_log = []

    # =========================================================================
    # PROCESSAMENTO
    # =========================================================================
    for i, lead in enumerate(pending_leads):
        lead_start_time = time.time()

        # Atualizar status
        elapsed = time.time() - start_time
        avg_time_per_lead = elapsed / (i + 1) if i > 0 else 2.5
        remaining_leads = total_leads - i - 1
        estimated_remaining = remaining_leads * avg_time_per_lead

        status_container.markdown(f"""
        **Progresso:** {i + 1}/{total_leads} leads ({((i + 1) / total_leads * 100):.0f}%)
        | ✅ {processed_count} processados | ❌ {error_count} erros
        | ⏱️ Restante: ~{estimated_remaining:.0f}s
        """)

        current_lead_container.info(f"🔄 Processando: **{lead.contact_name or 'Lead sem nome'}** ({lead.contact_phone})")

        # Atualizar progress bar
        progress_bar.progress((i + 1) / total_leads)

        try:
            # Gerar variáveis com IA
            result = generator.generate_for_lead(campaign, lead)

            if result.get('status') == LeadStatus.PROCESSED:
                # Sucesso!
                var1 = result.get('var1', '')
                var2 = result.get('var2', '')
                var3 = result.get('var3', '')
                metadata = result.get('metadata', {})

                # Gerar preview
                preview = campaign.template_text
                preview = preview.replace("{{1}}", var1)
                preview = preview.replace("{{2}}", var2)
                preview = preview.replace("{{3}}", var3)

                # Salvar no banco
                service.update_lead(
                    lead_id=lead.id,
                    var1=var1,
                    var2=var2,
                    var3=var3,
                    message_preview=preview,
                    status=LeadStatus.PROCESSED,
                    generation_metadata=metadata
                )

                # Atualizar estatísticas
                processed_count += 1
                lead_cost = metadata.get('cost_brl', 0.003)
                lead_tokens = metadata.get('tokens_total', 900)
                total_cost += lead_cost
                total_tokens += lead_tokens

                results_log.append({
                    'name': lead.contact_name or 'Lead',
                    'status': 'success',
                    'var1': var1,
                    'cost': lead_cost
                })

            else:
                # Erro na geração
                error_msg = result.get('error_message', 'Erro desconhecido')
                service.update_lead(
                    lead_id=lead.id,
                    status=LeadStatus.ERROR,
                    error_message=error_msg[:200]
                )
                error_count += 1
                results_log.append({
                    'name': lead.contact_name or 'Lead',
                    'status': 'error',
                    'error': error_msg[:50]
                })

        except Exception as e:
            # Erro inesperado
            service.update_lead(
                lead_id=lead.id,
                status=LeadStatus.ERROR,
                error_message=str(e)[:200]
            )
            error_count += 1
            results_log.append({
                'name': lead.contact_name or 'Lead',
                'status': 'error',
                'error': str(e)[:50]
            })

    # =========================================================================
    # FINALIZAÇÃO
    # =========================================================================
    total_time = time.time() - start_time

    # Limpar containers de progresso
    progress_bar.empty()
    status_container.empty()
    current_lead_container.empty()

    # Atualizar métricas da campanha
    service._update_campaign_cost(campaign_id, total_cost)

    # =========================================================================
    # RESUMO FINAL
    # =========================================================================
    st.markdown("---")
    st.markdown("### ✅ Processamento Concluído!")

    # Cards de resumo
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background: #10B981; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: bold; color: white;">✅ {processed_count}</div>
            <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Processados</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {'#EF4444' if error_count > 0 else '#64748b'}; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: bold; color: white;">❌ {error_count}</div>
            <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Erros</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: #3B82F6; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: bold; color: white;">R$ {total_cost:.2f}</div>
            <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Custo Total</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: #8B5CF6; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: bold; color: white;">{total_time:.1f}s</div>
            <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Tempo Total</div>
        </div>
        """, unsafe_allow_html=True)

    # Detalhes
    st.markdown(f"""
    **📊 Detalhes:**
    - Tokens utilizados: **{total_tokens:,}**
    - Média por lead: **R$ {total_cost/max(processed_count, 1):.3f}** | **{total_time/total_leads:.1f}s**
    """)

    # Log de resultados
    if results_log:
        with st.expander("📋 Ver detalhes por lead", expanded=False):
            for r in results_log:
                if r['status'] == 'success':
                    st.markdown(f"✅ **{r['name']}** → `{r['var1']}` (R$ {r['cost']:.3f})")
                else:
                    st.markdown(f"❌ **{r['name']}** → {r.get('error', 'Erro')}")

    # Botão para continuar
    st.markdown("---")
    if st.button("🔄 Atualizar página", type="primary", use_container_width=True):
        st.rerun()


def render_export_tab(service: CampaignService, campaign_id: int, campaign, stats: dict):
    """Tab para exportar CSV"""
    from multi_tenant.campaigns import CampaignCSVExporter
    from datetime import datetime

    st.markdown("### Exportar CSV")

    exportable = stats['processed'] + stats['exported']
    if exportable == 0:
        st.info("Nenhum lead processado. Processe primeiro na aba anterior.")
        return

    only_new = st.checkbox("Apenas não exportados", value=False, help="Desmarque para incluir leads já exportados anteriormente")
    leads = service.get_exportable_leads(campaign_id, only_not_exported=only_new)

    if not leads:
        st.info("Nenhum lead disponível.")
        return

    st.markdown(f"**{len(leads)}** leads para exportar")

    with st.expander("👁️ Preview"):
        for lead in leads[:3]:
            st.text(f"{lead.contact_phone} | {lead.var1} | {(lead.var2 or '')[:30]}...")

    if st.button(f"📥 Gerar CSV ({len(leads)} leads)", type="primary", use_container_width=True):
        try:
            lead_ids = [l.id for l in leads]

            # Criar exporter e gerar CSV passando os objetos CampaignLead diretamente
            exporter = CampaignCSVExporter()
            csv_content, export_stats = exporter.export(leads, campaign)

            filename = f"campanha_{campaign.slug}_{datetime.now():%Y%m%d_%H%M}.csv"

            # Registrar exportação no histórico
            service.register_export(
                campaign_id=campaign_id,
                file_name=filename,
                leads_count=export_stats['exported'],
                lead_ids=lead_ids,
                file_size_bytes=export_stats['file_size_bytes']
            )

            # Marcar leads como exportados
            service.mark_leads_as_exported(lead_ids, campaign_id)

            st.download_button("📥 Baixar CSV", csv_content, filename, "text/csv", use_container_width=True)
            st.success(f"✅ {export_stats['exported']} leads exportados!")

            if export_stats.get('skipped_no_phone', 0) > 0:
                st.warning(f"⚠️ {export_stats['skipped_no_phone']} leads ignorados (sem telefone)")

        except Exception as e:
            st.error(f"Erro: {str(e)}")


def render_export_history_tab(service: CampaignService, campaign_id: int, stats: dict):
    """
    Tab para visualizar histórico de exportações e resumo de leads exportados.

    Mostra:
    - Resumo estatístico dos leads exportados
    - Histórico de todas as exportações realizadas
    - Opção de resetar leads exportados para reprocessamento
    """
    st.markdown("### 📊 Histórico e Estatísticas")

    # =========================================================================
    # RESUMO DE LEADS EXPORTADOS
    # =========================================================================
    st.markdown("#### Resumo de Leads Exportados")

    summary = service.get_exported_leads_summary(campaign_id)

    if summary['total_exported'] == 0:
        st.info("Nenhum lead foi exportado ainda nesta campanha.")
    else:
        # Cards de métricas
        metric_cols = st.columns(4)

        with metric_cols[0]:
            st.markdown(f"""
            <div style="background: #8B5CF6; border-radius: 8px; padding: 1rem; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: white;">📤 {summary['total_exported']}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Total Exportados</div>
            </div>
            """, unsafe_allow_html=True)

        with metric_cols[1]:
            st.markdown(f"""
            <div style="background: #3B82F6; border-radius: 8px; padding: 1rem; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: white;">🔄 {summary.get('exported_multiple', 0)}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Re-exportados</div>
            </div>
            """, unsafe_allow_html=True)

        with metric_cols[2]:
            exported_once = summary.get('exported_once', 0)
            exported_multiple = summary.get('exported_multiple', 0)
            st.markdown(f"""
            <div style="background: #10B981; border-radius: 8px; padding: 1rem; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: white;">{exported_once}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">1x Exportados</div>
            </div>
            """, unsafe_allow_html=True)

        with metric_cols[3]:
            max_exports = summary.get('max_exports', 0)
            st.markdown(f"""
            <div style="background: #F59E0B; border-radius: 8px; padding: 1rem; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: white;">{max_exports}x</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Máx. Exports</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Info de datas de exportação
        if summary.get('first_export') or summary.get('last_export'):
            st.markdown("**Período de exportações:**")
            if summary.get('first_export'):
                first_date = summary['first_export']
                if hasattr(first_date, 'strftime'):
                    st.markdown(f"- **Primeira:** {first_date.strftime('%d/%m/%Y %H:%M')}")
            if summary.get('last_export'):
                last_date = summary['last_export']
                if hasattr(last_date, 'strftime'):
                    st.markdown(f"- **Última:** {last_date.strftime('%d/%m/%Y %H:%M')}")

    st.markdown("---")

    # =========================================================================
    # HISTÓRICO DE EXPORTAÇÕES
    # =========================================================================
    st.markdown("#### Histórico de Exportações")

    # Buscar histórico de exportações
    exports = service.get_export_history(campaign_id, limit=20)

    if not exports:
        st.info("Nenhuma exportação registrada ainda.")
    else:
        st.markdown(f"**{len(exports)}** exportações realizadas")

        for export in exports:
            export_date = export.get('exported_at')
            if export_date:
                if isinstance(export_date, str):
                    date_str = export_date
                else:
                    date_str = export_date.strftime('%d/%m/%Y %H:%M')
            else:
                date_str = "Data não registrada"

            leads_count = export.get('leads_count', 0)
            file_name = export.get('file_name', 'arquivo.csv')
            file_size = export.get('file_size_bytes', 0)

            # Formatar tamanho do arquivo
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} bytes"

            with st.expander(f"📥 {date_str} - {leads_count} leads - {file_name}", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Arquivo:** `{file_name}`")
                    st.markdown(f"**Leads exportados:** {leads_count}")
                    st.markdown(f"**Tamanho:** {size_str}")

                with col2:
                    st.markdown(f"**Data/Hora:** {date_str}")
                    if export.get('exported_by'):
                        st.markdown(f"**Exportado por:** {export['exported_by']}")

    st.markdown("---")

    # =========================================================================
    # AÇÕES EM MASSA PARA LEADS EXPORTADOS
    # =========================================================================
    st.markdown("#### Ações em Massa")

    if stats['exported'] > 0:
        st.warning(f"⚠️ Existem **{stats['exported']}** leads com status EXPORTED nesta campanha.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Voltar todos para Processado:**")
            st.caption("Permite re-exportar estes leads mantendo as variáveis geradas.")
            if st.button("↩️ Resetar TODOS para Processado", key="reset_all_to_processed"):
                # Buscar todos os leads exportados
                exported_leads = service.get_campaign_leads(campaign_id, status=LeadStatus.EXPORTED, limit=1000)
                lead_ids = [l.id for l in exported_leads]

                reset_count = service.reset_leads_batch(
                    lead_ids=lead_ids,
                    campaign_id=campaign_id,
                    new_status=LeadStatus.PROCESSED,
                    clear_variables=False,
                    reason="Reset em massa para reexportação"
                )
                st.success(f"✅ {reset_count} leads voltaram para Processado!")
                st.rerun()

        with col2:
            st.markdown("**Regenerar variáveis de todos:**")
            st.caption("Volta para Pendente e regenera variáveis com IA. Útil se o briefing mudou.")
            if st.button("🔄 Regenerar TODOS exportados", key="regen_all_exported"):
                exported_leads = service.get_campaign_leads(campaign_id, status=LeadStatus.EXPORTED, limit=1000)
                lead_ids = [l.id for l in exported_leads]

                regen_count = service.mark_leads_for_regeneration(
                    lead_ids=lead_ids,
                    campaign_id=campaign_id,
                    keep_history=True
                )
                st.success(f"✅ {regen_count} leads marcados para regeneração!")
                st.rerun()
    else:
        st.success("✅ Não há leads com status EXPORTED para ações em massa.")


# ============================================================================
# ENTRY POINT PARA TESTES
# ============================================================================

if __name__ == "__main__":
    # Para teste direto da página
    st.set_page_config(
        page_title="Campanhas - GeniAI Analytics",
        page_icon="📢",
        layout="wide"
    )

    # Sessão mock para teste
    mock_session = {
        'user_id': 1,
        'tenant_id': 1,
        'role': 'admin',
        'email': 'test@test.com'
    }

    show_campaigns_page(mock_session, tenant_id=1)