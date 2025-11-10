"""
Test ETL with OpenAI - Subset
==============================

Testa ETL com OpenAI processando um subset de conversas (últimas 50).

Execução:
    cd /home/tester/projetos/allpfit-analytics
    source venv/bin/activate
    OPENAI_API_KEY="sk-..." python tests/test_etl_openai_subset.py
"""

import sys
import os
from datetime import datetime, timedelta
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


def backup_and_prepare_subset(engine, tenant_id=1, limit=50):
    """
    Cria backup das conversas atuais e prepara subset para teste.
    """
    print_section("Preparando Subset de Teste")

    with engine.begin() as conn:
        # 1. Criar tabela de backup se não existir
        print("📋 Criando backup das conversas atuais...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations_analytics_backup AS
            SELECT * FROM conversations_analytics WHERE 1=0;
        """))

        # 2. Fazer backup das últimas N conversas (as que vamos reprocessar)
        result = conn.execute(text("""
            DELETE FROM conversations_analytics_backup
            WHERE tenant_id = :tenant_id;

            INSERT INTO conversations_analytics_backup
            SELECT * FROM conversations_analytics
            WHERE tenant_id = :tenant_id
            ORDER BY conversation_created_at DESC
            LIMIT :limit;

            SELECT COUNT(*) FROM conversations_analytics_backup WHERE tenant_id = :tenant_id;
        """), {'tenant_id': tenant_id, 'limit': limit})

        backup_count = result.fetchone()[0]
        print(f"✅ Backup criado: {backup_count} conversas")

        # 3. Deletar essas conversas para reprocessar
        print(f"\n🗑️  Deletando {limit} conversas mais recentes para reprocessar...")
        result = conn.execute(text("""
            DELETE FROM conversations_analytics
            WHERE tenant_id = :tenant_id
            AND conversation_id IN (
                SELECT conversation_id
                FROM conversations_analytics_backup
                WHERE tenant_id = :tenant_id
            );

            SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = :tenant_id;
        """), {'tenant_id': tenant_id})

        remaining = result.fetchone()[0]
        print(f"✅ {limit} conversas deletadas. Restam {remaining} no banco.")

        # 4. Ajustar watermark para forçar extração dessas conversas
        print(f"\n⏰ Ajustando watermark para reprocessar...")

        # Pegar a data mais antiga do backup
        result = conn.execute(text("""
            SELECT MIN(conversation_created_at) - INTERVAL '1 hour'
            FROM conversations_analytics_backup
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant_id})

        new_watermark = result.fetchone()[0]

        # Atualizar último watermark
        conn.execute(text("""
            UPDATE etl_control
            SET watermark_end = :new_watermark
            WHERE tenant_id = :tenant_id
            AND id = (
                SELECT id FROM etl_control
                WHERE tenant_id = :tenant_id
                ORDER BY started_at DESC
                LIMIT 1
            )
        """), {'tenant_id': tenant_id, 'new_watermark': new_watermark})

        print(f"✅ Watermark ajustado para: {new_watermark}")

    return backup_count


