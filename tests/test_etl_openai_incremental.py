"""
Test ETL with OpenAI - Incremental Processing
==============================================

Processa APENAS as conversas que ainda NÃO foram analisadas pela OpenAI.

Execução:
    cd /home/tester/projetos/allpfit-analytics
    source venv/bin/activate
    OPENAI_API_KEY="sk-..." python tests/test_etl_openai_incremental.py
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


def check_pending_conversations(engine, tenant_id=1):
    """Verifica quantas conversas ainda precisam ser analisadas"""
    print_section("Verificando Conversas Pendentes")

    query = text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE analise_ia != '' AND analise_ia IS NOT NULL) as analisadas,
            COUNT(*) FILTER (WHERE analise_ia = '' OR analise_ia IS NULL) as pendentes
        FROM conversations_analytics
        WHERE tenant_id = :tenant_id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"tenant_id": tenant_id}).fetchone()

        total = result[0]
        analisadas = result[1]
        pendentes = result[2]

        print(f"📊 Total conversas: {total}")
        print(f"✅ Já analisadas: {analisadas} ({analisadas/total*100:.1f}%)")
        print(f"⏳ Pendentes: {pendentes} ({pendentes/total*100:.1f}%)")

        return pendentes


def run_incremental_openai():
    """Executa ETL incremental com OpenAI apenas para conversas não analisadas"""

    print_section("ETL OpenAI - Processamento Incremental")
    print(f"🕐 Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não configurada!")
        print("\nConfigure com:")
        print('export OPENAI_API_KEY="sk-..."')
        sys.exit(1)

    print(f"✅ OpenAI API Key configurada ({api_key[:10]}...)")

    # Criar engine
    engine = get_local_engine()
    print("✅ Conexão com banco estabelecida")

    # Verificar conversas pendentes
    pendentes = check_pending_conversations(engine, tenant_id=1)

    if pendentes == 0:
        print("\n✅ Todas as conversas já foram analisadas!")
        return

    print(f"\n🚀 Iniciando processamento de {pendentes} conversas pendentes...")

    # Configurar tenant para usar OpenAI
    tenant_config = {
        'tenant_id': 1,
        'tenant_name': 'AllpFit',
        'use_openai': True,  # FORÇAR OpenAI
        'openai_api_key': api_key,
        'openai_model': 'gpt-4o-mini'
    }

    # Executar ETL
    pipeline = ETLPipeline(
        local_engine=engine,
        remote_engine=None  # Usa variável de ambiente
    )

    try:
        # Executar full sync para o tenant (vai pegar TODAS, mas só analisar as sem analise_ia)
        result = pipeline.run_for_tenant(
            tenant_id=1,
            tenant_config=tenant_config,
            load_type='full',
            chunk_size=100
        )

        print_section("Resultado do ETL")
        print(f"✅ Status: {result['status']}")
        print(f"📊 Records updated: {result.get('records_updated', 0)}")
        print(f"📊 Records inserted: {result.get('records_inserted', 0)}")

        # Custos OpenAI
        if 'openai_stats' in result:
            stats = result['openai_stats']
            print("\n💰 Custos OpenAI:")
            print(f"   API Calls: {stats.get('api_calls', 0)}")
            print(f"   Total Tokens: {stats.get('total_tokens', 0)}")
            print(f"   Custo (BRL): R$ {stats.get('cost_brl', 0):.4f}")

        print(f"\n🕐 Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_incremental_openai()