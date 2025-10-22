"""
Metrics Calculator - Cálculo de KPIs e Métricas
"""

import pandas as pd
import json
from datetime import datetime, timedelta


def calculate_total_contacts(df):
    """
    Total de contatos válidos (leads que engajaram)
    Contato válido = enviou pelo menos 1 mensagem
    """
    return len(df[df['contact_messages_count'] > 0])


def calculate_ai_conversations(df):
    """
    Total de conversas 100% bot (sem intervenção humana)
    """
    return len(df[df['has_human_intervention'] == False])


def calculate_human_conversations(df):
    """
    Total de conversas com intervenção humana
    """
    return len(df[df['has_human_intervention'] == True])


def detect_visit_scheduled(message_compiled):
    """
    Detecta se houve agendamento de visita na conversa

    Procura por:
    - Confirmação de agendamento
    - Data específica
    - Horário específico
    - Endereço da academia

    Args:
        message_compiled: JSON string com todas as mensagens

    Returns:
        bool: True se detectou agendamento
    """
    if not message_compiled or message_compiled == 'null':
        return False

    try:
        messages = json.loads(message_compiled)

        # Keywords de agendamento
        keywords_agendamento = [
            'visita agendada',
            'agendei sua visita',
            'agendamento confirmado',
            'te espero',
            'esperamos você',
            'confirmada sua visita',
            'anotei aqui',
            'pode vir',
            'comparecer',
        ]

        # Keywords de data
        keywords_data = [
            'hoje',
            'amanhã',
            'segunda',
            'terça',
            'quarta',
            'quinta',
            'sexta',
            'sábado',
            'domingo',
            '/',  # Para datas como 17/10
        ]

        # Keywords de hora
        keywords_hora = [
            'h',
            ':',
            'manhã',
            'tarde',
            'noite',
        ]

        # Converter para texto único
        all_text = ' '.join([
            msg.get('text', '').lower()
            for msg in messages
            if msg.get('sender') == 'AgentBot'  # Apenas mensagens do bot
        ])

        # Verificar se tem confirmação + data/hora
        has_confirmation = any(kw in all_text for kw in keywords_agendamento)
        has_date = any(kw in all_text for kw in keywords_data)
        has_time = any(kw in all_text for kw in keywords_hora)

        return has_confirmation and (has_date or has_time)

    except:
        return False


