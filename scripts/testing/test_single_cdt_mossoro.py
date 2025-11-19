#!/usr/bin/env python3
"""
Teste de análise de 1 único lead do CDT Mossoró
Para validar qualidade da análise OpenAI em outro contexto
"""

import sys
import os

sys.path.insert(0, '/home/tester/projetos/geniai-analytics')
sys.path.insert(0, '/home/tester/projetos/geniai-analytics/src')

from sqlalchemy import create_engine, text
from src.multi_tenant.etl_v4.remarketing_analyzer import analyze_inactive_leads

# Configurar banco
LOCAL_DB_URL = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
local_engine = create_engine(LOCAL_DB_URL)

# API Key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ ERRO: OPENAI_API_KEY não configurada!")
    sys.exit(1)

print("=" * 80)
print("TESTE DE 1 LEAD - CDT MOSSORÓ")
print("Tenant ID: 14")
print("=" * 80)
print()

# Analisar apenas 1 lead
resultado = analyze_inactive_leads(
    local_engine=local_engine,
    tenant_id=14,
    openai_api_key=api_key,
    limit=1,
    max_cost_brl=0.10
)

print()
print("=" * 80)
print("RESULTADO DO TESTE")
print("=" * 80)
print()
print(f"✅ Analisados: {resultado['analyzed_count']}")
print(f"❌ Falhas: {resultado['failed_count']}")
print(f"⏭️  Pulados: {resultado.get('skipped_no_response', 0)}")
print(f"💰 Custo: R$ {resultado['total_cost_brl']:.4f}")
print()

# Buscar o lead analisado para ver a qualidade
if resultado['analyzed_count'] > 0:
    with local_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                conversation_id,
                contact_name,
                tipo_conversa,
                tipo_remarketing,
                prioridade_conversa,
                confianca_analise,
                palavras_chave,
                sugestao_mensagem
            FROM conversations_analytics
            WHERE tenant_id = 14
              AND tipo_conversa IS NOT NULL
              AND tipo_conversa != 'SKIP_NO_RESPONSE'
            ORDER BY custo_analise_brl DESC
            LIMIT 1
        """))
        lead = result.fetchone()

        if lead:
            print("=" * 80)
            print("ANÁLISE GERADA PELA IA")
            print("=" * 80)
            print()
            print(f"📞 Contato: {lead[1]}")
            print(f"🔖 Tipo de Conversa: {lead[2]}")
            print(f"📧 Tipo Remarketing: {lead[3]}")
            print(f"⭐ Prioridade: {lead[4]}")
            print(f"📊 Confiança: {lead[5]}%")
            print(f"🔑 Palavras-chave: {lead[6]}")
            print()
            print("💬 Sugestão de Mensagem:")
            print("-" * 80)
            print(lead[7])
            print("-" * 80)
            print()