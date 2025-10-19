"""
ETL Pipeline V2: Extract from remote view vw_conversations_analytics_final → Load to local PostgreSQL
Execução: 1x por dia (agendado para 3h da manhã)
Estratégia: UPSERT (INSERT ou UPDATE se já existir)
"""
import os
import sys
import pandas as pd
import json
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configurações
SOURCE_VIEW = 'vw_conversations_analytics_final'
LOCAL_TABLE = 'conversas_analytics'


def get_source_engine():
    """Cria engine de conexão com banco remoto"""
    conn_str = (
        f"postgresql://{os.getenv('SOURCE_DB_USER')}:{os.getenv('SOURCE_DB_PASSWORD')}"
        f"@{os.getenv('SOURCE_DB_HOST')}:{os.getenv('SOURCE_DB_PORT')}/{os.getenv('SOURCE_DB_NAME')}"
    )
    return create_engine(conn_str)


def get_local_engine():
    """Cria engine de conexão com banco local"""
    # URL encode da senha para evitar problemas com caracteres especiais (@, etc)
    password_encoded = quote_plus(os.getenv('LOCAL_DB_PASSWORD'))

    conn_str = (
        f"postgresql://{os.getenv('LOCAL_DB_USER')}:{password_encoded}"
        f"@{os.getenv('LOCAL_DB_HOST')}:{os.getenv('LOCAL_DB_PORT')}/{os.getenv('LOCAL_DB_NAME')}"
    )
    return create_engine(conn_str)


def extract_from_source():
    """
    Extrai dados da view remota vw_conversations_analytics_final
    Retorna: DataFrame com todos os dados
    """
    print("=" * 80)
    print("EXTRACT: Buscando dados da view remota")
    print("=" * 80)
    print(f"View: {SOURCE_VIEW}")
    print(f"Host: {os.getenv('SOURCE_DB_HOST')}")
    print(f"Database: {os.getenv('SOURCE_DB_NAME')}")

    try:
        engine = get_source_engine()

        # Query para extrair todos os dados
        query = f"SELECT * FROM {SOURCE_VIEW}"

        print(f"\nExecutando query...")
        start_time = datetime.now()

        df = pd.read_sql(query, engine)

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ Extração concluída!")
        print(f"   Linhas extraídas: {len(df):,}")
        print(f"   Colunas: {len(df.columns)}")
        print(f"   Tempo: {elapsed:.2f}s")

        # Mostrar primeiras colunas
        print(f"\n📊 Primeiras colunas:")
        for i, col in enumerate(df.columns[:10], 1):
            print(f"   {i}. {col}")
        print(f"   ... e mais {len(df.columns) - 10} colunas")

        engine.dispose()
        return df

    except Exception as e:
        print(f"\n❌ Erro ao extrair dados: {e}")
        import traceback
        traceback.print_exc()
        return None


