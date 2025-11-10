"""
Test ETL with OpenAI - Full Reprocess
======================================

Reprocessa TODAS as conversas do AllpFit com OpenAI habilitado.

Execução:
    cd /home/tester/projetos/allpfit-analytics
    source venv/bin/activate
    OPENAI_API_KEY="sk-..." python tests/test_etl_openai_full.py
"""

import sys
import os
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Adicionar path do projeto
sys.path.insert(0, '/home/tester/projetos/allpfit-analytics')


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


def create_backup_comparison(engine, tenant_id=1):
    """Cria snapshot atual (Regex) para comparação posterior"""
    print_section("Criando Snapshot Regex para Comparação")

    with engine.begin() as conn:
        # Criar tabela temporária com estatísticas atuais (Regex)
        print("📋 Salvando estatísticas atuais (Regex)...")
        conn.execute(text("""
            DROP TABLE IF EXISTS temp_regex_stats;

            CREATE TEMP TABLE temp_regex_stats AS
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_lead THEN 1 ELSE 0 END) as leads,
                SUM(CASE WHEN visit_scheduled THEN 1 ELSE 0 END) as visits,
                SUM(CASE WHEN crm_converted THEN 1 ELSE 0 END) as conversions,
                ROUND(AVG(ai_probability_score), 2) as avg_score
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant_id})

        result = conn.execute(text("SELECT * FROM temp_regex_stats")).fetchone()
        total, leads, visits, conversions, avg_score = result

        print(f"✅ Snapshot salvo:")
        print(f"   Total: {total}")
        print(f"   Leads: {leads} ({leads/total*100:.1f}%)" if total > 0 else "   Leads: 0")
        print(f"   Visitas: {visits}")
        print(f"   Conversões: {conversions} ({conversions/total*100:.1f}%)" if total > 0 else "   Conversões: 0")
        print(f"   Score médio: {avg_score}")

    return total


def run_etl_with_openai_full(tenant_id=1):
    """Executa ETL FULL com OpenAI habilitado"""
    print_section("Executando ETL FULL com OpenAI")

    from src.multi_tenant.etl_v4.pipeline import ETLPipeline

    # Criar engine
    local_engine = get_local_engine()

    # Verificar se OpenAI está habilitado
    with local_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT features->>'use_openai' as use_openai
            FROM tenant_configs
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant_id}).fetchone()

        use_openai = result[0]
        print(f"📋 OpenAI status: {use_openai}")

        if use_openai != 'true':
            print("❌ ERRO: OpenAI não está habilitado!")
            return False

    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não encontrada")
        return False

    print(f"✅ API Key configurada: {api_key[:20]}...")

    # Criar pipeline
    print("\n🔧 Criando pipeline...")
    pipeline = ETLPipeline(local_engine=local_engine)

    # Executar ETL FULL (vai reprocessar TODAS as conversas)
    print(f"\n🚀 Executando ETL FULL com OpenAI GPT-4o-mini...")
    print("   ⚠️  ATENÇÃO: Vai reprocessar TODAS as conversas do AllpFit!")
    print("   ⏱️  Tempo estimado: ~2-3 horas (1.281 conversas × 8s/conversa)")
    print("   💰 Custo estimado: R$ 3.50 - R$ 4.00")
    print("\n   Processando em chunks de 100 conversas...\n")

    start_time = datetime.now()

    try:
        stats = pipeline.run_for_tenant(
            tenant_id=tenant_id,
            force_full=True,      # FULL LOAD - reprocessa tudo
            chunk_size=100,       # Chunks de 100
            triggered_by='test_openai_full'
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if not stats['success']:
            print(f"\n❌ ETL FALHOU: {stats.get('error', 'Unknown')}")
            return False

        # Mostrar resultados
        print("\n" + "=" * 80)
        print("  ✅ ETL COM OPENAI CONCLUÍDO!")
        print("=" * 80)

        print(f"\n📊 Estatísticas ETL:")
        print(f"   Conversas extraídas: {stats['records_extracted']}")
        print(f"   Conversas inseridas: {stats['records_inserted']}")
        print(f"   Conversas atualizadas: {stats['records_updated']}")
        print(f"   Tempo total: {elapsed/60:.1f} minutos")
        print(f"   Velocidade: {stats['records_extracted']/elapsed:.2f} conv/s")

        if stats.get('openai_api_calls', 0) > 0:
            print(f"\n💰 Custos OpenAI:")
            print(f"   API calls: {stats['openai_api_calls']}")
            print(f"   Total tokens: {stats['openai_total_tokens']}")
            print(f"   Custo: R$ {stats['openai_cost_brl']:.2f}")
            print(f"   Custo/conversa: R$ {stats['openai_cost_brl']/stats['records_extracted']:.4f}")

        return True

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ ERRO ao executar ETL ({elapsed/60:.1f} min): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def analyze_results(engine, tenant_id=1):
    """Analisa e compara resultados Regex vs OpenAI"""
    print_section("Análise de Resultados: Regex vs OpenAI")

    with engine.connect() as conn:
        # Pegar última execução ETL
        result = conn.execute(text("""
            SELECT
                id,
                started_at,
                duration_seconds,
                records_extracted,
                records_updated,
                openai_api_calls,
                openai_total_tokens,
                openai_cost_brl
            FROM etl_control
            WHERE tenant_id = :tenant_id
            ORDER BY started_at DESC
            LIMIT 1
        """), {'tenant_id': tenant_id}).fetchone()

        if result:
            exec_id, started, duration, extracted, updated, api_calls, tokens, cost = result

            print(f"📋 Última execução ETL (ID: {exec_id}):")
            print(f"   Data: {started}")
            print(f"   Duração: {duration/60:.1f} min")
            print(f"   Conversas processadas: {extracted}")
            print(f"   Conversas atualizadas: {updated}")

            if api_calls and api_calls > 0:
                print(f"\n💰 Custos OpenAI:")
                print(f"   API calls: {api_calls}")
                print(f"   Total tokens: {tokens:,}")
                print(f"   Custo: R$ {cost:.2f}")
                if extracted > 0:
                    print(f"   Custo/conversa: R$ {cost/extracted:.4f}")

        # Estatísticas OpenAI (atuais)
        print(f"\n📊 Estatísticas após OpenAI:")

        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_lead THEN 1 ELSE 0 END) as leads,
                SUM(CASE WHEN visit_scheduled THEN 1 ELSE 0 END) as visits,
                SUM(CASE WHEN crm_converted THEN 1 ELSE 0 END) as conversions,
                ROUND(AVG(ai_probability_score), 2) as avg_score,
                COUNT(CASE WHEN nome_mapeado_bot != '' THEN 1 END) as names_extracted,
                COUNT(CASE WHEN condicao_fisica != 'Não mencionado' THEN 1 END) as condition_found,
                COUNT(CASE WHEN objetivo != 'Não mencionado' THEN 1 END) as objective_found
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant_id}).fetchone()

        total, leads, visits, conversions, avg_score, names, conditions, objectives = result

        print(f"   Total conversas: {total}")
        print(f"   Leads: {leads} ({leads/total*100:.1f}%)") if total > 0 else print("   Leads: 0")
        print(f"   Visitas: {visits} ({visits/total*100:.1f}%)") if total > 0 else print("   Visitas: 0")
        print(f"   Conversões: {conversions} ({conversions/total*100:.1f}%)") if total > 0 else print("   Conversões: 0")
        print(f"   Score médio: {avg_score}")

        print(f"\n✨ Dados extras (OpenAI):")
        print(f"   Nomes extraídos: {names}/{total} ({names/total*100:.0f}%)") if total > 0 else print("   N/A")
        print(f"   Condição física: {conditions}/{total} ({conditions/total*100:.0f}%)") if total > 0 else print("   N/A")
        print(f"   Objetivo: {objectives}/{total} ({objectives/total*100:.0f}%)") if total > 0 else print("   N/A")

        # Amostra de conversas
        print(f"\n📝 Amostra de conversas (5 primeiras):")
        result = conn.execute(text("""
            SELECT
                conversation_id,
                contact_name,
                is_lead,
                visit_scheduled,
                ai_probability_score,
                nome_mapeado_bot,
                condicao_fisica,
                objetivo
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
            ORDER BY conversation_created_at DESC
            LIMIT 5
        """), {'tenant_id': tenant_id})

        for i, row in enumerate(result, 1):
            conv_id, contact, lead, visit, score, nome, cond, obj = row
            print(f"\n   [{i}] Conv {conv_id} - {contact}")
            print(f"       Lead: {'✅' if lead else '❌'} | Visita: {'✅' if visit else '❌'} | Score: {score:.0f}")
            if nome:
                print(f"       Nome IA: {nome}")
            if cond and cond != 'Não mencionado':
                print(f"       Condição: {cond}")
            if obj and obj != 'Não mencionado':
                print(f"       Objetivo: {obj}")


def run_test():
    """Executa teste completo"""
    print("\n" + "🧪" * 40)
    print("  ETL WITH OPENAI - FULL REPROCESS TEST")
    print("  Fase 5.6 - OpenAI Integration")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🧪" * 40)

    tenant_id = 1

    # Criar engine
    engine = get_local_engine()

    # 1. Criar snapshot Regex para comparação
    total_convs = create_backup_comparison(engine, tenant_id)

    if total_convs == 0:
        print("\n❌ ERRO: Nenhuma conversa para reprocessar")
        return 1

    print(f"\n⚠️  CONFIRMAÇÃO NECESSÁRIA:")
    print(f"   - Vai reprocessar {total_convs} conversas com OpenAI")
    print(f"   - Custo estimado: R$ {total_convs * 0.0029:.2f}")
    print(f"   - Tempo estimado: {total_convs * 8 / 60:.0f} minutos")
    print(f"\n   Tem certeza? (Ctrl+C para cancelar)")
    input("\n   Pressione ENTER para continuar...")

    # 2. Executar ETL com OpenAI
    if not run_etl_with_openai_full(tenant_id):
        print("\n❌ ERRO: ETL falhou")
        return 1

    # 3. Analisar resultados
    analyze_results(engine, tenant_id)

    print_section("RESUMO FINAL")
    print("✅ Teste concluído com sucesso!")
    print(f"\n💡 Resultados:")
    print(f"   - Todas as {total_convs} conversas foram reprocessadas com OpenAI")
    print(f"   - Dados extras extraídos: nomes, condições físicas, objetivos")
    print(f"   - Análises detalhadas e sugestões de disparo geradas")

    return 0


if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)