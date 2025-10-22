"""
AI Initial Load - Primeira Carga de Análises
Analisa TODAS as conversas existentes que ainda não foram analisadas pela IA
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from ai_analyzer import analyze_and_save
import time

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco local
LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST')
LOCAL_DB_PORT = os.getenv('LOCAL_DB_PORT')
LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME')
LOCAL_DB_USER = os.getenv('LOCAL_DB_USER')
LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD')


def get_local_engine():
    """Cria engine para banco local"""
    from urllib.parse import quote_plus
    password_encoded = quote_plus(LOCAL_DB_PASSWORD)
    connection_string = f"postgresql://{LOCAL_DB_USER}:{password_encoded}@{LOCAL_DB_HOST}:{LOCAL_DB_PORT}/{LOCAL_DB_NAME}"
    return create_engine(connection_string)


def get_conversations_to_analyze(engine):
    """
    Busca conversas que ainda não foram analisadas pela IA

    Returns:
        Lista de dicts com conversation_id, message_compiled, contact_name
    """
    query = text("""
        SELECT
            ca.conversation_id,
            ca.message_compiled::text as message_compiled,
            ca.contact_name,
            ca.contact_messages_count
        FROM conversas_analytics ca
        LEFT JOIN conversas_analytics_ai ai ON ca.conversation_id = ai.conversation_id
        WHERE ai.id IS NULL  -- Ainda não analisada
          AND ca.contact_messages_count > 0  -- Apenas leads que engajaram
          AND ca.message_compiled IS NOT NULL
          AND LENGTH(ca.message_compiled::text) > 10
        ORDER BY ca.last_activity_at DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        conversations = []
        for row in result:
            conversations.append({
                'conversation_id': row[0],
                'message_compiled': row[1],
                'contact_name': row[2],
                'contact_messages_count': row[3]
            })

    return conversations


def run_initial_analysis(batch_size=10, delay_between_batches=2):
    """
    Executa análise inicial de todas as conversas

    Args:
        batch_size: Número de conversas por lote (para não estourar rate limit da OpenAI)
        delay_between_batches: Segundos de delay entre lotes
    """
    print("=" * 80)
    print("ANÁLISE INICIAL DE CONVERSAS COM IA")
    print("=" * 80)

    engine = get_local_engine()

    # Buscar conversas não analisadas
    print("\n[1/3] Buscando conversas para analisar...")
    conversations = get_conversations_to_analyze(engine)

    if not conversations:
        print("✅ Nenhuma conversa pendente de análise!")
        return

    total = len(conversations)
    print(f"📊 Total de conversas encontradas: {total}")
    print(f"⚙️  Processamento em lotes de {batch_size}")

    # Processar em lotes
    print(f"\n[2/3] Iniciando análise com OpenAI...")
    success_count = 0
    error_count = 0

    for i, conv in enumerate(conversations, 1):
        print(f"\n--- Conversa {i}/{total} ---")

        # Analisar e salvar
        success = analyze_and_save(
            conversation_id=conv['conversation_id'],
            conversa_compilada=conv['message_compiled'],
            contact_name=conv['contact_name']
        )

        if success:
            success_count += 1
        else:
            error_count += 1

        # Delay entre chamadas (rate limiting)
        if i % batch_size == 0 and i < total:
            print(f"\n⏳ Pausa de {delay_between_batches}s entre lotes...")
            time.sleep(delay_between_batches)

    # Resumo final
    print("\n" + "=" * 80)
    print("[3/3] RESUMO DA ANÁLISE INICIAL")
    print("=" * 80)
    print(f"✅ Sucesso: {success_count}/{total}")
    print(f"❌ Erros: {error_count}/{total}")
    print(f"📈 Taxa de sucesso: {(success_count/total*100):.1f}%")

    if success_count > 0:
        # Mostrar estatísticas das análises
        stats_query = text("""
            SELECT
                probabilidade_conversao,
                COUNT(*) as total
            FROM conversas_analytics_ai
            GROUP BY probabilidade_conversao
            ORDER BY probabilidade_conversao DESC
        """)

        with engine.connect() as conn:
            result = conn.execute(stats_query)
            print("\n📊 DISTRIBUIÇÃO DE PROBABILIDADE DE CONVERSÃO:")
            for row in result:
                prob = row[0]
                count = row[1]
                bar = "█" * int(count / 2)  # Barra visual
                print(f"   {prob}/5: {count:3d} leads {bar}")

    print("\n✅ Análise inicial concluída!")


if __name__ == "__main__":
    try:
        run_initial_analysis(batch_size=10, delay_between_batches=2)
    except KeyboardInterrupt:
        print("\n\n⚠️  Análise interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        raise
