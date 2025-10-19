"""
Script de teste para validar as views após deploy no banco de produção
Executa uma série de testes para garantir que tudo está funcionando
"""
import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.shared.config import Config


def test_views():
    """Testa as views criadas no banco de produção"""

    print("=" * 80)
    print("TESTE DAS VIEWS - Banco de Produção")
    print("=" * 80)
    print()

    try:
        # Conectar ao banco
        conn_str = Config.get_source_connection_string()
        engine = create_engine(conn_str)

        views_to_test = [
            'vw_conversations_base_complete',
            'vw_messages_compiled_complete',
            'vw_csat_base',
            'vw_conversation_metrics_complete',
            'vw_message_stats_complete',
            'vw_temporal_metrics',
            'vw_conversations_analytics_final'
        ]

        results = []

        print("TESTE 1: Verificando se as views existem")
        print("-" * 80)

        for view_name in views_to_test:
            query = text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_views
                    WHERE viewname = :view_name
                    AND schemaname = 'public'
                )
            """)

            result = engine.execute(query, {'view_name': view_name}).scalar()

            if result:
                print(f"  ✓ {view_name}")
                results.append((view_name, 'EXISTS', True))
            else:
                print(f"  ✗ {view_name} - NÃO ENCONTRADA!")
                results.append((view_name, 'EXISTS', False))

        print()
        print("TESTE 2: Contando registros em cada view")
        print("-" * 80)

        for view_name in views_to_test:
            try:
                count_query = f"SELECT COUNT(*) as total FROM {view_name}"
                count_df = pd.read_sql(count_query, engine)
                total = count_df['total'][0]
                print(f"  ✓ {view_name}: {total:,} registros")
                results.append((view_name, 'COUNT', total))
            except Exception as e:
                print(f"  ✗ {view_name}: ERRO - {str(e)[:50]}")
                results.append((view_name, 'COUNT', f"ERRO: {e}"))

        print()
        print("TESTE 3: Testando query na view final")
        print("-" * 80)

        try:
            test_query = """
                SELECT
                    conversation_id,
                    display_id,
                    status,
                    contact_name,
                    inbox_name,
                    assignee_name,
                    csat_rating,
                    first_response_time_minutes,
                    is_bot_resolved,
                    total_messages_public,
                    conversation_date
                FROM vw_conversations_analytics_final
                LIMIT 5
            """

            test_df = pd.read_sql(test_query, engine)

            print(f"  ✓ Query executada com sucesso!")
            print(f"  ✓ Retornou {len(test_df)} registros")
            print(f"  ✓ Colunas: {len(test_df.columns)}")
            print()
            print("  Amostra dos dados:")
            print(test_df.to_string(index=False))

            results.append(('vw_conversations_analytics_final', 'QUERY_TEST', True))

        except Exception as e:
            print(f"  ✗ ERRO ao executar query: {e}")
            results.append(('vw_conversations_analytics_final', 'QUERY_TEST', False))

        print()
        print("TESTE 4: Verificando campos da view final")
        print("-" * 80)

        try:
            columns_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'vw_conversations_analytics_final'
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """

            columns_df = pd.read_sql(columns_query, engine)
            total_columns = len(columns_df)

            print(f"  ✓ Total de colunas: {total_columns}")

            if total_columns >= 140:
                print(f"  ✓ Quantidade de campos OK (esperado: ~150)")
            else:
                print(f"  ⚠️  Poucos campos! Esperado: ~150, Encontrado: {total_columns}")

            print()
            print("  Primeiras 20 colunas:")
            for col in columns_df['column_name'].head(20):
                print(f"    - {col}")

            results.append(('vw_conversations_analytics_final', 'COLUMNS', total_columns))

        except Exception as e:
            print(f"  ✗ ERRO: {e}")
            results.append(('vw_conversations_analytics_final', 'COLUMNS', f"ERRO: {e}"))

        print()
        print("TESTE 5: Performance - Query com filtro")
        print("-" * 80)

        try:
            import time

            perf_query = """
                SELECT
                    conversation_id,
                    status,
                    inbox_name,
                    first_response_time_minutes
                FROM vw_conversations_analytics_final
                WHERE conversation_date >= CURRENT_DATE - 7
                LIMIT 100
            """

            start_time = time.time()
            perf_df = pd.read_sql(perf_query, engine)
            end_time = time.time()

            duration = end_time - start_time

            print(f"  ✓ Query executada em {duration:.2f} segundos")
            print(f"  ✓ Retornou {len(perf_df)} registros")

            if duration < 5:
                print(f"  ✓ Performance OK (< 5s)")
            else:
                print(f"  ⚠️  Performance lenta (> 5s)")

            results.append(('vw_conversations_analytics_final', 'PERFORMANCE', f"{duration:.2f}s"))

        except Exception as e:
            print(f"  ✗ ERRO: {e}")
            results.append(('vw_conversations_analytics_final', 'PERFORMANCE', f"ERRO: {e}"))

        engine.dispose()

        # Resumo final
        print()
        print("=" * 80)
        print("RESUMO DOS TESTES")
        print("=" * 80)
        print()

        success_count = sum(1 for r in results if r[2] == True or (isinstance(r[2], int) and r[2] > 0))
        total_tests = len(results)

        print(f"Testes executados: {total_tests}")
        print(f"Sucessos: {success_count}")
        print(f"Falhas: {total_tests - success_count}")
        print()

        if success_count == total_tests:
            print("✅ TODOS OS TESTES PASSARAM!")
            print()
            print("Próximo passo: Atualizar o ETL para usar vw_conversations_analytics_final")
        else:
            print("⚠️  ALGUNS TESTES FALHARAM!")
            print()
            print("Verifique os erros acima e corrija antes de prosseguir.")

        print()
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_views()
