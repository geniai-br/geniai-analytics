"""
Script: Reanalisar Conversa Específica com Novo Sistema
========================================================

Permite reanalisar uma conversa específica usando o novo sistema
de remarketing inteligente.

Uso:
    python scripts/maintenance/reanalyze_conversation.py <conversation_id>

Autor: Isaac (via Claude Code)
Data: 2025-11-19
"""

import os
import sys
import json
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.multi_tenant.etl_v4.analyzers.openai_analyzer import OpenAIAnalyzer
import psycopg2
from psycopg2.extras import RealDictCursor

# Carregar variáveis de ambiente
load_dotenv()

def get_db_connection():
    """Conecta ao banco de dados"""
    return psycopg2.connect(
        host='localhost',
        database='geniai_analytics',
        user='johan_geniai',
        password='vlVMVM6UNz2yYSBlzodPjQvZh'
    )

def fetch_conversation(conversation_id: int):
    """Busca dados da conversa no banco"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    tenant_id,
                    conversation_id,
                    contact_name,
                    contact_phone,
                    message_compiled,
                    contact_messages_count,
                    analise_ia as analise_antiga,
                    sugestao_disparo as sugestao_antiga,
                    precisa_remarketing as remarketing_antigo,
                    status_resolucao as status_antigo,
                    nivel_interesse as interesse_antigo
                FROM conversations_analytics
                WHERE conversation_id = %s
            """, (conversation_id,))

            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()

def update_conversation(conversation_id: int, analysis: dict):
    """Atualiza conversa no banco com nova análise"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Preparar dados JSONB
            dados_extraidos = json.dumps({
                'status_resolucao': analysis.get('_status_resolucao', ''),
                'precisa_remarketing': analysis.get('_precisa_remarketing', True),
                'nivel_interesse': analysis.get('_nivel_interesse', ''),
                'motivo_remarketing': analysis.get('_motivo_remarketing', ''),
                'objecoes_identificadas': analysis.get('_objecoes', []),
                'sinais_positivos': analysis.get('_sinais_positivos', []),
            })

            cur.execute("""
                UPDATE conversations_analytics
                SET
                    analise_ia = %s,
                    sugestao_disparo = %s,
                    precisa_remarketing = %s,
                    status_resolucao = %s,
                    nivel_interesse = %s,
                    ai_probability_score = %s,
                    ai_probability_label = %s,
                    is_lead = %s,
                    visit_scheduled = %s,
                    dados_extraidos_ia = %s::jsonb,
                    etl_updated_at = NOW()
                WHERE conversation_id = %s
            """, (
                analysis.get('analise_ia', ''),
                analysis.get('sugestao_disparo', ''),
                analysis.get('_precisa_remarketing', True),
                analysis.get('_status_resolucao', None),
                analysis.get('_nivel_interesse', None),
                analysis.get('ai_probability_score', 0.0),
                analysis.get('ai_probability_label', 'N/A'),
                analysis.get('is_lead', False),
                analysis.get('visit_scheduled', False),
                dados_extraidos,
                conversation_id
            ))

            conn.commit()
            print(f"✅ Conversa {conversation_id} atualizada no banco!")
    finally:
        conn.close()

def format_conversation(message_compiled):
    """Formata mensagens para análise"""
    if isinstance(message_compiled, str):
        messages = json.loads(message_compiled)
    else:
        messages = message_compiled

    lines = []
    for msg in messages:
        if msg.get('message_type') in [2, 3]:
            continue

        sender = msg.get('sender', 'Unknown')
        text = msg.get('text', '')

        if sender == 'Contact':
            lines.append(f"Lead: {text}")
        elif sender in ['User', 'Agent']:
            lines.append(f"Atendente: {text}")

    return '\n'.join(lines)

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python scripts/maintenance/reanalyze_conversation.py <conversation_id>")
        sys.exit(1)

    conversation_id = int(sys.argv[1])

    print("=" * 80)
    print(f"🔄 REANALISANDO CONVERSA {conversation_id}")
    print("=" * 80)
    print()

    # Buscar conversa
    print("📥 Buscando dados da conversa...")
    conv = fetch_conversation(conversation_id)

    if not conv:
        print(f"❌ Conversa {conversation_id} não encontrada!")
        sys.exit(1)

    print(f"✅ Conversa encontrada:")
    print(f"   - Tenant: {conv['tenant_id']}")
    print(f"   - Contato: {conv['contact_name']} ({conv['contact_phone']})")
    print(f"   - Mensagens: {conv['contact_messages_count']}")
    print()

    # Mostrar dados antigos
    print("📊 DADOS ANTIGOS:")
    print(f"   - Status: {conv.get('status_antigo', 'NULL')}")
    print(f"   - Precisa Remarketing: {conv.get('remarketing_antigo', 'NULL')}")
    print(f"   - Nível Interesse: {conv.get('interesse_antigo', 'NULL')}")
    print()

    # Obter API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY não encontrada no .env")
        sys.exit(1)

    # Inicializar analyzer
    print("🤖 Inicializando OpenAI Analyzer...")
    analyzer = OpenAIAnalyzer(
        tenant_id=conv['tenant_id'],
        api_key=api_key,
        model='gpt-4o-mini'
    )

    # Formatar conversa
    conversation_text = format_conversation(conv['message_compiled'])

    # Analisar
    print("🔄 Analisando conversa com novo sistema...")
    print()

    result = analyzer.analyze_conversation(
        message_text=conversation_text,
        contact_name=conv['contact_name'],
        message_count=conv['contact_messages_count']
    )

    # Mostrar resultados
    print("=" * 80)
    print("✅ NOVA ANÁLISE CONCLUÍDA")
    print("=" * 80)
    print()

    print("📊 NOVOS DADOS:")
    print(f"   - Status: {result.get('_status_resolucao', 'N/A')}")
    print(f"   - Precisa Remarketing: {result.get('_precisa_remarketing', 'N/A')}")
    print(f"   - Nível Interesse: {result.get('_nivel_interesse', 'N/A')}")
    print(f"   - Score: {result.get('ai_probability_score', 0)}")
    print(f"   - Motivo: {result.get('_motivo_remarketing', 'N/A')}")
    print()

    print("💬 SUGESTÃO DE DISPARO:")
    sugestao = result.get('sugestao_disparo', '')
    if sugestao:
        print(f"   {sugestao}")
    else:
        print("   ✅ NENHUMA (conversa resolvida)")
    print()

    # Confirmar atualização
    resposta = input("💾 Salvar nova análise no banco? (s/N): ")

    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        print("💾 Salvando no banco...")
        update_conversation(conversation_id, result)
        print()
        print("🎉 Pronto! A conversa foi reanalisada e atualizada.")
        print()
        print("📌 Agora ela aparecerá corretamente no dashboard com:")
        print(f"   - precisa_remarketing = {result.get('_precisa_remarketing')}")
        print(f"   - status_resolucao = {result.get('_status_resolucao')}")
        print(f"   - nivel_interesse = {result.get('_nivel_interesse')}")
    else:
        print()
        print("❌ Atualização cancelada. Banco não foi modificado.")

if __name__ == '__main__':
    main()