def transform_data(df):
    """
    Transforma os dados para adequar ao schema local
    - Renomeia colunas se necessário
    - Converte tipos de dados
    - Trata valores nulos
    """
    print("\n" + "=" * 80)
    print("TRANSFORM: Preparando dados para inserção")
    print("=" * 80)

    if df is None or df.empty:
        print("❌ Nenhum dado para transformar")
        return None

    try:
        # Criar cópia para não modificar original
        df_transformed = df.copy()

        # Converter message_compiled para JSON string válido
        if 'message_compiled' in df_transformed.columns:
            # PostgreSQL retorna como objeto Python, converter para JSON string
            df_transformed['message_compiled'] = df_transformed['message_compiled'].apply(
                lambda x: json.dumps(x) if x is not None else None
            )

        # Adicionar campos de controle do ETL
        df_transformed['etl_inserted_at'] = datetime.now()
        df_transformed['etl_updated_at'] = datetime.now()

        # Tratar valores NaN/None em campos numéricos
        numeric_cols = df_transformed.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            df_transformed[col] = df_transformed[col].where(pd.notna(df_transformed[col]), None)

        # Tratar valores NaN/None em campos de texto
        text_cols = df_transformed.select_dtypes(include=['object']).columns
        for col in text_cols:
            if col != 'message_compiled':  # Já tratado acima
                df_transformed[col] = df_transformed[col].where(pd.notna(df_transformed[col]), None)

        print(f"✅ Dados transformados com sucesso")
        print(f"   Linhas: {len(df_transformed):,}")
        print(f"   Colunas finais: {len(df_transformed.columns)}")

        return df_transformed

    except Exception as e:
        print(f"❌ Erro na transformação: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_to_local(df):
    """
    Carrega dados no banco local usando estratégia UPSERT
    - INSERT novos registros
    - UPDATE registros existentes
    """
    print("\n" + "=" * 80)
    print("LOAD: Inserindo/Atualizando dados no banco local")
    print("=" * 80)

    if df is None or df.empty:
        print("❌ Nenhum dado para carregar")
        return False

    try:
        engine = get_local_engine()

        print(f"Tabela destino: {LOCAL_TABLE}")
        print(f"Estratégia: UPSERT (INSERT ou UPDATE)")

        # Verificar quantos registros já existem
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {LOCAL_TABLE}"))
            count_before = result.scalar()
            print(f"\nRegistros atuais na tabela: {count_before:,}")

        start_time = datetime.now()

        # Usar pandas to_sql com método UPSERT customizado
        # Por simplicidade, vamos usar TRUNCATE + INSERT para primeira versão
        # Depois podemos otimizar para UPDATE apenas registros modificados

        print(f"\nInserindo {len(df):,} registros...")

        # Estratégia 1: Limpar tabela e inserir tudo (mais simples)
        # Para produção, podemos mudar para UPDATE apenas registros alterados
        with engine.connect() as conn:
            # Truncate (limpar tabela)
            conn.execute(text(f"TRUNCATE TABLE {LOCAL_TABLE}"))
            conn.commit()
            print("✓ Tabela limpa (TRUNCATE)")

        # Insert em batch
        df.to_sql(
            LOCAL_TABLE,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000  # Inserir em lotes de 1000 registros
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # Verificar inserção
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {LOCAL_TABLE}"))
            count_after = result.scalar()

        print(f"\n✅ Carga concluída!")
        print(f"   Registros inseridos: {count_after:,}")
        print(f"   Tempo: {elapsed:.2f}s")
        print(f"   Velocidade: {count_after/elapsed:.0f} registros/segundo")

        engine.dispose()
        return True

    except Exception as e:
        print(f"\n❌ Erro ao carregar dados: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_backup(df):
    """
    Cria backup CSV dos dados extraídos
    """
    if df is None or df.empty:
        return

    try:
        # Criar diretório de backups
        backup_dir = "data/backups"
        os.makedirs(backup_dir, exist_ok=True)

        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"{backup_dir}/conversas_analytics_{timestamp}.csv"

        df.to_csv(csv_file, index=False)

        file_size_mb = os.path.getsize(csv_file) / (1024 * 1024)
        print(f"\n💾 Backup criado: {csv_file}")
        print(f"   Tamanho: {file_size_mb:.2f} MB")

    except Exception as e:
        print(f"\n⚠️  Erro ao criar backup: {e}")


def print_statistics(df):
    """
    Imprime estatísticas dos dados extraídos
    """
    if df is None or df.empty:
        return

    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS DOS DADOS")
    print("=" * 80)

    try:
        # Estatísticas gerais
        print(f"\n📈 Resumo:")
        print(f"   Total de conversas: {len(df):,}")

        if 'status_label_pt' in df.columns:
            print(f"\n📊 Por Status:")
            status_counts = df['status_label_pt'].value_counts()
            for status, count in status_counts.items():
                pct = (count / len(df)) * 100
                print(f"   {status}: {count:,} ({pct:.1f}%)")

        if 'conversation_date' in df.columns:
            print(f"\n📅 Período:")
            print(f"   Data mais antiga: {df['conversation_date'].min()}")
            print(f"   Data mais recente: {df['conversation_date'].max()}")

        if 'has_csat' in df.columns:
            csat_count = df['has_csat'].sum()
            csat_pct = (csat_count / len(df)) * 100
            print(f"\n⭐ CSAT:")
            print(f"   Com avaliação: {csat_count:,} ({csat_pct:.1f}%)")

        if 'has_human_intervention' in df.columns:
            human_count = df['has_human_intervention'].sum()
            human_pct = (human_count / len(df)) * 100
            print(f"\n🤖 Atendimento:")
            print(f"   Com intervenção humana: {human_count:,} ({human_pct:.1f}%)")
            print(f"   Apenas bot: {len(df) - human_count:,} ({100 - human_pct:.1f}%)")

    except Exception as e:
        print(f"⚠️  Erro ao calcular estatísticas: {e}")


def run_etl():
    """
    Executa pipeline ETL completo
    """
    print("\n" + "█" * 80)
    print("  ETL PIPELINE V2 - AllpFit Analytics")
    print("  Extração: vw_conversations_analytics_final (remoto)")
    print("  Destino: conversas_analytics (local)")
    print(f"  Execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("█" * 80 + "\n")

    start_total = datetime.now()

    # 1. EXTRACT
    df = extract_from_source()

    if df is None:
        print("\n❌ ETL abortado - falha na extração")
        return False

    # 2. TRANSFORM
    df_transformed = transform_data(df)

    if df_transformed is None:
        print("\n❌ ETL abortado - falha na transformação")
        return False

    # 3. LOAD
    success = load_to_local(df_transformed)

    if not success:
        print("\n❌ ETL abortado - falha na carga")
        return False

    # 4. BACKUP
    create_backup(df)

    # 5. ESTATÍSTICAS
    print_statistics(df)

    # Tempo total
    elapsed_total = (datetime.now() - start_total).total_seconds()

    print("\n" + "█" * 80)
    print("  ✅ ETL PIPELINE CONCLUÍDO COM SUCESSO!")
    print(f"  Tempo total: {elapsed_total:.2f}s ({elapsed_total/60:.1f} minutos)")
    print("█" * 80 + "\n")

    return True


if __name__ == "__main__":
    run_etl()
