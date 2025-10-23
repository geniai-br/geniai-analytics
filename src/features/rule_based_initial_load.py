"""
Rule-Based Initial Load - Análise de Conversas com Regras Heurísticas
Analisa todas as conversas existentes usando regras (sem IA)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.rule_based_analyzer import analyze_and_save

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
    """Busca conversas que ainda não foram analisadas"""
    query = text("""
        SELECT
            ca.conversation_id,
            ca.message_compiled::text as message_compiled,
            ca.contact_name,
            ca.contact_messages_count
        FROM conversas_analytics ca
        LEFT JOIN conversas_analytics_ai ai ON ca.conversation_id = ai.conversation_id
        WHERE ai.id IS NULL  -- Ainda não analisada
          AND ca.contact_messages_count > 0
          AND LENGTH(ca.message_compiled::text) > 10
        ORDER BY ca.last_activity_at DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

        conversations = []
        for row in rows:
            conversations.append({
                'conversation_id': row[0],
                'message_compiled': row[1],
                'contact_name': row[2],
                'contact_messages_count': row[3]
            })

        return conversations


def main():
    """Função principal - carrega e analisa todas as conversas"""
    print("=" * 80)
    print("RULE-BASED INITIAL LOAD - Análise de Conversas com Regras Heurísticas")
    print("=" * 80)
    print()

    # Conectar ao banco
    engine = get_local_engine()

    # Buscar conversas para analisar
    print("[1/3] Buscando conversas para analisar...")
    conversations = get_conversations_to_analyze(engine)
    total = len(conversations)

    if total == 0:
        print("✅ Nenhuma conversa nova para analisar!")
        return

    print(f"📊 Encontradas {total} conversas para analisar\n")

    # Analisar conversas
    print("[2/3] Analisando conversas com regras heurísticas...")
    print("-" * 80)

    success_count = 0
    error_count = 0

    for i, conv in enumerate(conversations, 1):
        try:
            print(f"\n[{i}/{total}] Analisando conversa {conv['conversation_id']} ({conv['contact_name']})...")

            # Analisar e salvar
            result = analyze_and_save(
                conversation_id=conv['conversation_id'],
                conversa_compilada=conv['message_compiled'],
                contact_name=conv['contact_name'],
                message_count=conv['contact_messages_count']
            )

            if result:
                success_count += 1
                print(f"✅ [{i}/{total}] Conversa {conv['conversation_id']} analisada com sucesso!")
            else:
                error_count += 1
                print(f"⚠️  [{i}/{total}] Conversa {conv['conversation_id']} pulada (muito curta)")

        except Exception as e:
            error_count += 1
            print(f"❌ [{i}/{total}] Erro ao analisar conversa {conv['conversation_id']}: {e}")

    # Resumo final
    print("\n" + "=" * 80)
    print("[3/3] RESUMO FINAL")
    print("=" * 80)
    print(f"Total de conversas: {total}")
    print(f"✅ Analisadas com sucesso: {success_count}")
    print(f"⚠️  Puladas/Erros: {error_count}")
    print(f"Taxa de sucesso: {(success_count/total*100):.1f}%")
    print("=" * 80)
    print("\n✅ Processo concluído!")


if __name__ == "__main__":
    main()
