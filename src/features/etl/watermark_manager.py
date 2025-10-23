"""
Watermark Manager - Gerenciamento de ponto de sincronização incremental

Este módulo gerencia o watermark (ponto de controle) que permite ao ETL
saber a partir de qual timestamp buscar dados novos/atualizados.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_local_engine():
    """Cria engine de conexão com banco local"""
    password_encoded = quote_plus(os.getenv('LOCAL_DB_PASSWORD'))
    conn_str = (
        f"postgresql://{os.getenv('LOCAL_DB_USER')}:{password_encoded}"
        f"@{os.getenv('LOCAL_DB_HOST')}:{os.getenv('LOCAL_DB_PORT')}/{os.getenv('LOCAL_DB_NAME')}"
    )
    return create_engine(conn_str)


def get_last_watermark():
    """
    Retorna o último watermark bem-sucedido

    Returns:
        datetime or None: Último watermark_end ou None se primeira execução
    """
    try:
        engine = get_local_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT watermark_end
                FROM etl_control
                WHERE status = 'success'
                  AND watermark_end IS NOT NULL
                ORDER BY watermark_end DESC
                LIMIT 1
            """))

            row = result.fetchone()
            if row and row[0]:
                return row[0]

            return None

    except Exception as e:
        print(f"⚠️  Erro ao buscar watermark: {e}")
        return None
    finally:
        engine.dispose()


def create_etl_execution(triggered_by='manual', load_type='incremental', is_full_load=False):
    """
    Cria registro de nova execução do ETL com status 'running'

    Args:
        triggered_by: Como foi disparado ('manual', 'scheduler', 'api')
        load_type: Tipo de carga ('incremental', 'full')
        is_full_load: Se é carga completa

    Returns:
        int: ID da execução criada
    """
    try:
        import socket
        hostname = socket.gethostname()

        engine = get_local_engine()
        with engine.connect() as conn:
            # Buscar último watermark
            watermark_start = get_last_watermark()

            result = conn.execute(text("""
                INSERT INTO etl_control (
                    started_at,
                    status,
                    watermark_start,
                    triggered_by,
                    load_type,
                    is_full_load,
                    hostname,
                    etl_version
                ) VALUES (
                    NOW(),
                    'running',
                    :watermark_start,
                    :triggered_by,
                    :load_type,
                    :is_full_load,
                    :hostname,
                    'v3.0'
                )
                RETURNING id
            """), {
                'watermark_start': watermark_start,
                'triggered_by': triggered_by,
                'load_type': load_type,
                'is_full_load': is_full_load,
                'hostname': hostname
            })

            conn.commit()
            execution_id = result.fetchone()[0]

            return execution_id

    except Exception as e:
        print(f"❌ Erro ao criar execução do ETL: {e}")
        raise
    finally:
        engine.dispose()


def update_etl_execution(
    execution_id,
    status='success',
    watermark_end=None,
    rows_extracted=0,
    rows_inserted=0,
    rows_updated=0,
    rows_unchanged=0,
    duration_seconds=0,
    extract_duration=0,
    transform_duration=0,
    load_duration=0,
    error_message=None,
    error_traceback=None
):
    """
    Atualiza registro de execução do ETL

    Args:
        execution_id: ID da execução
        status: 'success' ou 'failed'
        watermark_end: Timestamp do último registro processado
        rows_*: Estatísticas de linhas
        duration_*: Durações em segundos
        error_*: Informações de erro
    """
    try:
        engine = get_local_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE etl_control SET
                    completed_at = NOW(),
                    status = :status,
                    watermark_end = :watermark_end,
                    rows_extracted = :rows_extracted,
                    rows_inserted = :rows_inserted,
                    rows_updated = :rows_updated,
                    rows_unchanged = :rows_unchanged,
                    duration_seconds = :duration_seconds,
                    extract_duration_seconds = :extract_duration,
                    transform_duration_seconds = :transform_duration,
                    load_duration_seconds = :load_duration,
                    error_message = :error_message,
                    error_traceback = :error_traceback
                WHERE id = :execution_id
            """), {
                'execution_id': execution_id,
                'status': status,
                'watermark_end': watermark_end,
                'rows_extracted': rows_extracted,
                'rows_inserted': rows_inserted,
                'rows_updated': rows_updated,
                'rows_unchanged': rows_unchanged,
                'duration_seconds': duration_seconds,
                'extract_duration': extract_duration,
                'transform_duration': transform_duration,
                'load_duration': load_duration,
                'error_message': error_message,
                'error_traceback': error_traceback
            })

            conn.commit()

    except Exception as e:
        print(f"❌ Erro ao atualizar execução do ETL: {e}")
        raise
    finally:
        engine.dispose()


def get_etl_stats(limit=10):
    """
    Retorna estatísticas das últimas execuções do ETL

    Args:
        limit: Número de execuções a retornar

    Returns:
        list: Lista de dicionários com estatísticas
    """
    try:
        engine = get_local_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM vw_etl_stats
                LIMIT :limit
            """), {'limit': limit})

            columns = result.keys()
            rows = []
            for row in result:
                rows.append(dict(zip(columns, row)))

            return rows

    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas do ETL: {e}")
        return []
    finally:
        engine.dispose()
