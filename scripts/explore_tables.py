"""
Script para explorar as tabelas principais do Chatwoot
"""
import sys
import os
import pandas as pd
from sqlalchemy import create_engine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.shared.config import Config


def explore_tables():
    """Explora estrutura das tabelas principais"""

    print("=" * 80)
    print("EXPLORAÇÃO DAS TABELAS DO CHATWOOT")
    print("=" * 80)

    # Tabelas principais que precisamos analisar
    main_tables = [
        'conversations',
        'contacts',
        'inboxes',
        'messages',
        'users',
        'teams',
        'labels',
        'csat_survey_responses',
        'accounts',
        'conversation_participants',
        'contact_inboxes',
        'inbox_members',
        'team_members',
        'automation_rules',
        'agent_bots'
    ]

    try:
        conn_str = Config.get_source_connection_string()
        engine = create_engine(conn_str)

        for table in main_tables:
            print(f"\n{'='*80}")
            print(f"TABELA: {table}")
            print('='*80)

            # Verificar se a tabela existe
            check_query = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                )
            """

            exists_df = pd.read_sql(check_query, engine)

            if not exists_df.iloc[0, 0]:
                print(f"⚠️  Tabela '{table}' NÃO EXISTE no banco")
                continue

            # Estrutura da tabela
            columns_query = f"""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """

            columns_df = pd.read_sql(columns_query, engine)

            if len(columns_df) > 0:
                print(f"\n✓ Tabela existe com {len(columns_df)} colunas:")
                print("\n" + columns_df.to_string(index=False))

                # Contar registros
                try:
                    count_query = f"SELECT COUNT(*) as total FROM {table}"
                    count_df = pd.read_sql(count_query, engine)
                    print(f"\nTotal de registros: {count_df['total'][0]:,}")
                except Exception as e:
                    print(f"\nErro ao contar registros: {e}")

                # Amostra de dados (apenas algumas colunas principais)
                try:
                    sample_query = f"SELECT * FROM {table} LIMIT 3"
                    sample_df = pd.read_sql(sample_query, engine)
                    print(f"\nAmostra de dados (primeiras 3 linhas):")
                    # Mostrar apenas primeiras 5 colunas para não poluir
                    print(sample_df.iloc[:, :min(5, len(sample_df.columns))].to_string(index=False))
                except Exception as e:
                    print(f"\nErro ao buscar amostra: {e}")

        engine.dispose()

        print("\n" + "=" * 80)
        print("✓ EXPLORAÇÃO CONCLUÍDA")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    explore_tables()