def calculate_visits_scheduled(df):
    """
    Total de visitas agendadas pelo bot (confirmadas)
    Busca diretamente do banco para garantir precisão
    """
    from .db_connector import get_engine
    from sqlalchemy import text

    try:
        engine = get_engine()

        # Query para contar visitas confirmadas pelo bot
        query = text("""
            WITH bot_confirmations AS (
                SELECT DISTINCT ca.conversation_id
                FROM conversas_analytics ca,
                     jsonb_array_elements(ca.message_compiled) as msg
                WHERE ca.contact_messages_count > 0
                  AND ca.contact_name <> 'Isaac'
                  AND (msg->>'sender' = 'AgentBot' OR msg->>'sender' IS NULL)
                  AND (
                      msg->>'text' ILIKE '%visita agendada%' OR
                      msg->>'text' ILIKE '%agendamento confirmado%' OR
                      msg->>'text' ILIKE '%já agendei%' OR
                      msg->>'text' ILIKE '%te espero%'
                  )
            )
            SELECT COUNT(*) as total
            FROM bot_confirmations
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    except Exception as e:
        # Fallback para método antigo se houver erro
        if 'message_compiled' not in df.columns:
            return 0
        df['has_visit'] = df['message_compiled'].apply(detect_visit_scheduled)
        return df['has_visit'].sum()


def calculate_daily_metrics(df):
    """
    Calcula métricas do dia atual com comparação ao dia anterior

    Returns:
        dict com métricas diárias e percentuais de variação
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Filtrar conversas de hoje e ontem
    df_today = df[df['conversation_date'] == today]
    df_yesterday = df[df['conversation_date'] == yesterday]

    # 1. NOVOS LEADS (conversas criadas hoje que engajaram)
    novos_leads_hoje = calculate_total_contacts(df_today)
    novos_leads_ontem = calculate_total_contacts(df_yesterday)
    perc_novos_leads = calculate_percentage_change(novos_leads_hoje, novos_leads_ontem)

    # 2. TOTAL DE CONVERSAS DIA (todas as conversas com atividade hoje - novas + antigas)
    # Precisamos filtrar por last_activity_at ao invés de conversation_date
    df_ativas_hoje = df[df['last_activity_at'].dt.date == today] if 'last_activity_at' in df.columns else df_today
    df_ativas_ontem = df[df['last_activity_at'].dt.date == yesterday] if 'last_activity_at' in df.columns else df_yesterday

    total_conversas_hoje = len(df_ativas_hoje)
    total_conversas_ontem = len(df_ativas_ontem)
    perc_total_conversas = calculate_percentage_change(total_conversas_hoje, total_conversas_ontem)

    # 3. CONVERSAS DIA (manter - mesmo que novos leads)
    conversas_dia_hoje = len(df_today)
    conversas_dia_ontem = len(df_yesterday)
    perc_conversas_dia = calculate_percentage_change(conversas_dia_hoje, conversas_dia_ontem)

    # 4. CONVERSAS REABERTAS (conversas antigas que tiveram atividade hoje)
    conversas_reabertas_hoje = total_conversas_hoje - conversas_dia_hoje
    conversas_reabertas_ontem = total_conversas_ontem - conversas_dia_ontem
    perc_reabertas = calculate_percentage_change(conversas_reabertas_hoje, conversas_reabertas_ontem)

    return {
        'novos_leads': novos_leads_hoje,
        'novos_leads_perc': perc_novos_leads,
        'total_conversas_dia': total_conversas_hoje,
        'total_conversas_dia_perc': perc_total_conversas,
        'conversas_dia': conversas_dia_hoje,
        'conversas_dia_perc': perc_conversas_dia,
        'conversas_reabertas': conversas_reabertas_hoje,
        'conversas_reabertas_perc': perc_reabertas,
        'visitas_dia': calculate_visits_scheduled(df_today),
        'vendas_dia': 0  # TODO: Integrar com CRM
    }


def calculate_percentage_change(current, previous):
    """
    Calcula variação percentual entre dois valores

    Returns:
        str formatado com sinal (ex: "+15.5%", "-10.2%", "0%")
    """
    if previous == 0:
        if current == 0:
            return "0%"
        else:
            return "+100%"  # Se não tinha nada ontem e tem hoje

    change = ((current - previous) / previous) * 100

    if change > 0:
        return f"+{change:.1f}%"
    elif change < 0:
        return f"{change:.1f}%"
    else:
        return "0%"


def calculate_leads_by_day(df, days=30):
    """
    Calcula média de leads por dia nos últimos N dias

    Returns:
        DataFrame com data e quantidade de leads
    """
    # Agrupar por data
    leads_per_day = df.groupby('conversation_date').agg({
        'conversation_id': 'count'
    }).reset_index()

    leads_per_day.columns = ['data', 'leads']

    # Ordenar por data
    leads_per_day = leads_per_day.sort_values('data')

    # Pegar últimos N dias
    if len(leads_per_day) > days:
        leads_per_day = leads_per_day.tail(days)

    return leads_per_day


def calculate_distribution_by_period(df):
    """
    Calcula distribuição de conversas por período do dia

    Returns:
        DataFrame com período e quantidade
    """
    if 'conversation_period' not in df.columns:
        return pd.DataFrame()

    distribution = df.groupby('conversation_period').size().reset_index()
    distribution.columns = ['periodo', 'quantidade']

    # Ordenar por ordem lógica dos períodos
    period_order = ['Manhã', 'Tarde', 'Noite', 'Madrugada']
    distribution['periodo'] = pd.Categorical(
        distribution['periodo'],
        categories=period_order,
        ordered=True
    )
    distribution = distribution.sort_values('periodo')

    return distribution


def get_leads_table_data(df, limit=50):
    """
    Prepara dados para tabela de leads

    Returns:
        DataFrame formatado para exibição
    """
    # Selecionar colunas relevantes
    columns = [
        'contact_name',
        'contact_phone',
        'conversation_created_at',
        'last_activity_at',
        'status_label_pt',
        't_messages',
        'contact_messages_count',
        'has_human_intervention'
    ]

    df_table = df[columns].copy()

    # Renomear colunas
    df_table.columns = [
        'Nome',
        'Celular',
        'Primeiro Contato',
        'Última Conversa',
        'Status',
        'Total Msgs',
        'Msgs Lead',
        'Intervenção Humana'
    ]

    # Ordenar por última conversa (mais recente primeiro)
    df_table = df_table.sort_values('Última Conversa', ascending=False)

    # Limitar registros
    if limit:
        df_table = df_table.head(limit)

    return df_table


def get_leads_not_converted(df, crm_phones=None):
    """
    Identifica leads não convertidos (não apareceram no CRM)

    Args:
        df: DataFrame com conversas
        crm_phones: Lista de telefones que estão no CRM (opcional)

    Returns:
        DataFrame com leads não convertidos
    """
    # Filtrar apenas contatos válidos (engajaram)
    leads_validos = df[df['contact_messages_count'] > 0].copy()

    if crm_phones is not None and len(crm_phones) > 0:
        # Filtrar leads que NÃO estão no CRM
        leads_not_converted = leads_validos[
            ~leads_validos['contact_phone'].isin(crm_phones)
        ]
    else:
        # Sem dados do CRM, retornar todos os leads válidos
        # (são oportunidades de follow-up)
        leads_not_converted = leads_validos

    return leads_not_converted


def calculate_conversion_rate(total_leads, total_sales):
    """
    Calcula taxa de conversão

    Returns:
        float: Taxa de conversão (0-100)
    """
    if total_leads == 0:
        return 0.0

    return (total_sales / total_leads) * 100


def get_leads_with_ai_analysis(engine, limit=50):
    """
    Busca leads não convertidos com análise de IA

    Args:
        engine: SQLAlchemy engine
        limit: Limite de registros

    Returns:
        DataFrame com leads analisados
    """
    from sqlalchemy import text

    query = text(f"""
        SELECT
            contact_name AS nome,
            contact_phone AS celular,
            condicao_fisica,
            objetivo,
            data_primeiro_contato,
            data_ultima_conversa,
            conversa_compilada,
            analise_ia,
            data_atualizacao_telefone,
            sugestao_disparo,
            probabilidade_conversao
        FROM vw_leads_nao_convertidos_com_ia
        WHERE probabilidade_conversao IS NOT NULL
        ORDER BY probabilidade_conversao DESC, data_ultima_conversa DESC
        LIMIT {limit}
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

        if not rows:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=[
            'Nome',
            'Celular',
            'Condição Física',
            'Objetivo',
            'Data Primeiro Contato',
            'Data Última Conversa',
            'Conversa Compilada',
            'Análise IA',
            'Data Atualização Tel',
            'Sugestão de Disparo',
            'Probabilidade'
        ])

        return df
