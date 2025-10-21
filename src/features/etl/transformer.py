"""
Transformer - Transformação de dados

Este módulo é responsável por:
1. Converter tipos de dados
2. Tratar valores nulos
3. Adicionar campos de controle ETL
4. Preparar dados para inserção no banco local
"""

import json
import pandas as pd
from datetime import datetime


def transform_data(df):
    """
    Transforma os dados para adequar ao schema local

    Args:
        df: DataFrame com dados extraídos

    Returns:
        tuple: (DataFrame transformado, duration_seconds)
    """
    print("\n" + "=" * 80)
    print("TRANSFORM: Preparando dados")
    print("=" * 80)

    if df is None or df.empty:
        print("⚠️  Nenhum dado para transformar")
        return None, 0

    start_time = datetime.now()

    try:
        # Criar cópia para não modificar original
        df_transformed = df.copy()

        print(f"📊 Linhas a transformar: {len(df_transformed):,}")

        # 1. Converter message_compiled para JSON string válido
        if 'message_compiled' in df_transformed.columns:
            print("   🔄 Convertendo message_compiled para JSON...")
            df_transformed['message_compiled'] = df_transformed['message_compiled'].apply(
                lambda x: json.dumps(x) if x is not None else None
            )

        # 2. Adicionar campos de controle do ETL
        df_transformed['etl_updated_at'] = datetime.now()

        # Para novos registros, etl_inserted_at será definido no INSERT
        # Para registros existentes (UPDATE), etl_inserted_at permanece o original

        # 3. Tratar NaT (Not a Time) em campos datetime
        print("   🔄 Tratando valores NaT em campos datetime...")
        datetime_cols = df_transformed.select_dtypes(include=['datetime64']).columns
        for col in datetime_cols:
            # Converter NaT para None (NULL no PostgreSQL)
            df_transformed[col] = df_transformed[col].where(pd.notna(df_transformed[col]), None)

        # 4. Tratar valores NaN/None em campos numéricos
        numeric_cols = df_transformed.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            df_transformed[col] = df_transformed[col].where(pd.notna(df_transformed[col]), None)

        # 5. Tratar valores NaN/None em campos de texto
        text_cols = df_transformed.select_dtypes(include=['object']).columns
        for col in text_cols:
            if col != 'message_compiled':  # Já tratado acima
                df_transformed[col] = df_transformed[col].where(pd.notna(df_transformed[col]), None)

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"✅ Transformação concluída!")
        print(f"   Linhas transformadas: {len(df_transformed):,}")
        print(f"   Colunas finais: {len(df_transformed.columns)}")
        print(f"   Tempo: {elapsed:.2f}s")

        return df_transformed, elapsed

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ Erro na transformação: {e}")
        import traceback
        traceback.print_exc()
        raise


def validate_data(df):
    """
    Valida dados transformados antes da carga

    Args:
        df: DataFrame transformado

    Returns:
        bool: True se dados são válidos
    """
    if df is None or df.empty:
        print("⚠️  DataFrame vazio - nada a validar")
        return False

    print(f"\n🔍 Validando dados...")

    # Verificar campos obrigatórios
    required_fields = ['conversation_id', 'inbox_name']

    for field in required_fields:
        if field not in df.columns:
            print(f"   ❌ Campo obrigatório ausente: {field}")
            return False

        null_count = df[field].isna().sum()
        if null_count > 0:
            print(f"   ⚠️  Campo {field} tem {null_count} valores nulos")

    # Verificar duplicatas
    if 'conversation_id' in df.columns:
        duplicates = df['conversation_id'].duplicated().sum()
        if duplicates > 0:
            print(f"   ⚠️  Encontradas {duplicates} conversation_ids duplicadas")
            return False

    print(f"   ✅ Validação concluída - dados OK")
    return True
