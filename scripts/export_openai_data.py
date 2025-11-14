#!/usr/bin/env python3
"""
Exporta dados OpenAI do banco para CSV
"""
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Conexão com banco
password = quote_plus('vlVMVM6UNz2yYSBlzodPjQvZh')
connection_string = f"postgresql://johan_geniai:{password}@localhost:5432/geniai_analytics"
engine = create_engine(connection_string)

print("📊 Exportando dados OpenAI...")

# Query
query = text("""
    SELECT
        conversation_id,
        contact_name,
        contact_phone,
        conversation_created_at as data,
        is_lead as lead,
        visit_scheduled as visita,
        crm_converted as crm,
        ROUND(ai_probability_score::numeric, 0) as score,
        ai_probability_label as classificacao,
        probabilidade_conversao as prob_0_5,
        nome_mapeado_bot as nome_ia,
        condicao_fisica,
        objetivo,
        LENGTH(analise_ia) as chars_analise,
        LENGTH(sugestao_disparo) as chars_sugestao,
        t_messages as total_msgs,
        contact_messages_count as msgs_cliente,
        analise_ia,
        sugestao_disparo
    FROM conversations_analytics
    WHERE tenant_id = 1
      AND LENGTH(analise_ia) > 0
    ORDER BY conversation_created_at DESC
""")

# Buscar dados
with engine.connect() as conn:
    df = pd.read_sql(query, conn)

print(f"✅ {len(df)} conversas encontradas")

# Salvar CSV resumido (sem textos completos)
df_resumo = df.drop(['analise_ia', 'sugestao_disparo'], axis=1)
csv_resumo = '/tmp/openai_resumo_300.csv'
df_resumo.to_csv(csv_resumo, index=False)
print(f"📄 CSV resumido salvo: {csv_resumo}")

# Salvar CSV completo (com textos)
csv_completo = '/tmp/openai_completo_300.csv'
df.to_csv(csv_completo, index=False)
print(f"📄 CSV completo salvo: {csv_completo}")

# Estatísticas
print("\n📊 ESTATÍSTICAS:")
print(f"   Total conversas: {len(df)}")
print(f"   Leads: {df['lead'].sum()} ({df['lead'].sum()/len(df)*100:.1f}%)")
print(f"   Visitas: {df['visita'].sum()} ({df['visita'].sum()/len(df)*100:.1f}%)")
print(f"   CRM: {df['crm'].sum()} ({df['crm'].sum()/len(df)*100:.1f}%)")
print(f"   Score médio: {df['score'].mean():.1f}")
print(f"\n✨ Dados OpenAI:")
print(f"   Com nome extraído: {(df['nome_ia'] != '').sum()} ({(df['nome_ia'] != '').sum()/len(df)*100:.1f}%)")
print(f"   Com condição física: {(df['condicao_fisica'] != 'Não mencionado').sum()}")
print(f"   Com objetivo: {(df['objetivo'] != 'Não mencionado').sum()}")
print(f"   Prob média (0-5): {df['prob_0_5'].mean():.2f}")

print("\n✅ Exportação concluída!")
