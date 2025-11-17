#!/usr/bin/env python3
"""
Script de Análise em Massa - JP Sul (Tenant 16)
================================================

Analisa TODOS os leads inativos 24h+ do tenant JP Sul usando OpenAI.
Processa em batches de 50 leads por vez para não sobrecarregar a API.

Uso:
    python analyze_jp_sul_mass.py [--limit N] [--batch-size N] [--dry-run]

Argumentos:
    --limit N: Limita análise a N leads (padrão: sem limite)
    --batch-size N: Leads por batch (padrão: 50)
    --dry-run: Apenas simula, não executa análises reais

Autor: Isaac (via Claude Code)
Data: 2025-11-17
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Adicionar diretório src ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from dotenv import load_dotenv
from multi_tenant.auth.auth import get_etl_engine
from multi_tenant.etl_v4.remarketing_analyzer import analyze_inactive_leads

# Carregar variáveis de ambiente
load_dotenv()


def main():
    """Executa análise em massa dos leads do JP Sul."""

    # Parse de argumentos
    parser = argparse.ArgumentParser(description='Análise em massa de leads - JP Sul')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limite total de leads a analisar')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Leads por batch (padrão: 50)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Apenas simula, não executa análises')

    args = parser.parse_args()

    # Configurações
    TENANT_ID = 16  # JP Sul
    BATCH_SIZE = args.batch_size
    MAX_COST_PER_BATCH = 0.20  # R$ 0.20 por batch (segurança)

    print("=" * 80)
    print("🤖 ANÁLISE EM MASSA DE LEADS - ALLPFIT JP SUL")
    print("=" * 80)
    print(f"📅 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏢 Tenant ID: {TENANT_ID} (AllpFit JP Sul)")
    print(f"📦 Batch size: {BATCH_SIZE} leads por vez")
    print(f"💰 Custo máximo por batch: R$ {MAX_COST_PER_BATCH:.2f}")

    if args.limit:
        print(f"🔢 Limite total: {args.limit} leads")
    else:
        print(f"🔢 Limite total: SEM LIMITE (todos os leads disponíveis)")

    if args.dry_run:
        print("⚠️  MODO DRY-RUN: Nenhuma análise será executada!")

    print("=" * 80)
    print()

    # Conectar ao banco
    try:
        engine = get_etl_engine()
        print("✅ Conectado ao banco de dados (ETL engine)")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return 1

    # Estatísticas globais
    total_analyzed = 0
    total_failed = 0
    total_skipped = 0
    total_tokens = 0
    total_cost_brl = 0.0
    batch_number = 0

    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY não encontrada no .env!")
        return 1

    print(f"✅ OPENAI_API_KEY configurada (primeiros 10 chars: {api_key[:10]}...)")
    print()

    if args.dry_run:
        print("🔍 MODO DRY-RUN: Simulando análise...")
        print(f"   Seriam analisados até {args.limit or 'TODOS'} leads em batches de {BATCH_SIZE}")
        print()
        return 0

    # Loop de análise em batches
    while True:
        batch_number += 1
        batch_limit = BATCH_SIZE

        # Aplicar limite global se especificado
        if args.limit:
            remaining = args.limit - total_analyzed
            if remaining <= 0:
                print(f"✅ Limite de {args.limit} leads atingido!")
                break
            batch_limit = min(batch_limit, remaining)

        print(f"📦 BATCH #{batch_number}")
        print(f"   Processando até {batch_limit} leads...")

        try:
            # Executar análise do batch
            result = analyze_inactive_leads(
                local_engine=engine,
                tenant_id=TENANT_ID,
                openai_api_key=api_key,
                limit=batch_limit,
                max_cost_brl=MAX_COST_PER_BATCH
            )

            # Atualizar estatísticas
            batch_analyzed = result.get('analyzed_count', 0)
            batch_failed = result.get('failed_count', 0)
            batch_skipped = result.get('skipped_no_response', 0)
            batch_tokens = result.get('total_tokens', 0)
            batch_cost = result.get('total_cost_brl', 0.0)

            total_analyzed += batch_analyzed
            total_failed += batch_failed
            total_skipped += batch_skipped
            total_tokens += batch_tokens
            total_cost_brl += batch_cost

            # Log do batch
            print(f"   ✅ Analisados: {batch_analyzed}")
            print(f"   ❌ Falhas: {batch_failed}")
            print(f"   ⏭️  Pulados (sem resposta): {batch_skipped}")
            print(f"   🎯 Tokens: {batch_tokens}")
            print(f"   💰 Custo: R$ {batch_cost:.4f}")
            print()

            # Se não encontrou mais leads, parar
            if batch_analyzed == 0 and batch_skipped == 0:
                print("✅ Nenhum lead restante para analisar!")
                break

            # Se atingiu o limite do batch (ainda há mais leads)
            if batch_analyzed + batch_skipped >= batch_limit:
                print(f"⏸️  Pausando 2 segundos antes do próximo batch...")
                time.sleep(2)
            else:
                # Batch incompleto = não há mais leads
                print("✅ Batch incompleto - análise concluída!")
                break

        except KeyboardInterrupt:
            print()
            print("⚠️  Análise interrompida pelo usuário (Ctrl+C)")
            break

        except Exception as e:
            print(f"   ❌ Erro no batch #{batch_number}: {e}")
            total_failed += 1

            # Decidir se continua ou para
            if batch_number >= 3:  # Após 3 falhas consecutivas, parar
                print("❌ Muitas falhas consecutivas. Abortando.")
                break

            print("   ⏸️  Aguardando 5 segundos antes de tentar próximo batch...")
            time.sleep(5)

    # Relatório final
    print()
    print("=" * 80)
    print("📊 RELATÓRIO FINAL - ANÁLISE EM MASSA JP SUL")
    print("=" * 80)
    print(f"🏢 Tenant: AllpFit JP Sul (ID: {TENANT_ID})")
    print(f"📅 Concluído em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"📦 Total de batches processados: {batch_number}")
    print(f"✅ Leads analisados com sucesso: {total_analyzed}")
    print(f"⏭️  Leads pulados (sem resposta bot/agente): {total_skipped}")
    print(f"❌ Leads com falha: {total_failed}")
    print()
    print(f"🎯 Total de tokens usados: {total_tokens:,}")
    print(f"💰 Custo total: R$ {total_cost_brl:.4f}")

    if total_analyzed > 0:
        avg_tokens = total_tokens / total_analyzed
        avg_cost = total_cost_brl / total_analyzed
        print(f"📊 Média por lead: {avg_tokens:.0f} tokens | R$ {avg_cost:.4f}")

    print("=" * 80)

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)