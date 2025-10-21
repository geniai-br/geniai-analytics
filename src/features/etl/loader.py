"""
Loader - Carga de dados com UPSERT (INSERT + UPDATE)

Este módulo é responsável por:
1. Inserir novos registros (INSERT)
2. Atualizar registros existentes (UPDATE)
3. Rastrear quantos registros foram inseridos/atualizados/inalterados
"""

import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

LOCAL_TABLE = 'conversas_analytics'


def get_local_engine():
    """Cria engine de conexão com banco local"""
    password_encoded = quote_plus(os.getenv('LOCAL_DB_PASSWORD'))
    conn_str = (
        f"postgresql://{os.getenv('LOCAL_DB_USER')}:{password_encoded}"
        f"@{os.getenv('LOCAL_DB_HOST')}:{os.getenv('LOCAL_DB_PORT')}/{os.getenv('LOCAL_DB_NAME')}"
    )
    return create_engine(conn_str)


def load_upsert(df):
    """
    Carrega dados no banco local usando estratégia UPSERT

    Para cada registro:
    - Se conversation_id já existe: UPDATE (se conversation_updated_at for mais recente)
    - Se conversation_id não existe: INSERT

    Args:
        df: DataFrame com dados transformados

    Returns:
        tuple: (rows_inserted, rows_updated, rows_unchanged, duration_seconds)
    """
    print("\n" + "=" * 80)
    print("LOAD: Carga UPSERT no banco local")
    print("=" * 80)

    if df is None or df.empty:
        print("⚠️  Nenhum dado para carregar")
        return 0, 0, 0, 0

    start_time = datetime.now()

    try:
        engine = get_local_engine()

        print(f"📊 Tabela destino: {LOCAL_TABLE}")
        print(f"   Registros a processar: {len(df):,}")

        rows_inserted = 0
        rows_updated = 0
        rows_unchanged = 0

        # Verificar quais conversation_ids já existem
        with engine.connect() as conn:
            existing_ids_result = conn.execute(text(f"""
                SELECT conversation_id, conversation_updated_at, etl_inserted_at
                FROM {LOCAL_TABLE}
                WHERE conversation_id = ANY(:conv_ids)
            """), {'conv_ids': df['conversation_id'].tolist()})

            existing_data = {}
            for row in existing_ids_result:
                existing_data[row[0]] = {
                    'updated_at': row[1],
                    'inserted_at': row[2]
                }

        print(f"\n📍 Registros existentes no banco: {len(existing_data):,}")
        print(f"   Registros novos: {len(df) - len(existing_data):,}")

        # Processar cada registro
        with engine.connect() as conn:
            for idx, row in df.iterrows():
                conv_id = row['conversation_id']
                conv_updated_at = row.get('conversation_updated_at')

                # Preparar dados
                row_dict = row.to_dict()

                # Tratar valores NaT e NaN no dicionário
                for key, value in row_dict.items():
                    if pd.isna(value):
                        row_dict[key] = None

                # Verificar se já existe
                if conv_id in existing_data:
                    # Registro existe - verificar se precisa atualizar
                    existing_updated_at = existing_data[conv_id]['updated_at']

                    # Atualizar apenas se updated_at remoto for mais recente
                    if conv_updated_at and existing_updated_at and conv_updated_at > existing_updated_at:
                        # UPDATE
                        # Manter o etl_inserted_at original
                        row_dict['etl_inserted_at'] = existing_data[conv_id]['inserted_at']

                        # Construir SET clause dinamicamente
                        set_columns = [f"{col} = :{col}" for col in row_dict.keys() if col != 'conversation_id']
                        set_clause = ', '.join(set_columns)

                        update_query = text(f"""
                            UPDATE {LOCAL_TABLE}
                            SET {set_clause}
                            WHERE conversation_id = :conversation_id
                        """)

                        conn.execute(update_query, row_dict)
                        rows_updated += 1

                    else:
                        # Registro inalterado
                        rows_unchanged += 1

                else:
                    # Registro novo - INSERT
                    # Definir etl_inserted_at para agora
                    row_dict['etl_inserted_at'] = datetime.now()

                    # Construir INSERT dinamicamente
                    columns = list(row_dict.keys())
                    columns_str = ', '.join(columns)
                    values_str = ', '.join([f":{col}" for col in columns])

                    insert_query = text(f"""
                        INSERT INTO {LOCAL_TABLE} ({columns_str})
                        VALUES ({values_str})
                    """)

                    conn.execute(insert_query, row_dict)
                    rows_inserted += 1

            # Commit todas as transações
            conn.commit()

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ Carga UPSERT concluída!")
        print(f"   ✨ Registros inseridos: {rows_inserted:,}")
        print(f"   🔄 Registros atualizados: {rows_updated:,}")
        print(f"   ⚪ Registros inalterados: {rows_unchanged:,}")
        print(f"   ⏱️  Tempo: {elapsed:.2f}s")

        if elapsed > 0:
            rate = (rows_inserted + rows_updated) / elapsed
            print(f"   ⚡ Velocidade: {rate:.0f} registros/segundo")

        engine.dispose()

        return rows_inserted, rows_updated, rows_unchanged, elapsed

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ Erro na carga: {e}")
        import traceback
        traceback.print_exc()
        raise


def load_full(df, truncate=True):
    """
    Carga completa (TRUNCATE + INSERT)

    Args:
        df: DataFrame com dados
        truncate: Se True, limpa tabela antes (padrão: True)

    Returns:
        tuple: (rows_inserted, duration_seconds)
    """
    print("\n" + "=" * 80)
    print("LOAD: Carga FULL (TRUNCATE + INSERT)")
    print("=" * 80)

    if df is None or df.empty:
        print("⚠️  Nenhum dado para carregar")
        return 0, 0

    start_time = datetime.now()

    try:
        engine = get_local_engine()

        if truncate:
            print(f"🗑️  Limpando tabela {LOCAL_TABLE}...")
            with engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {LOCAL_TABLE} CASCADE"))
                conn.commit()
            print("   ✅ Tabela limpa")

        # Adicionar etl_inserted_at para todos os registros
        df['etl_inserted_at'] = datetime.now()

        print(f"\n📥 Inserindo {len(df):,} registros...")

        # Insert em batch usando pandas to_sql
        df.to_sql(
            LOCAL_TABLE,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=500
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ Carga FULL concluída!")
        print(f"   Registros inseridos: {len(df):,}")
        print(f"   Tempo: {elapsed:.2f}s")
        print(f"   Velocidade: {len(df)/elapsed:.0f} registros/segundo")

        engine.dispose()

        return len(df), elapsed

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ Erro na carga: {e}")
        import traceback
        traceback.print_exc()
        raise
