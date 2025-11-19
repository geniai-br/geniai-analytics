"""
Script de DEBUG: Testar função de categorização
"""

import os
import sys
import pandas as pd

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.app.utils.db_connector import get_all_conversations
from src.app.utils.metrics import calculate_conversation_categories

print("=" * 80)
print("🐛 DEBUG: Teste de Categorização de Conversas")
print("=" * 80)
print()

# Carregar dados
print("📥 Carregando conversas...")
df = get_all_conversations()
print(f"✅ {len(df)} conversas carregadas")
print()

# Verificar coluna message_compiled
print("🔍 Verificando coluna 'message_compiled':")
if 'message_compiled' in df.columns:
    print("✅ Coluna 'message_compiled' existe")
    print(f"   - Valores nulos: {df['message_compiled'].isna().sum()}")
    print(f"   - Valores válidos: {df['message_compiled'].notna().sum()}")
else:
    print("❌ Coluna 'message_compiled' NÃO existe!")
    print(f"   Colunas disponíveis: {df.columns.tolist()}")
print()

# Testar categorização
print("🔄 Executando categorização...")
try:
    categories = calculate_conversation_categories(df, min_threshold=5.0)

    if categories.empty:
        print("❌ ERRO: DataFrame retornado está vazio!")
    else:
        print("✅ Categorização concluída com sucesso!")
        print()
        print("📊 RESULTADOS:")
        print(categories)
        print()
        print(f"Total de categorias: {len(categories)}")
        print(f"Total de conversas: {categories['quantidade'].sum()}")

except Exception as e:
    print(f"❌ ERRO durante categorização:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)