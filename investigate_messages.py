#!/usr/bin/env python3
"""Script para investigar conteúdo das conversas analisadas"""

import os
import sys
from pathlib import Path

# Adicionar src ao path
src_path = str(Path(__file__).parent / 'src')
sys.path.insert(0, src_path)

from multi_tenant.auth import get_database_engine
from sqlalchemy import text as sql_text
import json

def investigate_messages():
    """Investiga conteúdo das mensagens analisadas"""
    engine = get_database_engine()

    with engine.connect() as conn:
        # Buscar 1 conversa analisada
        result = conn.execute(sql_text("""
            SELECT
                display_id,
                contact_name,
                message_compiled,
                analise_ia,
                contact_messages_count
            FROM conversations_analytics
            WHERE tenant_id = 18
              AND analisado_em IS NOT NULL
            LIMIT 1
        """)).fetchone()

        if not result:
            print("❌ Nenhuma conversa analisada encontrada")
            return

        print(f"\n{'='*80}")
        print(f"LEAD: {result.contact_name} (ID: #{result.display_id})")
        print(f"{'='*80}")
        print(f"\n📊 Total de mensagens do contato: {result.contact_messages_count}")
        print(f"\n🤖 Análise IA:")
        print(f"   {result.analise_ia[:200]}...")

        print(f"\n{'='*80}")
        print("CONVERSA COMPILADA (message_compiled)")
        print(f"{'='*80}\n")

        # Parse JSON
        if not result.message_compiled:
            print("⚠️  message_compiled está NULL ou vazio!")
            return

        messages = json.loads(result.message_compiled) if isinstance(result.message_compiled, str) else result.message_compiled

        if not messages:
            print("⚠️  Lista de mensagens está vazia!")
            return

        print(f"✅ Total de mensagens no JSON: {len(messages)}\n")

        # Analisar mensagens
        contact_msgs = 0
        agent_msgs = 0
        bot_msgs = 0

        for idx, msg in enumerate(messages[:10], 1):  # Primeiras 10 mensagens
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')
            msg_type = msg.get('message_type', None)
            private = msg.get('private', False)

            # Contar por tipo
            if sender == 'Contact':
                contact_msgs += 1
            elif sender == 'AgentBot':
                bot_msgs += 1
            elif sender in ['User', 'Agent']:
                agent_msgs += 1

            # Exibir mensagem
            icon = '👤' if sender == 'Contact' else ('🤖' if sender == 'AgentBot' else '👨‍💼')
            print(f"{icon} Mensagem {idx} ({sender}):")
            print(f"   Type: {msg_type} | Private: {private}")
            print(f"   Text: {text[:150]}")
            print()

        print(f"{'='*80}")
        print("RESUMO:")
        print(f"{'='*80}")
        print(f"👤 Mensagens do Contato: {contact_msgs}")
        print(f"🤖 Mensagens do Bot: {bot_msgs}")
        print(f"👨‍💼 Mensagens do Agente: {agent_msgs}")
        print(f"📋 Total: {len(messages)}")

if __name__ == '__main__':
    investigate_messages()
