"""
Script de Teste: Validar Análise Melhorada com Caso Samuel Rodrigues
=================================================================

Testa a nova lógica de análise de IA que detecta conversas resolvidas
e não gera remarketing desnecessário.

Autor: Isaac (via Claude Code)
Data: 2025-11-19
"""

import os
import sys
import json

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.multi_tenant.etl_v4.analyzers.openai_analyzer import OpenAIAnalyzer
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# ===================================================================
# CONVERSA DO SAMUEL RODRIGUES (CASO REAL)
# ===================================================================
samuel_messages = [
    {
        "text": "superadminallpfitjpsul self-assigned this conversation",
        "sender": None,
        "message_type": 2
    },
    {
        "text": "Boa tarde, gostaria de agendar um treino experimental",
        "sender": "Contact",
        "sent_at": "2025-11-12T16:47:36.860186"
    },
    {
        "text": "Conversation was reopened by Automation System",
        "sender": None,
        "message_type": 2
    },
    {
        "text": "‎Allp Fit Academia agradece seu contato. Como podemos ajudar? \n\nPara um atendimento mais rápido, envie por escrito o que deseja e assim que possível já te respondemos! 🚀",
        "sender": "User",
        "sent_at": "2025-11-12T16:47:38.163127"
    },
    {
        "text": "Olá, boa tarde! Me chamo Amanda aqui da Allp Fit. Tudo bem?",
        "sender": "User",
        "sent_at": "2025-11-12T16:48:33.609659"
    },
    {
        "text": "Me informa seu nome completo, data e hora. De menor?",
        "sender": "User",
        "sent_at": "2025-11-12T16:48:48.369945"
    },
    {
        "text": "Samuel Rodrigues Leandro",
        "sender": "Contact",
        "sent_at": "2025-11-12T16:49:04.269379"
    },
    {
        "text": "Pode ser hoje ?",
        "sender": "Contact",
        "sent_at": "2025-11-12T16:49:09.675842"
    },
    {
        "text": "Sou de maior",
        "sender": "Contact",
        "sent_at": "2025-11-12T16:49:14.822978"
    },
    {
        "text": "Qual horário?",
        "sender": "User",
        "sent_at": "2025-11-12T16:49:50.507314"
    },
    {
        "text": "17:00",
        "sender": "Contact",
        "sent_at": "2025-11-12T16:50:12.273799"
    },
    {
        "text": "agendado ✅",
        "sender": "User",
        "sent_at": "2025-11-12T17:29:52.343547"
    }
]

# ===================================================================
# FORMATAR CONVERSA PARA ANÁLISE
# ===================================================================
def format_conversation(messages):
    """Formata mensagens para texto legível"""
    lines = []
    for msg in messages:
        if msg.get('message_type') in [2, 3]:
            continue  # Pular mensagens do sistema

        sender = msg.get('sender', 'Unknown')
        text = msg.get('text', '')

        if sender == 'Contact':
            lines.append(f"Lead: {text}")
        elif sender == 'User':
            lines.append(f"Atendente: {text}")

    return '\n'.join(lines)


def main():
    print("=" * 80)
    print("TESTE: Análise Melhorada - Caso Samuel Rodrigues")
    print("=" * 80)
    print()

    # Obter API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não encontrada no .env")
        return

    # Formatar conversa
    conversation_text = format_conversation(samuel_messages)

    print("📋 CONVERSA:")
    print("-" * 80)
    print(conversation_text)
    print("-" * 80)
    print()

    # Inicializar analyzer
    print("🤖 Inicializando OpenAI Analyzer...")
    analyzer = OpenAIAnalyzer(tenant_id=16, api_key=api_key, model='gpt-4o-mini')

    # Analisar
    print("🔄 Analisando conversa com nova lógica...")
    print()

    result = analyzer.analyze_conversation(
        message_text=conversation_text,
        contact_name="Samuel Rodrigues Leandro",
        message_count=8
    )

    # Mostrar resultados
    print("=" * 80)
    print("✅ RESULTADOS DA ANÁLISE")
    print("=" * 80)
    print()

    print("📊 CAMPOS PADRÃO:")
    print(f"  • is_lead: {result['is_lead']}")
    print(f"  • visit_scheduled: {result['visit_scheduled']}")
    print(f"  • crm_converted: {result['crm_converted']}")
    print(f"  • ai_probability_score: {result['ai_probability_score']}")
    print(f"  • ai_probability_label: {result['ai_probability_label']}")
    print()

    print("🆕 NOVOS CAMPOS:")
    print(f"  • status_resolucao: {result.get('_status_resolucao', 'N/A')}")
    print(f"  • precisa_remarketing: {result.get('_precisa_remarketing', 'N/A')}")
    print(f"  • nivel_interesse: {result.get('_nivel_interesse', 'N/A')}")
    print(f"  • motivo_remarketing: {result.get('_motivo_remarketing', 'N/A')}")
    print()

    print("📝 ANÁLISE IA:")
    print("-" * 80)
    print(result.get('analise_ia', 'Nenhuma'))
    print("-" * 80)
    print()

    print("💬 SUGESTÃO DE DISPARO:")
    print("-" * 80)
    sugestao = result.get('sugestao_disparo', '')
    if sugestao:
        print(sugestao)
    else:
        print("✅ NENHUMA - Conversa resolvida, não precisa remarketing!")
    print("-" * 80)
    print()

    # Validação
    print("=" * 80)
    print("🔍 VALIDAÇÃO DO TESTE")
    print("=" * 80)
    print()

    precisa_remarketing = result.get('_precisa_remarketing', True)
    status_resolucao = result.get('_status_resolucao', '')

    if not precisa_remarketing and status_resolucao == 'resolvida':
        print("✅ SUCESSO! A IA corretamente identificou:")
        print("   - Conversa foi RESOLVIDA (agendamento confirmado)")
        print("   - NÃO precisa remarketing")
        print("   - Sugestão de disparo foi bloqueada")
        print()
        print("🎉 O problema foi RESOLVIDO! Não enviará mensagem desnecessária.")
    else:
        print("⚠️  ATENÇÃO! Resultado inesperado:")
        print(f"   - precisa_remarketing: {precisa_remarketing}")
        print(f"   - status_resolucao: {status_resolucao}")
        print()
        print("   Esperado: precisa_remarketing=False, status='resolvida'")

    print()
    print("=" * 80)


if __name__ == '__main__':
    main()