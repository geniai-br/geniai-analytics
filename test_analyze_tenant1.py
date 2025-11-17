#!/usr/bin/env python3
"""Script para testar análise de remarketing no tenant 1 (AllpFit CrossFit)"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = str(Path(__file__).parent / 'src')
sys.path.insert(0, src_path)

from multi_tenant.auth import get_etl_engine
from multi_tenant.etl_v4.remarketing_analyzer import analyze_inactive_leads
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_tenant1_analysis():
    """Testa análise de 1 lead do tenant 1 (AllpFit CrossFit)"""

    tenant_id = 1
    tenant_name = "AllpFit CrossFit"

    print("="*100)
    print(f"TESTE DE ANÁLISE DE REMARKETING - {tenant_name} (ID: {tenant_id})")
    print("="*100)
    print()

    # Obter engine ETL (bypass RLS)
    engine = get_etl_engine()

    print(f"🤖 Iniciando análise de leads inativos 24h+ para {tenant_name}...")
    print(f"⚠️  Limitando a APENAS 1 LEAD para teste")
    print()

    # Obter API key do .env
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não encontrada no .env")
        return

    # DEBUG: Verificar se há leads antes de analisar
    from sqlalchemy import text
    with engine.connect() as conn:
        debug_query = text("""
            SELECT COUNT(*) as total
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
              AND is_lead = TRUE
              AND tipo_conversa IS NULL
              AND mc_last_message_at < NOW() - INTERVAL '24 hours'
              AND contact_messages_count >= 3
              AND message_compiled IS NOT NULL
        """)
        debug_result = conn.execute(debug_query, {'tenant_id': tenant_id}).fetchone()
        print(f"🔍 DEBUG: Encontrados {debug_result[0]} leads para analisar na query manual")
        print()

    # Chamar análise (limitada a 1 lead para teste)
    result = analyze_inactive_leads(
        engine,
        tenant_id,
        openai_api_key=api_key,
        limit=1  # TESTE: apenas 1 lead
    )

    print()
    print("="*100)
    print("RESULTADO DA ANÁLISE:")
    print("="*100)
    print(f"✅ Leads analisados: {result['analyzed_count']}")
    print(f"❌ Falhas: {result['failed_count']}")
    print(f"💰 Tokens usados: {result['total_tokens']:,}")
    print(f"💵 Custo total: R$ {result['total_cost_brl']:.4f}")

    if result.get('skipped'):
        print(f"⏭️  Análise pulada: {result.get('error', 'Motivo desconhecido')}")

    print()

    # Buscar lead analisado para exibir resultado
    if result['analyzed_count'] > 0:
        print("="*100)
        print("VISUALIZANDO LEAD ANALISADO:")
        print("="*100)
        print()

        from sqlalchemy import text

        with engine.connect() as conn:
            query = text("""
                SELECT
                    display_id,
                    contact_name,
                    contact_phone,
                    tipo_conversa,
                    score_prioridade,
                    analise_ia,
                    sugestao_disparo,
                    dados_extraidos_ia,
                    metadados_analise_ia
                FROM conversations_analytics
                WHERE tenant_id = :tenant_id
                  AND analisado_em IS NOT NULL
                ORDER BY analisado_em DESC
                LIMIT 1
            """)

            lead = conn.execute(query, {'tenant_id': tenant_id}).fetchone()

            if lead:
                print(f"👤 LEAD: {lead.contact_name} (#{lead.display_id})")
                print(f"📞 Telefone: {lead.contact_phone}")
                print(f"🎯 Tipo: {lead.tipo_conversa}")
                print(f"⭐ Score: {lead.score_prioridade}/5")
                print()

                print("📝 ANÁLISE DA IA:")
                print("-" * 100)
                print(lead.analise_ia)
                print()

                if lead.dados_extraidos_ia:
                    import json
                    dados = json.loads(lead.dados_extraidos_ia) if isinstance(lead.dados_extraidos_ia, str) else lead.dados_extraidos_ia

                    print("📊 DADOS EXTRAÍDOS:")
                    print("-" * 100)
                    print(f"- Interesse: {dados.get('interesse_mencionado', 'N/A')}")
                    print(f"- Urgência: {dados.get('urgencia', 'N/A')}")
                    print(f"- Objeções: {', '.join(dados.get('objecoes', [])) if dados.get('objecoes') else 'Nenhuma'}")
                    print()

                print("💬 SUGESTÃO DE DISPARO:")
                print("-" * 100)
                print(lead.sugestao_disparo)
                print()

                if lead.metadados_analise_ia:
                    metadados = json.loads(lead.metadados_analise_ia) if isinstance(lead.metadados_analise_ia, str) else lead.metadados_analise_ia

                    print("📈 METADADOS:")
                    print("-" * 100)
                    print(f"- Modelo: {metadados.get('modelo', 'N/A')}")
                    print(f"- Tokens: {metadados.get('tokens_total', 0):,}")
                    print(f"- Custo: R$ {metadados.get('custo_brl', 0):.4f}")
                    print()

    print("="*100)
    print("FIM DO TESTE")
    print("="*100)

if __name__ == '__main__':
    test_tenant1_analysis()