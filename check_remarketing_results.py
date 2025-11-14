#!/usr/bin/env python3
"""
Script to validate remarketing analysis results
"""

import os
import sys
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def get_local_engine():
    """Cria engine de conexão com banco local"""
    password_encoded = quote_plus(os.getenv('LOCAL_DB_PASSWORD'))
    conn_str = (
        f"postgresql://{os.getenv('LOCAL_DB_USER')}:{password_encoded}"
        f"@{os.getenv('LOCAL_DB_HOST')}:{os.getenv('LOCAL_DB_PORT')}/{os.getenv('LOCAL_DB_NAME')}"
    )
    return create_engine(conn_str)

def main():
    print("="*80)
    print("VALIDAÇÃO DOS RESULTADOS DE ANÁLISE DE REMARKETING")
    print("="*80)
    print()

    engine = get_local_engine()

    # Query 1: Verificar leads analisados
    query1 = text("""
        SELECT
            conversation_id,
            display_id,
            contact_name,
            tipo_conversa,
            score_prioridade,
            LEFT(analise_ia, 100) as analise_preview,
            analisado_em
        FROM conversations_analytics
        WHERE tenant_id = 18
          AND tipo_conversa IS NOT NULL
        ORDER BY conversation_id
        LIMIT 10
    """)

    print("📊 LEADS ANALISADOS (Tenant 18):")
    print("-" * 80)

    with engine.connect() as conn:
        result = conn.execute(query1)
        rows = result.fetchall()

        if not rows:
            print("❌ Nenhum lead encontrado com análise de remarketing!")
            return 1

        print(f"✅ Total: {len(rows)} leads analisados\n")

        for row in rows:
            print(f"ID: {row[0]} | Display: #{row[1]} | Nome: {row[2]}")
            print(f"Tipo: {row[3]} | Score: {row[4]}")
            print(f"Análise: {row[5]}...")
            print(f"Analisado em: {row[6]}")
            print("-" * 80)

    # Query 2: Verificar campos JSONB
    query2 = text("""
        SELECT
            conversation_id,
            display_id,
            dados_extraidos_ia->>'objetivo' as objetivo,
            dados_extraidos_ia->>'urgencia' as urgencia,
            metadados_analise_ia->>'tokens_total' as tokens,
            metadados_analise_ia->>'custo_brl' as custo_brl
        FROM conversations_analytics
        WHERE tenant_id = 18
          AND tipo_conversa IS NOT NULL
        ORDER BY conversation_id
        LIMIT 10
    """)

    print("\n📋 DADOS EXTRAÍDOS E METADADOS:")
    print("-" * 80)

    with engine.connect() as conn:
        result = conn.execute(query2)
        rows = result.fetchall()

        total_tokens = 0
        total_cost = 0.0

        for row in rows:
            print(f"Display #{row[1]} (ID: {row[0]})")
            print(f"  Objetivo: {row[2]}")
            print(f"  Urgência: {row[3]}")
            print(f"  Tokens: {row[4]} | Custo: R$ {row[5]}")
            print()

            if row[4]:
                total_tokens += int(row[4])
            if row[5]:
                total_cost += float(row[5])

        print("-" * 80)
        print(f"TOTAL: {total_tokens} tokens | R$ {total_cost:.4f}")
        print()

    # Query 3: Verificar sugestões de disparo
    query3 = text("""
        SELECT
            display_id,
            contact_name,
            tipo_conversa,
            sugestao_disparo
        FROM conversations_analytics
        WHERE tenant_id = 18
          AND tipo_conversa IS NOT NULL
        ORDER BY conversation_id
        LIMIT 3
    """)

    print("\n💬 SUGESTÕES DE DISPARO GERADAS:")
    print("-" * 80)

    with engine.connect() as conn:
        result = conn.execute(query3)
        rows = result.fetchall()

        for row in rows:
            print(f"\nLead #{row[0]} - {row[1]} ({row[2]})")
            print("-" * 40)
            print(row[3])
            print("-" * 40)

    print("\n" + "="*80)
    print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*80)

    return 0

if __name__ == "__main__":
    sys.exit(main())