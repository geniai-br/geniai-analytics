"""
Extractor - Extração incremental de dados do banco remoto

Este módulo é responsável por:
1. Conectar ao banco remoto (Chatwoot)
2. Buscar apenas dados novos/atualizados (usando watermark)
3. Retornar DataFrame com dados extraídos
"""

import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def get_source_engine():
    """Cria engine de conexão com banco remoto (Chatwoot)"""
    conn_str = (
        f"postgresql://{os.getenv('SOURCE_DB_USER')}:{os.getenv('SOURCE_DB_PASSWORD')}"
        f"@{os.getenv('SOURCE_DB_HOST')}:{os.getenv('SOURCE_DB_PORT')}/{os.getenv('SOURCE_DB_NAME')}"
    )
    return create_engine(conn_str)


def extract_incremental(watermark_start=None, inbox_filter='allpfitjpsulcloud1'):
    """
    Extrai dados incrementais do banco remoto

    Args:
        watermark_start: Timestamp de início (None = buscar tudo)
        inbox_filter: Nome da inbox para filtrar (padrão: allpfitjpsulcloud1)

    Returns:
        tuple: (DataFrame, watermark_end, duration_seconds)
    """
    print("=" * 80)
    print("EXTRACT: Extração Incremental")
    print("=" * 80)

    start_time = datetime.now()

    try:
        engine = get_source_engine()

        # Construir query incremental
        if watermark_start:
            print(f"📅 Modo INCREMENTAL")
            print(f"   Watermark inicial: {watermark_start}")
            print(f"   Buscando conversas com updated_at > '{watermark_start}'")

            query = text("""
                SELECT *
                FROM vw_conversations_analytics_final
                WHERE conversation_updated_at > :watermark
                  AND inbox_name = :inbox
                ORDER BY conversation_updated_at ASC
            """)

            params = {
                'watermark': watermark_start,
                'inbox': inbox_filter
            }

        else:
            print(f"📅 Modo FULL LOAD (primeira execução)")
            print(f"   Buscando TODAS as conversas")

            query = text("""
                SELECT *
                FROM vw_conversations_analytics_final
                WHERE inbox_name = :inbox
                ORDER BY conversation_updated_at ASC
            """)

            params = {'inbox': inbox_filter}

        print(f"\n🔍 Executando query...")

        # Executar query
        df = pd.read_sql(query, engine, params=params)

        elapsed = (datetime.now() - start_time).total_seconds()

        # Determinar watermark_end (último updated_at)
        watermark_end = None
        if not df.empty and 'conversation_updated_at' in df.columns:
            watermark_end = df['conversation_updated_at'].max()

        print(f"\n✅ Extração concluída!")
        print(f"   Linhas extraídas: {len(df):,}")
        print(f"   Colunas: {len(df.columns)}")
        print(f"   Tempo: {elapsed:.2f}s")

        if watermark_end:
            print(f"   Watermark final: {watermark_end}")

        if len(df) > 0:
            print(f"\n📊 Amostra de conversation_ids extraídos:")
            sample_ids = df['conversation_id'].head(5).tolist()
            for conv_id in sample_ids:
                print(f"      - {conv_id}")
            if len(df) > 5:
                print(f"      ... e mais {len(df) - 5} conversas")

        engine.dispose()

        return df, watermark_end, elapsed

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ Erro na extração: {e}")
        import traceback
        traceback.print_exc()
        raise


def extract_full():
    """
    Extrai TODOS os dados do banco remoto (carga completa)

    Returns:
        tuple: (DataFrame, watermark_end, duration_seconds)
    """
    return extract_incremental(watermark_start=None)


def test_connection():
    """
    Testa conexão com banco remoto

    Returns:
        bool: True se conectou com sucesso
    """
    try:
        print("🔌 Testando conexão com banco remoto...")
        print(f"   Host: {os.getenv('SOURCE_DB_HOST')}")
        print(f"   Database: {os.getenv('SOURCE_DB_NAME')}")
        print(f"   User: {os.getenv('SOURCE_DB_USER')}")

        engine = get_source_engine()

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            test_value = result.scalar()

            if test_value == 1:
                print("   ✅ Conexão bem-sucedida!")

                # Testar view
                result = conn.execute(text("""
                    SELECT COUNT(*) as total
                    FROM vw_conversations_analytics_final
                    WHERE inbox_name = 'allpfitjpsulcloud1'
                """))
                total = result.scalar()
                print(f"   ✅ View acessível: {total:,} conversas encontradas")

                engine.dispose()
                return True

    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        return False


if __name__ == "__main__":
    # Teste de conexão
    test_connection()
