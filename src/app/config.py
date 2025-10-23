"""
Configurações do Dashboard - AllpFit Analytics
Tema Dark com cores azul/laranja
"""

import streamlit as st
import locale

# Configurar locale para português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        pass  # Se não conseguir, usar padrão

# ============================================================================
# TEMA E CORES
# ============================================================================

THEME = {
    # Cores principais
    'primary': '#1E90FF',      # Azul
    'secondary': '#FF8C00',    # Laranja
    'success': '#00C853',      # Verde
    'warning': '#FFB300',      # Amarelo
    'danger': '#E53935',       # Vermelho
    'info': '#00B8D4',         # Ciano

    # Backgrounds
    'bg_dark': '#0E1117',      # Fundo escuro principal
    'bg_card': '#1A1F2E',      # Fundo dos cards
    'bg_secondary': '#262B3D', # Fundo secundário

    # Texto
    'text_primary': '#FFFFFF',
    'text_secondary': '#B0B8C4',
    'text_muted': '#6C757D',
}

# ============================================================================
# CONFIGURAÇÃO STREAMLIT
# ============================================================================

def apply_custom_css():
    """Aplica CSS customizado para tema dark"""
    st.markdown("""
        <style>
        /* Background principal */
        .stApp {
            background-color: #0E1117;
        }

        /* Cards/Metrics - Compacto */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            color: #FFFFFF;
            font-weight: 700;
        }

        [data-testid="stMetricLabel"] {
            color: #B0B8C4;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.8rem;
        }

        /* Títulos - Compacto */
        h1 {
            color: #FFFFFF;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
            font-size: 1.8rem;
        }

        h2, h3 {
            color: #FFFFFF;
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 1.2rem;
        }

        /* Divisor - Compacto */
        hr {
            margin: 0.8rem 0;
            border-color: #262B3D;
        }

        /* Reduzir espaçamento vertical geral */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* Reduzir espaço entre elementos */
        .element-container {
            margin-bottom: 0.3rem;
        }

        /* Tabelas */
        [data-testid="stTable"] {
            background-color: #1A1F2E;
        }

        /* Gráficos */
        .js-plotly-plot {
            background-color: transparent !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0E1117;
        }

        /* Botões */
        .stButton button {
            background-color: #1E90FF;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }

        .stButton button:hover {
            background-color: #1873CC;
        }

        /* Filtros */
        .stSelectbox, .stMultiSelect {
            color: white;
        }

        /* Cards customizados */
        .metric-card {
            background-color: #1A1F2E;
            border-radius: 10px;
            padding: 1.5rem;
            border-left: 4px solid #1E90FF;
            margin-bottom: 1rem;
        }

        .metric-card-orange {
            border-left-color: #FF8C00;
        }

        .metric-card-green {
            border-left-color: #00C853;
        }

        /* Seção Resultado Diário */
        .daily-result {
            background-color: #1A1F2E;
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
            border-top: 3px solid #FF8C00;
        }

        /* Estilo da tabela */
        .dataframe {
            background-color: #1A1F2E !important;
            color: white !important;
        }

        .dataframe th {
            background-color: #262B3D !important;
            color: #B0B8C4 !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            font-size: 0.85rem !important;
        }

        .dataframe td {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)


def configure_page():
    """Configura a página do Streamlit"""
    st.set_page_config(
        page_title="Analytics GenIAI - AllpFit",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    apply_custom_css()


# ============================================================================
# FORMATAÇÃO
# ============================================================================

def format_number(number, decimals=0):
    """Formata número com separador de milhares"""
    if number is None:
        return "0"
    return f"{number:,.{decimals}f}".replace(",", ".")


def format_percentage(value, total, decimals=1):
    """Calcula e formata percentual"""
    if total == 0:
        return "0%"
    percentage = (value / total) * 100
    return f"{percentage:.{decimals}f}%"


def format_phone(phone):
    """Formata número de telefone brasileiro"""
    if not phone:
        return "-"

    # Remove caracteres não numéricos
    digits = ''.join(filter(str.isdigit, str(phone)))

    # Formato: +55 (83) 98694-1334
    if len(digits) >= 13:
        return f"+{digits[0:2]} ({digits[2:4]}) {digits[4:9]}-{digits[9:]}"
    elif len(digits) >= 11:
        return f"({digits[0:2]}) {digits[2:7]}-{digits[7:]}"

    return phone


def format_datetime(dt, format='%d/%m/%Y %H:%M'):
    """Formata datetime (converte UTC para SP se necessário)"""
    if dt is None:
        return "-"

    from datetime import timedelta

    # Converter UTC para horário de São Paulo (UTC-3)
    dt_sp = dt - timedelta(hours=3)

    return dt_sp.strftime(format)


def format_date_pt(date):
    """Formata data em português (ex: 15/Jan)"""
    if date is None:
        return "-"

    import pandas as pd
    from datetime import datetime

    # Converter para datetime se for date
    if isinstance(date, pd.Timestamp):
        dt = date
    elif hasattr(date, 'strftime'):
        dt = date
    else:
        dt = datetime.strptime(str(date), '%Y-%m-%d')

    # Meses em português (abreviados)
    meses = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
        5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    dia = dt.day
    mes = meses[dt.month]

    return f"{dia}/{mes}"


def format_datetime_pt(dt):
    """Formata datetime completo em português (ex: 15 de Janeiro de 2025, 14:30)"""
    if dt is None:
        return "-"

    from datetime import timedelta

    # Converter UTC para horário de São Paulo (UTC-3)
    dt_sp = dt - timedelta(hours=3)

    # Meses em português (completos)
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    dia = dt_sp.day
    mes = meses[dt_sp.month]
    ano = dt_sp.year
    hora = dt_sp.strftime('%H:%M:%S')

    return f"{dia} de {mes} de {ano}, {hora}"


def format_conversation_readable(message_compiled_json, contact_name="Lead"):
    """
    Formata a conversa compilada (JSON) em formato legível de chat

    Args:
        message_compiled_json: String JSON ou objeto Python com as mensagens
        contact_name: Nome do contato (padrão: "Lead")

    Returns:
        String formatada como chat legível
    """
    import json
    from datetime import datetime, timedelta

    if not message_compiled_json:
        return "Conversa vazia"

    # Se for string JSON, converter para objeto Python
    if isinstance(message_compiled_json, str):
        try:
            messages = json.loads(message_compiled_json)
        except:
            return message_compiled_json
    else:
        messages = message_compiled_json

    if not messages or not isinstance(messages, list):
        return "Conversa vazia"

    formatted_lines = []

    for msg in messages:
        # Pular mensagens do sistema (message_type 2 ou 3)
        if msg.get('message_type') in [2, 3]:
            continue

        # Pular mensagens privadas
        if msg.get('private', False):
            continue

        text = msg.get('text', '')
        if text is None:
            text = ''
        text = text.strip()
        if not text:
            continue

        sender = msg.get('sender', 'Unknown')
        sender_name_from_msg = msg.get('sender_name', '')  # Nome do atendente se houver
        sent_at = msg.get('sent_at')

        # Determinar quem enviou
        if sender == 'Contact':
            sender_name = f"Lead ({contact_name})"
        elif sender == 'AgentBot':
            sender_name = "Bot AllpFit (IA)"
        elif sender == 'User':
            # Atendente humano - mostrar nome se disponível
            if sender_name_from_msg:
                sender_name = f"Atendente Humano ({sender_name_from_msg})"
            else:
                sender_name = "Atendente Humano"
        elif sender == 'Agent':
            sender_name = "Atendente"
        elif sender is None or sender == 'Bot':
            sender_name = "Bot AllpFit (IA)"
        else:
            sender_name = sender

        # Formatar data/hora
        if sent_at:
            try:
                # Parse ISO format
                dt = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                # Converter UTC para SP (UTC-3)
                dt_sp = dt - timedelta(hours=3)
                date_str = dt_sp.strftime('%d/%m/%Y %H:%M')
            except:
                date_str = sent_at
        else:
            date_str = "Data desconhecida"

        # Adicionar linha formatada
        formatted_lines.append(f"{sender_name}: {text}")
        formatted_lines.append(f"Enviado: {date_str}")
        formatted_lines.append("")  # Linha em branco entre mensagens

    return "\n".join(formatted_lines) if formatted_lines else "Conversa vazia"
