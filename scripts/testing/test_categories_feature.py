"""
Script de Teste: Validar Feature de Categorização de Conversas
==============================================================

Testa a nova função calculate_conversation_categories() e simula
o comportamento do dashboard.

Autor: Isaac (via Claude Code)
Data: 2025-11-19
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.app.utils.db_connector import get_all_conversations
from src.app.utils.metrics import calculate_conversation_categories

print("=" * 80)
print("🧪 TESTE: Feature de Categorização de Conversas")
print("=" * 80)
print()

# ===================================================================
# 1. CARREGAR DADOS DO BANCO
# ===================================================================
print("📥 Carregando conversas do banco de dados...")
df = get_all_conversations()

print(f"✅ {len(df)} conversas carregadas")
print()

# ===================================================================
# 2. TESTAR FUNÇÃO DE CATEGORIZAÇÃO
# ===================================================================
print("🔄 Executando categorização...")
print()

try:
    categories = calculate_conversation_categories(df, min_threshold=5.0)

    print("=" * 80)
    print("✅ CATEGORIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print()

    # ===================================================================
    # 3. EXIBIR RESULTADOS
    # ===================================================================
    print("📊 CATEGORIAS IDENTIFICADAS:")
    print("-" * 80)
    print(f"{'CATEGORIA':<35} {'QUANTIDADE':<15} {'%':<10} {'COR'}")
    print("-" * 80)

    for _, row in categories.iterrows():
        print(f"{row['categoria']:<35} {row['quantidade']:<15} {row['percentual']:>6.1f}%    {row['cor']}")

    print("-" * 80)
    print(f"{'TOTAL':<35} {categories['quantidade'].sum():<15}")
    print()

    # ===================================================================
    # 4. ESTATÍSTICAS
    # ===================================================================
    print("=" * 80)
    print("📈 ESTATÍSTICAS:")
    print("=" * 80)
    print()

    total_conversas = categories['quantidade'].sum()
    categoria_principal = categories.iloc[0]

    print(f"Total de conversas analisadas: {total_conversas}")
    print(f"Número de categorias: {len(categories)}")
    print(f"Categoria principal: {categoria_principal['categoria']} ({categoria_principal['percentual']}%)")
    print()

    # ===================================================================
    # 5. VALIDAÇÃO
    # ===================================================================
    print("=" * 80)
    print("🔍 VALIDAÇÕES:")
    print("=" * 80)
    print()

    validacoes = []

    # Validação 1: Total de conversas bate
    if total_conversas == len(df):
        print("✅ Total de conversas categorizado = Total no DataFrame")
        validacoes.append(True)
    else:
        print(f"❌ ERRO: Total categorizado ({total_conversas}) != Total no DF ({len(df)})")
        validacoes.append(False)

    # Validação 2: Soma dos percentuais = 100%
    soma_percentuais = categories['percentual'].sum()
    if 99.9 <= soma_percentuais <= 100.1:  # Tolerância de arredondamento
        print(f"✅ Soma dos percentuais = {soma_percentuais:.1f}% (OK)")
        validacoes.append(True)
    else:
        print(f"❌ ERRO: Soma dos percentuais = {soma_percentuais:.1f}% (deveria ser ~100%)")
        validacoes.append(False)

    # Validação 3: Todas as categorias têm cores
    if all(row['cor'].startswith('#') for _, row in categories.iterrows()):
        print("✅ Todas as categorias têm cores válidas (formato hex)")
        validacoes.append(True)
    else:
        print("❌ ERRO: Algumas categorias sem cor válida")
        validacoes.append(False)

    # Validação 4: Categorias ordenadas por quantidade (decrescente)
    if categories['quantidade'].is_monotonic_decreasing:
        print("✅ Categorias ordenadas por quantidade (maior primeiro)")
        validacoes.append(True)
    else:
        print("⚠️  Categorias NÃO estão ordenadas")
        validacoes.append(False)

    # Validação 5: Nenhuma categoria tem quantidade zero
    if all(row['quantidade'] > 0 for _, row in categories.iterrows()):
        print("✅ Nenhuma categoria com quantidade zero")
        validacoes.append(True)
    else:
        print("❌ ERRO: Existem categorias com quantidade zero")
        validacoes.append(False)

    print()

    # ===================================================================
    # 6. RESULTADO FINAL
    # ===================================================================
    print("=" * 80)
    print("🏁 RESULTADO FINAL:")
    print("=" * 80)
    print()

    if all(validacoes):
        print("✅ TODOS OS TESTES PASSARAM!")
        print("🎉 A feature está pronta para produção!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print(f"   Aprovados: {sum(validacoes)}/{len(validacoes)}")

    print()
    print("=" * 80)

except Exception as e:
    print("❌ ERRO durante categorização:")
    print(f"   {type(e).__name__}: {e}")
    print()
    import traceback
    traceback.print_exc()