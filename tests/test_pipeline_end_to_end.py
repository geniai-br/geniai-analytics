"""
Test Pipeline End-to-End
=========================

Testa o pipeline completo com dados reais do AllpFit.

Execução:
    cd /home/tester/projetos/allpfit-analytics
    source venv/bin/activate
    python tests/test_pipeline_end_to_end.py
"""

import sys
import os
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Adicionar path do projeto
sys.path.insert(0, '/home/tester/projetos/allpfit-analytics')

from src.multi_tenant.etl_v4.pipeline import ETLPipeline


def print_section(title):
    """Imprime seção formatada"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def get_local_engine():
    """Cria engine para banco local usando johan_geniai"""
    password = quote_plus('vlVMVM6UNz2yYSBlzodPjQvZh')
    connection_string = f"postgresql://johan_geniai:{password}@localhost:5432/geniai_analytics"

    engine = create_engine(
        connection_string,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        echo=False
    )

    return engine


def check_tenant_config(engine, tenant_id):
    """Verifica configuração do tenant"""
    query = text("""
        SELECT
            t.name as tenant_name,
            tc.features->>'use_openai' as use_openai,
            tc.features->>'ai_analysis' as ai_analysis
        FROM tenant_configs tc
        JOIN tenants t ON t.id = tc.tenant_id
        WHERE tc.tenant_id = :tenant_id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id})
        row = result.fetchone()

        if row:
            return {
                'tenant_name': row[0],
                'use_openai': row[1],
                'ai_analysis': row[2]
            }
        else:
            return None


def check_etl_history(engine, tenant_id, limit=5):
    """Verifica histórico de execuções ETL"""
    query = text("""
        SELECT
            id,
            started_at,
            finished_at,
            duration_seconds,
            status,
            load_type,
            records_extracted,
            records_inserted,
            records_updated,
            openai_api_calls,
            openai_total_tokens,
            openai_cost_brl
        FROM etl_control
        WHERE tenant_id = :tenant_id
        ORDER BY started_at DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id, 'limit': limit})

        history = []
        for row in result:
            history.append({
                'id': row[0],
                'started_at': row[1],
                'finished_at': row[2],
                'duration_seconds': row[3],
                'status': row[4],
                'load_type': row[5],
                'records_extracted': row[6],
                'records_inserted': row[7],
                'records_updated': row[8],
                'openai_api_calls': row[9],
                'openai_total_tokens': row[10],
                'openai_cost_brl': row[11]
            })

        return history


def check_conversations_data(engine, tenant_id, limit=10):
    """Verifica dados de conversas processadas"""
    query = text("""
        SELECT
            conversation_id,
            contact_name,
            is_lead,
            visit_scheduled,
            crm_converted,
            ai_probability_label,
            ai_probability_score
        FROM conversations_analytics
        WHERE tenant_id = :tenant_id
        ORDER BY conversation_created_at DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'tenant_id': tenant_id, 'limit': limit})

        conversations = []
        for row in result:
            conversations.append({
                'conversation_id': row[0],
                'contact_name': row[1],
                'is_lead': row[2],
                'visit_scheduled': row[3],
                'crm_converted': row[4],
                'ai_probability_label': row[5],
                'ai_probability_score': row[6]
            })

        return conversations


