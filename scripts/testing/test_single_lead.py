#!/usr/bin/env python3
"""
Script de teste para analisar um único lead
"""

import sys
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, '/home/tester/projetos/geniai-analytics')
sys.path.insert(0, '/home/tester/projetos/geniai-analytics/src')

from sqlalchemy import create_engine, text
from src.multi_tenant.etl_v4.analyzers.openai_lead_remarketing_analyzer import OpenAILeadRemarketingAnalyzer
from src.multi_tenant.etl_v4.remarketing_analyzer import save_analysis_to_db
import json

# Configurar banco local
LOCAL_DB_URL = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
local_engine = create_engine(LOCAL_DB_URL)

# Buscar o lead específico (John Gomes)
query = text("""
    SELECT
        conversation_id,
        display_id,
        message_compiled,
        contact_name,
        account_name,
        contact_messages_count,
        mc_last_message_at,
        EXTRACT(EPOCH FROM (NOW() - mc_last_message_at)) / 3600 AS horas_inativo
    FROM conversations_analytics
    WHERE conversation_id = 7797
""")

with local_engine.connect() as conn:
    result = conn.execute(query)
    lead = dict(result.fetchone()._mapping)

print(f"📊 Lead encontrado:")
print(f"  ID: {lead['conversation_id']}")
print(f"  Display ID: #{lead['display_id']}")
print(f"  Nome: {lead['contact_name']}")
print(f"  Account: {lead['account_name']}")
print(f"  Mensagens do contato: {lead['contact_messages_count']}")
print(f"  Inativo há: {lead['horas_inativo']:.1f} horas (~{int(lead['horas_inativo']/24)} dias)")
print()

# Verificar se OPENAI_API_KEY está configurada
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ ERRO: OPENAI_API_KEY não configurada!")
    print("Configure com: export OPENAI_API_KEY='sua-chave-aqui'")
    sys.exit(1)

print(f"✅ OpenAI API Key configurada: {api_key[:8]}...{api_key[-4:]}")
print()

# Inicializar analisador
print("🤖 Inicializando OpenAI Lead Remarketing Analyzer...")
analyzer = OpenAILeadRemarketingAnalyzer(
    tenant_id=16,  # Allp Fit JP Sul
    api_key=api_key,
    model='gpt-4o-mini-2024-07-18'
)

# Classificar tipo de remarketing
tipo_remarketing = analyzer.get_remarketing_type(lead['horas_inativo'])
print(f"📋 Tipo de remarketing: {tipo_remarketing}")
print()

# Analisar lead
print("🔍 Analisando conversa com OpenAI...")
print("-" * 80)

resultado = analyzer.analyze_lead(
    conversation_id=lead['conversation_id'],
    conversa_compilada=lead['message_compiled'],
    contact_name=lead['contact_name'] or 'Cliente',
    inbox_name=lead['account_name'] or 'Equipe',
    tipo_remarketing=tipo_remarketing,
    tempo_inativo_horas=lead['horas_inativo']
)

print()
print("=" * 80)
print("RESULTADO DA ANÁLISE")
print("=" * 80)
print()

print(f"🏷️  Tipo: {resultado['tipo_conversa']}")
print(f"⭐ Score: {resultado['score_prioridade']}/5")
print()

print("📝 Análise:")
print(resultado['analise_ia'])
print()

print("💬 Sugestão de disparo:")
print(resultado['sugestao_disparo'])
print()

print("📊 Dados extraídos:")
dados = resultado['dados_extraidos_ia']
print(f"  - Nome completo: {dados.get('nome_completo', 'N/A')}")
print(f"  - Interesse: {dados.get('interesse_mencionado', 'N/A')}")
print(f"  - Objeções: {dados.get('objecoes', [])}")
print(f"  - Urgência: {dados.get('urgencia', 'N/A')}")
print(f"  - Contexto: {dados.get('contexto_relevante', 'N/A')}")
print()

print("💰 Metadados:")
meta = resultado['metadados_analise_ia']
print(f"  - Tokens: {meta['tokens_total']}")
print(f"  - Custo: R$ {meta['custo_brl']:.6f}")
print(f"  - Modelo: {meta['modelo']}")
print()

# Salvar no banco
print("💾 Salvando análise no banco...")
save_analysis_to_db(
    local_engine=local_engine,
    conversation_id=lead['conversation_id'],
    resultado=resultado
)
print("✅ Análise salva com sucesso!")
print()

# Verificar no banco
with local_engine.connect() as conn:
    check = conn.execute(
        text("SELECT tipo_conversa, score_prioridade, nome_mapeado_bot FROM conversations_analytics WHERE conversation_id = 7797")
    ).fetchone()
    print(f"🔍 Verificação no banco:")
    print(f"  - Tipo: {check[0]}")
    print(f"  - Score: {check[1]}")
    print(f"  - Nome mapeado: {check[2] or '(vazio)'}")

print()
print("=" * 80)
print("✅ TESTE CONCLUÍDO COM SUCESSO!")
print("=" * 80)