"""
Script para inspecionar a view atual e entender sua estrutura
"""
import sys
import os
import json
import pandas as pd
from sqlalchemy import create_engine, inspect

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.shared.config import Config


def inspect_view():
    """Inspeciona a view atual detalhadamente"""

    print("=" * 80)
    print("INSPEÇÃO DETALHADA DA VIEW: vw_conversas_por_lead")
    print("=" * 80)

    try:
        conn_str = Config.get_source_connection_string()
        engine = create_engine(conn_str)

        # 1. Colunas e tipos
        print("\n1. ESTRUTURA DE COLUNAS")
        print("-" * 80)

        columns_query = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{Config.SOURCE_DB_VIEW}'
            ORDER BY ordinal_position
        """

        columns_df = pd.read_sql(columns_query, engine)
        print(columns_df.to_string(index=False))

        # 2. Amostra de dados com análise de message_compiled
        print("\n\n2. ANÁLISE DETALHADA DO message_compiled")
        print("-" * 80)

        sample_query = f"""
            SELECT *
            FROM {Config.SOURCE_DB_VIEW}
            WHERE message_compiled IS NOT NULL
            ORDER BY t_messages DESC
            LIMIT 3
        """

        samples_df = pd.read_sql(sample_query, engine)

        for idx, row in samples_df.iterrows():
            print(f"\n--- CONVERSA {idx + 1} (ID: {row['conversation_id']}) ---")
            print(f"Client Sender ID: {row['client_sender_id']}")
            print(f"Inbox ID: {row['inbox_id']}")
            print(f"Client Phone: {row['client_phone']}")
            print(f"Total Messages: {row['t_messages']}")

            # Parse JSON
            try:
                messages = row['message_compiled']
                if isinstance(messages, str):
                    messages = json.loads(messages)

                if isinstance(messages, list) and len(messages) > 0:
                    print(f"\nTotal de mensagens no JSON: {len(messages)}")

                    # Analisar primeira mensagem
                    first = messages[0]
                    print(f"\nESTRUTURA DA PRIMEIRA MENSAGEM:")
                    print(f"  Campos disponíveis: {list(first.keys())}")

                    # Mostrar todos os campos da primeira mensagem
                    for key, value in first.items():
                        val_str = str(value)
                        if len(val_str) > 80:
                            val_str = val_str[:80] + "..."
                        print(f"  - {key}: {val_str}")

                    # Analisar tipos de sender
                    senders = {}
                    for msg in messages:
                        sender = msg.get('sender', 'Unknown')
                        senders[sender] = senders.get(sender, 0) + 1

                    print(f"\nDISTRIBUIÇÃO DE MENSAGENS POR TIPO:")
                    for sender, count in senders.items():
                        print(f"  - {sender}: {count} mensagens")

                    # Verificar se tem timestamps
                    if 'sent_at' in first or 'created_at' in first:
                        print(f"\n✓ Mensagens TÊM timestamps!")
                        ts_field = 'sent_at' if 'sent_at' in first else 'created_at'
                        print(f"  Campo de timestamp: {ts_field}")
                        print(f"  Primeiro: {first.get(ts_field)}")
                        print(f"  Último: {messages[-1].get(ts_field)}")
                    else:
                        print(f"\n✗ Mensagens NÃO têm timestamps")

            except Exception as e:
                print(f"Erro ao parsear JSON: {e}")

        # 3. Estatísticas
        print("\n\n3. ESTATÍSTICAS GERAIS")
        print("-" * 80)

        stats_query = f"""
            SELECT
                COUNT(*) as total_conversas,
                COUNT(DISTINCT client_sender_id) as clientes_unicos,
                COUNT(DISTINCT inbox_id) as inboxes_unicos,
                AVG(t_messages) as media_msgs,
                MIN(t_messages) as min_msgs,
                MAX(t_messages) as max_msgs,
                COUNT(CASE WHEN client_phone IS NOT NULL THEN 1 END) as com_telefone,
                COUNT(CASE WHEN client_sender_id IS NOT NULL THEN 1 END) as com_sender_id
            FROM {Config.SOURCE_DB_VIEW}
        """

        stats_df = pd.read_sql(stats_query, engine)
        stats = stats_df.iloc[0]

        print(f"Total de conversas: {stats['total_conversas']}")
        print(f"Clientes únicos: {stats['clientes_unicos']}")
        print(f"Inboxes únicos: {stats['inboxes_unicos']}")
        print(f"Média de mensagens: {stats['media_msgs']:.2f}")
        print(f"Range de mensagens: {stats['min_msgs']} - {stats['max_msgs']}")
        print(f"Conversas com telefone: {stats['com_telefone']} ({stats['com_telefone']/stats['total_conversas']*100:.1f}%)")
        print(f"Conversas com sender_id: {stats['com_sender_id']} ({stats['com_sender_id']/stats['total_conversas']*100:.1f}%)")

        # 4. Valores nulos
        print("\n\n4. ANÁLISE DE VALORES NULOS")
        print("-" * 80)

        null_query = f"""
            SELECT
                COUNT(*) as total,
                COUNT(conversation_id) as conv_id_count,
                COUNT(message_compiled) as msg_compiled_count,
                COUNT(client_sender_id) as client_sender_count,
                COUNT(inbox_id) as inbox_id_count,
                COUNT(client_phone) as phone_count,
                COUNT(t_messages) as t_msg_count
            FROM {Config.SOURCE_DB_VIEW}
        """

        null_df = pd.read_sql(null_query, engine)
        null_data = null_df.iloc[0]
        total = null_data['total']

        for col in columns_df['column_name']:
            col_count = null_data.get(f"{col.replace('conversation_id', 'conv_id').replace('message_compiled', 'msg_compiled').replace('client_sender_id', 'client_sender').replace('client_phone', 'phone').replace('t_messages', 't_msg')}_count", total)
            null_count = total - col_count
            null_pct = (null_count / total * 100) if total > 0 else 0
            print(f"  {col:25} - Nulos: {null_count:5} ({null_pct:5.1f}%)")

        engine.dispose()

        print("\n" + "=" * 80)
        print("✓ INSPEÇÃO CONCLUÍDA")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    inspect_view()
