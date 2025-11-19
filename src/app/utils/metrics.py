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
    Total de visitas agendadas (detectadas pelo GPT-4)
    """
    from .db_connector import get_engine
    from sqlalchemy import text

    try:
        engine = get_engine()

        # Query para contar visitas agendadas detectadas pelo GPT-4
        query = text("""
            SELECT COUNT(*) as total
            FROM conversas_analytics_ai
            WHERE visita_agendada = TRUE
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    except Exception as e:
        print(f"Erro ao calcular visitas agendadas: {e}")
        return 0


def calculate_visits_scheduled_today():
    """
    Total de visitas agendadas HOJE (analisadas hoje pelo GPT-4)
    """
    from .db_connector import get_engine
    from sqlalchemy import text
    from datetime import datetime

    try:
        engine = get_engine()
        today = datetime.now().date()

        # Query para contar visitas agendadas que foram analisadas HOJE
        query = text(f"""
            SELECT COUNT(*) as total
            FROM conversas_analytics_ai
            WHERE visita_agendada = TRUE
              AND DATE(analisado_em) = '{today}'
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    except Exception as e:
        print(f"Erro ao calcular visitas do dia: {e}")
        return 0


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
        'visitas_dia': calculate_visits_scheduled_today(),  # CORRIGIDO: visitas agendadas HOJE
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


def build_filter_conditions(filters: dict) -> str:
    """
    Constrói condições WHERE para filtros

    Args:
        filters: Dicionário com os filtros ativos

    Returns:
        String com condições WHERE
    """
    conditions = []

    # Filtro de nome
    if filters.get('nome'):
        conditions.append(f"contact_name ILIKE '%{filters['nome']}%'")

    # Filtro de celular
    if filters.get('celular'):
        conditions.append(f"contact_phone ILIKE '%{filters['celular']}%'")

    # Filtro de condição física
    if filters.get('condicao_fisica') and len(filters['condicao_fisica']) > 0:
        condicoes = "', '".join(filters['condicao_fisica'])
        conditions.append(f"condicao_fisica IN ('{condicoes}')")

    # Filtro de objetivo
    if filters.get('objetivo') and len(filters['objetivo']) > 0:
        objetivos = "', '".join(filters['objetivo'])
        conditions.append(f"objetivo IN ('{objetivos}')")

    # Filtro de probabilidade
    if filters.get('probabilidade') and len(filters['probabilidade']) > 0:
        prob_values = []
        has_sem_analise = False

        for p in filters['probabilidade']:
            if p == 'Sem análise':
                has_sem_analise = True
            elif p in ['0', '1', '2', '3', '4', '5']:
                prob_values.append(p)

        if has_sem_analise and prob_values:
            # Incluir NULL e valores selecionados
            conditions.append(f"(probabilidade_conversao IN ({','.join(prob_values)}) OR probabilidade_conversao IS NULL)")
        elif has_sem_analise:
            # Apenas NULL
            conditions.append("probabilidade_conversao IS NULL")
        else:
            # Apenas valores selecionados
            conditions.append(f"probabilidade_conversao IN ({','.join(prob_values)})")

    # Filtro de status análise
    if filters.get('status_analise') == 'Com análise':
        conditions.append("probabilidade_conversao IS NOT NULL")
    elif filters.get('status_analise') == 'Sem análise':
        conditions.append("probabilidade_conversao IS NULL")

    # Filtro de data primeiro contato
    if filters.get('data_primeiro_inicio'):
        conditions.append(f"data_primeiro_contato >= '{filters['data_primeiro_inicio']}'")
    if filters.get('data_primeiro_fim'):
        conditions.append(f"data_primeiro_contato <= '{filters['data_primeiro_fim']} 23:59:59'")

    # Filtro de data última conversa
    if filters.get('data_ultima_inicio'):
        conditions.append(f"data_ultima_conversa >= '{filters['data_ultima_inicio']}'")
    if filters.get('data_ultima_fim'):
        conditions.append(f"data_ultima_conversa <= '{filters['data_ultima_fim']} 23:59:59'")

    return " AND ".join(conditions) if conditions else "1=1"


def get_total_leads_with_ai_analysis(engine, filters: dict = None):
    """
    Conta total de leads não convertidos (com e sem análise de IA)

    Args:
        engine: SQLAlchemy engine
        filters: Dicionário com filtros ativos

    Returns:
        int: Total de leads
    """
    from sqlalchemy import text

    where_clause = build_filter_conditions(filters) if filters else "1=1"

    query = text(f"""
        SELECT COUNT(*) as total
        FROM vw_leads_nao_convertidos_com_ia
        WHERE {where_clause}
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0
    except Exception as e:
        return 0


def get_leads_with_ai_analysis(engine, limit=50, offset=0, filters: dict = None):
    """
    Busca leads não convertidos (com e sem análise de IA)

    Args:
        engine: SQLAlchemy engine
        limit: Limite de registros por página
        offset: Número de registros a pular (para paginação)
        filters: Dicionário com filtros ativos

    Returns:
        DataFrame com leads (campos vazios para os sem análise)
    """
    from sqlalchemy import text

    where_clause = build_filter_conditions(filters) if filters else "1=1"

    # Se limit for None, retorna todos os registros (para download)
    limit_clause = f"LIMIT {limit} OFFSET {offset}" if limit is not None else ""

    query = text(f"""
        SELECT
            contact_name AS nome,
            nome_mapeado_bot,
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
        WHERE {where_clause}
        ORDER BY
            CASE
                WHEN probabilidade_conversao IS NOT NULL THEN probabilidade_conversao
                ELSE 0
            END DESC,
            data_ultima_conversa DESC
        {limit_clause}
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

        if not rows:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=[
            'Nome',
            'Nome Mapeado Bot',
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

def calculate_crm_conversions():
    """
    Busca conversões reais da tabela conversas_crm_match_real
    (Leads do bot que viraram clientes no EVO CRM)

    Returns:
        int: Número de conversões identificadas
    """
    from .db_connector import get_engine
    from sqlalchemy import text

    try:
        engine = get_engine()

        query = text("""
            SELECT COUNT(*) as total
            FROM conversas_crm_match_real
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    except Exception as e:
        # Se tabela não existir ainda, retornar 0
        return 0


def calculate_days_running():
    """
    Calcula quantos dias o bot está rodando
    (desde a primeira conversa criada)

    Returns:
        int: Número de dias
    """
    from .db_connector import get_engine
    from sqlalchemy import text

    try:
        engine = get_engine()

        query = text("""
            SELECT 
                CURRENT_DATE - MIN(conversation_created_at)::date AS dias_rodando
            FROM conversas_analytics
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    except Exception as e:
        return 0


def get_crm_conversions_detail(engine):
    """
    Busca detalhes das conversões do CRM

    Args:
        engine: SQLAlchemy engine

    Returns:
        DataFrame com conversões detalhadas
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            nome_bot AS "Nome (Bot)",
            nome_crm AS "Nome (CRM)",
            telefone AS "Telefone",
            COALESCE(origem, 'Agente IA') AS "Origem",
            conversa_criada_em AS "Data Conversa",
            cadastro_crm_em AS "Data Cadastro CRM",
            dias_para_conversao AS "Dias",
            total_mensagens AS "Msgs"
        FROM conversas_crm_match_real
        ORDER BY cadastro_crm_em DESC
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[
                'Nome (Bot)',
                'Nome (CRM)',
                'Telefone',
                'Origem',
                'Data Conversa',
                'Data Cadastro CRM',
                'Dias',
                'Msgs'
            ])

            return df

    except Exception as e:
        return pd.DataFrame()


# ===================================================================
# CATEGORIZAÇÃO DE CONVERSAS (Adicionado 2025-11-19)
# ===================================================================

def calculate_conversation_categories(df, min_threshold=5.0):
    """
    Categoriza conversas em tipos principais baseado em palavras-chave.

    Categorias principais (baseado em análise de 2.069 conversas):
    - PREÇO/PLANOS (65.4%)
    - AGENDAMENTO (18.2%)
    - INFORMAÇÕES GERAIS (6.3%)
    - OUTROS (10.1%)

    Args:
        df: DataFrame com conversas (deve ter coluna 'message_compiled')
        min_threshold: Percentual mínimo para categoria aparecer (padrão 5.0%)

    Returns:
        DataFrame com colunas:
        - categoria: Nome da categoria
        - quantidade: Número de conversas
        - percentual: Percentual do total
        - cor: Cor hex para gráfico
    """
    import re
    import json

    # ===================================================================
    # PADRÕES DE CATEGORIZAÇÃO (baseados em análise real)
    # ===================================================================
    CATEGORY_PATTERNS = {
        'AGENDAMENTO': {
            'label': '📅 Agendamentos',
            'color': '#28a745',  # Verde
            'keywords': [
                r'\bagendar\b', r'\bagendamento\b', r'\bmarcar\b', r'\bhorário\b',
                r'\bvisita\b', r'\bdata\b', r'\bhora\b', r'\bquando\b',
                r'\bexperimental\b', r'\btreino experimental\b', r'\baula experimental\b',
                r'\bpode ser\b', r'\bagendado\b', r'\bconfirmado\b', r'\bok\s*✅\b',
                r'\bagendei\b', r'\tte espero\b', r'\bmarcado\b'
            ],
            'weight': 2  # Prioridade alta
        },

        'PREÇO/PLANOS': {
            'label': '💰 Preços & Planos',
            'color': '#ffc107',  # Amarelo
            'keywords': [
                r'\bpreço\b', r'\bvalor\b', r'\bcusto\b', r'\bquanto\b',
                r'\bplano\b', r'\bmensalidade\b', r'\bmatrícula\b',
                r'\bpagamento\b', r'\bforma de pagamento\b', r'\bpagar\b',
                r'\bpix\b', r'\bcartão\b', r'\bparcela\b', r'\bdinheiro\b',
                r'\bcondição\b', r'\bpromoção\b', r'\bdesconto\b'
            ],
            'weight': 2
        },

        'INFORMAÇÕES GERAIS': {
            'label': 'ℹ️ Informações Gerais',
            'color': '#17a2b8',  # Azul claro
            'keywords': [
                r'\binformação\b', r'\bsobre\b', r'\bcomo funciona\b',
                r'\bfunciona\b', r'\bdetalhes\b', r'\bme fala\b',
                r'\bme explica\b', r'\bquero saber\b', r'\bgostaria de saber\b',
                r'\bconhecer\b', r'\bserviços\b'
            ],
            'weight': 1
        },

        'SUPORTE/DÚVIDAS': {
            'label': '❓ Suporte & Dúvidas',
            'color': '#20c997',  # Verde água
            'keywords': [
                r'\bajuda\b', r'\bdúvida\b', r'\bnão entendi\b',
                r'\bcomo faz\b', r'\bcomo faço\b', r'\bpreciso de ajuda\b',
                r'\bsuporte\b', r'\batendimento\b', r'\bproblema\b'
            ],
            'weight': 1
        },

        'CANCELAMENTO/RECLAMAÇÃO': {
            'label': '🚫 Cancelamentos',
            'color': '#dc3545',  # Vermelho
            'keywords': [
                r'\bcancelar\b', r'\bcancelamento\b', r'\bdesistir\b',
                r'\breclamação\b', r'\bnão funcionou\b',
                r'\binsatisfeito\b', r'\bruim\b', r'\bpéssimo\b'
            ],
            'weight': 2
        }
    }

    def extract_messages_text(message_compiled):
        """Extrai texto limpo das mensagens compiladas"""
        try:
            if isinstance(message_compiled, str):
                messages = json.loads(message_compiled)
            else:
                messages = message_compiled

            texts = []
            for msg in messages:
                # Pular mensagens do sistema
                if msg.get('message_type') in [2, 3]:
                    continue

                text = msg.get('text', '')
                if text:
                    texts.append(text.lower())

            return ' '.join(texts)
        except:
            return ''

    def categorize_single_conversation(message_text):
        """Categoriza uma conversa baseada em palavras-chave"""
        category_scores = {}

        for category, config in CATEGORY_PATTERNS.items():
            score = 0

            for pattern in config['keywords']:
                if re.search(pattern, message_text):
                    score += config['weight']

            if score > 0:
                category_scores[category] = score

        # Se não encontrou nenhuma categoria, retornar OUTROS
        if not category_scores:
            return 'OUTROS'

        # Retornar categoria com maior score
        primary_category = max(category_scores, key=category_scores.get)
        return primary_category

    # ===================================================================
    # PROCESSAR TODAS AS CONVERSAS
    # ===================================================================
    categories = []

    for _, row in df.iterrows():
        message_compiled = row.get('message_compiled')
        if not message_compiled or message_compiled == 'null':
            categories.append('OUTROS')
            continue

        message_text = extract_messages_text(message_compiled)
        category = categorize_single_conversation(message_text)
        categories.append(category)

    # ===================================================================
    # CALCULAR ESTATÍSTICAS
    # ===================================================================
    from collections import Counter
    category_counter = Counter(categories)
    total = len(categories)

    # Criar DataFrame de resultado
    result_data = []

    for category, count in category_counter.most_common():
        percentage = (count / total * 100) if total > 0 else 0

        # Pegar configuração da categoria (ou usar padrão para OUTROS)
        config = CATEGORY_PATTERNS.get(category, {
            'label': '📦 Outros',
            'color': '#6c757d'
        })

        result_data.append({
            'categoria': config['label'],
            'quantidade': count,
            'percentual': round(percentage, 1),
            'cor': config['color']
        })

    result_df = pd.DataFrame(result_data)

    # ===================================================================
    # VALIDAÇÃO: Se não houver dados, retornar DataFrame vazio
    # ===================================================================
    if result_df.empty or total == 0:
        return pd.DataFrame(columns=['categoria', 'quantidade', 'percentual', 'cor'])

    # ===================================================================
    # AGRUPAR CATEGORIAS MENORES EM "OUTROS"
    # ===================================================================
    # Separar categorias principais (>= threshold) das menores
    main_categories = result_df[result_df['percentual'] >= min_threshold].copy()
    small_categories = result_df[result_df['percentual'] < min_threshold]

    # Se tiver categorias pequenas, agrupar em OUTROS
    if not small_categories.empty:
        outros_total = small_categories['quantidade'].sum()
        outros_perc = small_categories['percentual'].sum()

        # Verificar se já existe categoria OUTROS nas principais
        outros_mask = main_categories['categoria'] == '📦 Outros'
        if outros_mask.any():
            # Somar com OUTROS existente
            main_categories.loc[outros_mask, 'quantidade'] += outros_total
            main_categories.loc[outros_mask, 'percentual'] += outros_perc
        else:
            # Criar nova entrada OUTROS
            outros_row = pd.DataFrame([{
                'categoria': '📦 Outros',
                'quantidade': outros_total,
                'percentual': round(outros_perc, 1),
                'cor': '#6c757d'
            }])
            main_categories = pd.concat([main_categories, outros_row], ignore_index=True)

    # Ordenar por quantidade (maior primeiro)
    main_categories = main_categories.sort_values('quantidade', ascending=False).reset_index(drop=True)

    return main_categories
