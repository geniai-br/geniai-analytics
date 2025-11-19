#!/usr/bin/env python3
"""
Script de teste para análise de leads do CDT Mossoró (tenant_id 14)
Testa a análise OpenAI em outro contexto de negócio
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, '/home/tester/projetos/geniai-analytics')
sys.path.insert(0, '/home/tester/projetos/geniai-analytics/src')

from sqlalchemy import create_engine, text
from src.multi_tenant.etl_v4.remarketing_analyzer import analyze_inactive_leads

# Configurar banco local
LOCAL_DB_URL = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
local_engine = create_engine(LOCAL_DB_URL)

# Verificar se OPENAI_API_KEY está configurada
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ ERRO: OPENAI_API_KEY não configurada!")
    print("Configure com: export OPENAI_API_KEY='sua-chave-aqui'")
    sys.exit(1)

print("=" * 80)
print("ANÁLISE EM MASSA - CDT MOSSORÓ")
print("Tenant ID: 14")
print("=" * 80)
print()

# Verificar quantos leads estão pendentes
with local_engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) as total
        FROM conversations_analytics
        WHERE tenant_id = 14
          AND is_lead = true
          AND tipo_conversa IS NULL
          AND message_compiled IS NOT NULL
    """))
    total_pendentes = result.scalar()

print(f"📊 Total de leads pendentes: {total_pendentes}")
print()

if total_pendentes == 0:
    print("✅ Nenhum lead pendente para analisar!")
    sys.exit(0)

# Confirmar
print(f"⚠️  Isso irá analisar {total_pendentes} leads usando OpenAI.")
print(f"💰 Custo estimado: R$ {total_pendentes * 0.0008:.2f} (aproximadamente)")
print()

# Configurações
BATCH_SIZE = 50  # Processar em lotes de 50
MAX_COST_PER_BATCH = 0.10  # R$ 0,10 por lote

total_analyzed = 0
total_failed = 0
total_skipped = 0
total_cost = 0.0
batch_num = 1

inicio = datetime.now()

while total_analyzed < total_pendentes:
    print()
    print("=" * 80)
    print(f"LOTE {batch_num} - Processando até {BATCH_SIZE} leads")
    print("=" * 80)
    print()

    resultado = analyze_inactive_leads(
        local_engine=local_engine,
        tenant_id=14,  # CDT Mossoró
        openai_api_key=api_key,
        limit=BATCH_SIZE,
        max_cost_brl=MAX_COST_PER_BATCH
    )

    # Atualizar contadores
    total_analyzed += resultado['analyzed_count']
    total_failed += resultado['failed_count']
    total_skipped += resultado.get('skipped_no_response', 0)
    total_cost += resultado['total_cost_brl']

    print()
    print(f"📊 Resumo do lote {batch_num}:")
    print(f"  ✅ Analisados: {resultado['analyzed_count']}")
    print(f"  ❌ Falhas: {resultado['failed_count']}")
    print(f"  ⏭️  Pulados: {resultado.get('skipped_no_response', 0)}")
    print(f"  💰 Custo do lote: R$ {resultado['total_cost_brl']:.4f}")
    print()

    # Se não analisou nenhum, parar
    if resultado['analyzed_count'] == 0:
        print("⚠️  Nenhum lead analisado neste lote. Finalizando.")
        break

    batch_num += 1

# Resumo final
fim = datetime.now()
duracao = (fim - inicio).total_seconds()

print()
print("=" * 80)
print("ANÁLISE CONCLUÍDA!")
print("=" * 80)
print()
print(f"📊 Estatísticas finais:")
print(f"  ✅ Total analisados: {total_analyzed}")
print(f"  ❌ Total falhas: {total_failed}")
print(f"  ⏭️  Total pulados: {total_skipped}")
print(f"  💰 Custo total: R$ {total_cost:.4f}")
print(f"  ⏱️  Tempo total: {duracao:.1f}s ({duracao/60:.1f} minutos)")
print(f"  📈 Média: {duracao/max(total_analyzed, 1):.2f}s por lead")
print()

# Verificar status final
with local_engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            COUNT(*) as total_leads,
            COUNT(CASE WHEN tipo_conversa IS NOT NULL THEN 1 END) as analisados,
            COUNT(CASE WHEN tipo_conversa IS NULL THEN 1 END) as pendentes
        FROM conversations_analytics
        WHERE tenant_id = 14 AND is_lead = true
    """))
    stats = result.fetchone()

    print(f"📊 Status final no banco:")
    print(f"  Total de leads: {stats[0]}")
    print(f"  Analisados: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"  Pendentes: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")

print()
print("=" * 80)