def run_etl_with_openai(tenant_id=1):
    """Executa ETL com OpenAI habilitado"""
    print_section("Executando ETL com OpenAI")

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

    # Executar ETL
    print(f"\n🚀 Executando ETL com OpenAI GPT-4o-mini...")
    print("   (Isso vai levar alguns minutos...)\n")

    start_time = datetime.now()

    try:
        stats = pipeline.run_for_tenant(
            tenant_id=tenant_id,
            force_full=False,  # Incremental
            chunk_size=50,     # Processar em chunks menores
            triggered_by='test_openai'
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
        print(f"   Tempo total: {elapsed:.1f}s")
        print(f"   Velocidade: {stats['records_extracted']/elapsed:.1f} conv/s")

        return True

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ ERRO ao executar ETL ({elapsed:.1f}s): {str(e)}")
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
                openai_api_calls,
                openai_total_tokens,
                openai_cost_brl
            FROM etl_control
            WHERE tenant_id = :tenant_id
            ORDER BY started_at DESC
            LIMIT 1
        """), {'tenant_id': tenant_id}).fetchone()

        if result:
            exec_id, started, duration, extracted, api_calls, tokens, cost = result

            print(f"📋 Última execução ETL (ID: {exec_id}):")
            print(f"   Data: {started}")
            print(f"   Duração: {duration}s")
            print(f"   Conversas processadas: {extracted}")

            if api_calls and api_calls > 0:
                print(f"\n💰 Custos OpenAI:")
                print(f"   API calls: {api_calls}")
                print(f"   Total tokens: {tokens}")
                print(f"   Custo: R$ {cost:.4f}")
                print(f"   Custo/conversa: R$ {cost/extracted:.4f}" if extracted > 0 else "   N/A")

        # Comparar resultados backup (Regex) vs novos (OpenAI)
        print(f"\n📊 Comparação Regex vs OpenAI:")

        # Stats do backup (Regex)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_lead THEN 1 ELSE 0 END) as leads,
                SUM(CASE WHEN visit_scheduled THEN 1 ELSE 0 END) as visits,
                SUM(CASE WHEN crm_converted THEN 1 ELSE 0 END) as conversions,
                ROUND(AVG(ai_probability_score), 2) as avg_score
            FROM conversations_analytics_backup
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant_id}).fetchone()

        regex_total, regex_leads, regex_visits, regex_conv, regex_score = result

        # Stats dos novos (OpenAI)
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
            AND conversation_id IN (
                SELECT conversation_id FROM conversations_analytics_backup WHERE tenant_id = :tenant_id
            )
        """), {'tenant_id': tenant_id}).fetchone()

        openai_total, openai_leads, openai_visits, openai_conv, openai_score, names, conditions, objectives = result

        print(f"\n{'Métrica':<25} {'Regex':<15} {'OpenAI':<15} {'Diferença'}")
        print("-" * 80)
        print(f"{'Total conversas':<25} {regex_total:<15} {openai_total:<15}")
        print(f"{'Leads detectados':<25} {regex_leads:<15} {openai_leads:<15} {'+' if openai_leads > regex_leads else ''}{openai_leads - regex_leads}")
        print(f"{'Visitas agendadas':<25} {regex_visits:<15} {openai_visits:<15} {'+' if openai_visits > regex_visits else ''}{openai_visits - regex_visits}")
        print(f"{'Conversões CRM':<25} {regex_conv:<15} {openai_conv:<15} {'+' if openai_conv > regex_conv else ''}{openai_conv - regex_conv}")
        print(f"{'Score médio':<25} {regex_score:<15} {openai_score:<15} {'+' if openai_score > regex_score else ''}{openai_score - regex_score:.2f}")

        print(f"\n✨ Dados extras (apenas OpenAI):")
        print(f"   Nomes extraídos: {names}/{openai_total} ({names/openai_total*100:.0f}%)" if openai_total > 0 else "   N/A")
        print(f"   Condição física identificada: {conditions}/{openai_total} ({conditions/openai_total*100:.0f}%)" if openai_total > 0 else "   N/A")
        print(f"   Objetivo identificado: {objectives}/{openai_total} ({objectives/openai_total*100:.0f}%)" if openai_total > 0 else "   N/A")

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
            AND conversation_id IN (
                SELECT conversation_id FROM conversations_analytics_backup WHERE tenant_id = :tenant_id
            )
            ORDER BY conversation_created_at DESC
            LIMIT 5
        """), {'tenant_id': tenant_id})

        for i, row in enumerate(result, 1):
            conv_id, contact, lead, visit, score, nome, cond, obj = row
            print(f"\n   [{i}] Conv {conv_id} - {contact}")
            print(f"       Lead: {'✅' if lead else '❌'} | Visita: {'✅' if visit else '❌'} | Score: {score:.0f}")
            if nome:
                print(f"       Nome: {nome}")
            if cond and cond != 'Não mencionado':
                print(f"       Condição: {cond}")
            if obj and obj != 'Não mencionado':
                print(f"       Objetivo: {obj}")


def run_test():
    """Executa teste completo"""
    print("\n" + "🧪" * 40)
    print("  ETL WITH OPENAI - SUBSET TEST")
    print("  Fase 5.6 - OpenAI Integration")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🧪" * 40)

    tenant_id = 1
    subset_size = 50

    # Criar engine
    engine = get_local_engine()

    # 1. Preparar subset
    backup_count = backup_and_prepare_subset(engine, tenant_id, subset_size)

    if backup_count == 0:
        print("\n❌ ERRO: Nenhuma conversa para testar")
        return 1

    # 2. Executar ETL com OpenAI
    if not run_etl_with_openai(tenant_id):
        print("\n❌ ERRO: ETL falhou")
        return 1

    # 3. Analisar resultados
    analyze_results(engine, tenant_id)

    print_section("RESUMO FINAL")
    print("✅ Teste concluído com sucesso!")
    print(f"\n💡 Próximos passos:")
    print(f"   1. Revisar resultados acima")
    print(f"   2. Se satisfeito, processar todas as 1.281 conversas")
    print(f"   3. Ou restaurar backup e ajustar configurações")

    return 0


if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)