def test_pipeline_with_regex(tenant_id=1):
    """Testa pipeline com Regex analyzer"""
    print_section(f"TEST 1: Pipeline End-to-End com Regex - Tenant {tenant_id}")

    # Criar engine
    local_engine = get_local_engine()

    # Verificar configuração do tenant
    print("📋 Verificando configuração do tenant...")
    config = check_tenant_config(local_engine, tenant_id)

    if not config:
        print(f"❌ ERRO: Tenant {tenant_id} não encontrado")
        return False

    print(f"✅ Tenant: {config['tenant_name']}")
    print(f"   use_openai: {config['use_openai']}")
    print(f"   ai_analysis: {config['ai_analysis']}")

    # Garantir que OpenAI está desabilitado para este teste
    if config['use_openai'] == 'true':
        print("\n⚠️  OpenAI está habilitado! Vou desabilitar para testar Regex primeiro...")

        with local_engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE tenant_configs DISABLE TRIGGER trigger_log_tenant_configs_changes;
                UPDATE tenant_configs
                SET features = features || '{"use_openai": false}'::jsonb
                WHERE tenant_id = :tenant_id;
                ALTER TABLE tenant_configs ENABLE TRIGGER trigger_log_tenant_configs_changes;
            """), {'tenant_id': tenant_id})

        print("✅ OpenAI desabilitado")

    # Criar pipeline
    print("\n🔧 Criando pipeline...")
    pipeline = ETLPipeline(local_engine=local_engine)
    print("✅ Pipeline criado")

    # Testar conexões
    print("\n🔌 Testando conexões...")
    if not pipeline.test_connection():
        print("❌ ERRO: Falha nas conexões")
        return False
    print("✅ Conexões OK")

    # Executar ETL
    print(f"\n🚀 Executando ETL para tenant {tenant_id}...")
    print("   (Isso pode levar alguns minutos...)\n")

    start_time = datetime.now()

    try:
        stats = pipeline.run_for_tenant(
            tenant_id=tenant_id,
            force_full=False,  # Incremental
            chunk_size=1000,
            triggered_by='test_script'
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if not stats['success']:
            print(f"\n❌ ETL FALHOU: {stats.get('error', 'Unknown')}")
            return False

        # Mostrar resultados
        print("\n" + "=" * 80)
        print("  ✅ ETL CONCLUÍDO COM SUCESSO")
        print("=" * 80)
        print(f"\n📊 Estatísticas:")
        print(f"   Tenant: {tenant_id}")
        print(f"   Tipo: {stats['load_type']}")
        print(f"   Chunks: {stats['chunks_processed']}")
        print(f"   Extraídas: {stats['records_extracted']}")
        print(f"   Inseridas: {stats['records_inserted']}")
        print(f"   Atualizadas: {stats['records_updated']}")
        print(f"   Tempo: {elapsed:.1f}s")
        print(f"   Velocidade: {stats['records_extracted'] / elapsed:.1f} conv/s")

        # Verificar histórico ETL
        print("\n📜 Histórico de execuções (últimas 3):")
        history = check_etl_history(local_engine, tenant_id, limit=3)

        for i, exec_record in enumerate(history, 1):
            print(f"\n   [{i}] Execução {exec_record['id']}")
            print(f"       Data: {exec_record['started_at']}")
            print(f"       Status: {exec_record['status']}")
            print(f"       Tipo: {exec_record['load_type']}")
            print(f"       Duração: {exec_record['duration_seconds']}s")
            print(f"       Extraídas: {exec_record['records_extracted']}")
            print(f"       Inseridas: {exec_record['records_inserted']}")

            if exec_record['openai_api_calls'] and exec_record['openai_api_calls'] > 0:
                print(f"       OpenAI Calls: {exec_record['openai_api_calls']}")
                print(f"       OpenAI Tokens: {exec_record['openai_total_tokens']}")
                print(f"       OpenAI Cost: R$ {exec_record['openai_cost_brl']:.4f}")
            else:
                print(f"       Analyzer: Regex (keywords)")

        # Verificar dados processados
        print("\n📊 Amostra de conversas processadas (últimas 5):")
        conversations = check_conversations_data(local_engine, tenant_id, limit=5)

        for i, conv in enumerate(conversations, 1):
            print(f"\n   [{i}] Conversa {conv['conversation_id']}")
            print(f"       Contato: {conv['contact_name']}")
            print(f"       Lead: {'✅' if conv['is_lead'] else '❌'}")
            print(f"       Visita: {'✅' if conv['visit_scheduled'] else '❌'}")
            print(f"       Conversão: {'✅' if conv['crm_converted'] else '❌'}")
            print(f"       Probabilidade: {conv['ai_probability_label']} ({conv['ai_probability_score']:.1f})")

        # Estatísticas gerais
        print("\n📈 Estatísticas gerais:")

        with local_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_lead THEN 1 ELSE 0 END) as leads,
                    SUM(CASE WHEN visit_scheduled THEN 1 ELSE 0 END) as visits,
                    SUM(CASE WHEN crm_converted THEN 1 ELSE 0 END) as conversions,
                    ROUND(AVG(ai_probability_score), 2) as avg_score
                FROM conversations_analytics
                WHERE tenant_id = :tenant_id
            """), {'tenant_id': tenant_id}).fetchone()

            total, leads, visits, conversions, avg_score = result

            print(f"   Total conversas: {total}")
            print(f"   Leads: {leads} ({leads/total*100:.1f}%)" if total > 0 else "   Leads: 0")
            print(f"   Visitas: {visits} ({visits/leads*100:.1f}%)" if leads > 0 else "   Visitas: 0")
            print(f"   Conversões: {conversions} ({conversions/total*100:.1f}%)" if total > 0 else "   Conversões: 0")
            print(f"   Score médio: {avg_score}")

        print("\n✅ PASS - Pipeline funcionando corretamente com Regex!")
        return True

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ ERRO ao executar ETL ({elapsed:.1f}s): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "🧪" * 40)
    print("  PIPELINE END-TO-END TEST SUITE")
    print("  Fase 5.6 - OpenAI Integration")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🧪" * 40)

    # Tenant AllpFit (ID=1)
    tenant_id = 1

    results = {
        'test_pipeline_regex': test_pipeline_with_regex(tenant_id),
    }

    # Resumo final
    print_section("RESUMO FINAL")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n📊 Total: {passed}/{total} testes passaram")

    if passed == total:
        print("\n🎉 SUCCESS - Todos os testes passaram!")
        return 0
    else:
        print(f"\n❌ FAILURE - {total - passed} teste(s) falharam")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)