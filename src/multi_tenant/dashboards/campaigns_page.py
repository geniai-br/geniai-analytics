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