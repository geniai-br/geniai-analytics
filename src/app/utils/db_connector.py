"""
Database Connector - Conexão com PostgreSQL local
"""

import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@st.cache_resource
def get_engine():
    """
    Cria e retorna engine de conexão com banco local
    Usa cache do Streamlit para não recriar a cada execução
    """
    password_encoded = quote_plus(os.getenv('LOCAL_DB_PASSWORD', ''))

    conn_str = (
        f"postgresql://{os.getenv('LOCAL_DB_USER', 'isaac')}:{password_encoded}"
        f"@{os.getenv('LOCAL_DB_HOST', 'localhost')}:{os.getenv('LOCAL_DB_PORT', '5432')}"
        f"/{os.getenv('LOCAL_DB_NAME', 'allpfit')}"
    )

    return create_engine(conn_str)


@st.cache_data(ttl=300)  # Cache por 5 minutos
def query_database(query, params=None):
    """
    Executa query no banco e retorna DataFrame

    Args:
        query: SQL query string
        params: Dicionário com parâmetros da query (opcional)

    Returns:
        DataFrame com resultados
    """
    engine = get_engine()

    try:
        if params:
            df = pd.read_sql(text(query), engine, params=params)
        else:
            df = pd.read_sql(query, engine)

        return df

    except Exception as e:
        print(f"Erro ao executar query: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_all_conversations(limit=None):
    """
    Retorna todas as conversas

    Args:
        limit: Limite de registros (None = todos)

    Returns:
        DataFrame com conversas
    """
    query = "SELECT * FROM conversas_analytics ORDER BY conversation_created_at DESC"

    if limit:
        query += f" LIMIT {limit}"

    return query_database(query)


@st.cache_data(ttl=60)  # Cache menor para dados "ao vivo"
def get_conversations_today():
    """
    Retorna conversas de hoje

    Returns:
        DataFrame com conversas de hoje
    """
    query = """
        SELECT *
        FROM conversas_analytics
        WHERE conversation_date = CURRENT_DATE
        ORDER BY conversation_created_at DESC
    """

    return query_database(query)


@st.cache_data(ttl=300)
def get_conversations_by_date_range(start_date, end_date):
    """
    Retorna conversas em um período

    Args:
        start_date: Data início (string ou datetime)
        end_date: Data fim (string ou datetime)

    Returns:
        DataFrame com conversas no período
    """
    query = """
        SELECT *
        FROM conversas_analytics
        WHERE conversation_date BETWEEN :start_date AND :end_date
        ORDER BY conversation_created_at DESC
    """

    return query_database(query, {
        'start_date': start_date,
        'end_date': end_date
    })


def clear_cache():
    """Limpa cache do Streamlit"""
    st.cache_data.clear()
    st.cache_resource.clear()
