#!/usr/bin/env python3
"""Script para investigar amostras de conversas de diferentes tenants"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Conectar direto ao banco (sem RLS)
conn = psycopg2.connect(
    host='localhost',
    database='geniai_analytics',
    user='johan_geniai',
    password='vlVMVM6UNz2yYSBlzodPjQvZh'
)

cur = conn.cursor(cursor_factory=RealDictCursor)

# Tenants para investigar (excluindo tenant 18 que já testamos)
tenants_to_check = [
    (16, 'Allp Fit JP Sul'),
    (1, 'AllpFit CrossFit'),
    (14, 'CDT Mossoró')
]

print("="*100)
print("INVESTIGAÇÃO DE CONVERSAS COMPILADAS - MÚLTIPLOS TENANTS")
print("="*100)

for tenant_id, tenant_name in tenants_to_check:
    print(f"\n{'='*100}")
    print(f"TENANT: {tenant_name} (ID: {tenant_id})")
    print(f"{'='*100}\n")

    # Buscar 1 conversa inativa com boa quantidade de mensagens
    cur.execute("""
        SELECT
            display_id,
            contact_name,
            contact_phone,
            message_compiled,
            contact_messages_count,
            mc_last_message_at
        FROM conversations_analytics
        WHERE tenant_id = %s
          AND is_lead = TRUE
          AND mc_last_message_at < NOW() - INTERVAL '24 hours'
          AND message_compiled IS NOT NULL
          AND contact_messages_count >= 3  -- Pelo menos 3 mensagens do contato
        ORDER BY contact_messages_count DESC
        LIMIT 1
    """, (tenant_id,))

    result = cur.fetchone()

    if not result:
        print(f"❌ Nenhuma conversa encontrada para {tenant_name}\n")
        continue

    print(f"📊 LEAD: {result['contact_name']} (#{result['display_id']})")
    print(f"📞 Telefone: {result['contact_phone']}")
    print(f"💬 Mensagens do contato: {result['contact_messages_count']}")
    print(f"⏰ Última msg: {result['mc_last_message_at']}")
    print()

    # Parse JSON
    messages = result['message_compiled']

    if not messages or len(messages) == 0:
        print("⚠️  Lista de mensagens vazia!\n")
        continue

    print(f"✅ Total de mensagens no JSON: {len(messages)}\n")

    # Analisar primeiras 5 mensagens
    print("📋 PRIMEIRAS 5 MENSAGENS:")
    print("-" * 100)

    contact_msgs = 0
    agent_msgs = 0
    bot_msgs = 0

    for idx, msg in enumerate(messages[:5], 1):
        sender = msg.get('sender', 'Unknown')
        text = msg.get('text') or ''
        msg_type = msg.get('message_type', None)

        # Contar por tipo
        if sender == 'Contact':
            contact_msgs += 1
            icon = '👤'
        elif sender == 'AgentBot':
            bot_msgs += 1
            icon = '🤖'
        elif sender in ['User', 'Agent']:
            agent_msgs += 1
            icon = '👨‍💼'
        else:
            icon = '❓'

        # Exibir mensagem
        print(f"{icon} Msg {idx} ({sender}):")
        print(f"   Tipo: {msg_type}")
        print(f"   Texto: {text[:200]}")
        print()

    # Resumo
    total_contact = sum(1 for m in messages if m.get('sender') == 'Contact')
    total_bot = sum(1 for m in messages if m.get('sender') == 'AgentBot')
    total_agent = sum(1 for m in messages if m.get('sender') in ['User', 'Agent'])

    print(f"📊 RESUMO COMPLETO:")
    print(f"   👤 Contato: {total_contact} mensagens")
    print(f"   🤖 Bot: {total_bot} mensagens")
    print(f"   👨‍💼 Agente: {total_agent} mensagens")
    print(f"   📋 Total: {len(messages)} mensagens")

    # Análise de qualidade
    print(f"\n🔍 ANÁLISE DE QUALIDADE:")

    # Verificar se tem mensagens do contato
    if total_contact == 0:
        print("   ❌ PROBLEMA: Nenhuma mensagem do contato!")
    elif total_contact < 2:
        print("   ⚠️  AVISO: Apenas 1 mensagem do contato (baixa qualidade)")
    else:
        print(f"   ✅ Bom: {total_contact} mensagens do contato")

    # Verificar se tem interação
    if total_bot == 0 and total_agent == 0:
        print("   ❌ PROBLEMA: Nenhuma resposta (bot ou agente)")
    else:
        print(f"   ✅ Tem interação: {total_bot} bot + {total_agent} agente")

    # Verificar comprimento das mensagens
    text_lengths = [len(m.get('text') or '') for m in messages if m.get('sender') == 'Contact']
    avg_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0

    if avg_length < 10:
        print(f"   ⚠️  AVISO: Mensagens muito curtas (média: {avg_length:.0f} caracteres)")
    else:
        print(f"   ✅ Mensagens com conteúdo (média: {avg_length:.0f} caracteres)")

    print()

print("\n" + "="*100)
print("FIM DA INVESTIGAÇÃO")
print("="*100)

cur.close()
conn.close()
