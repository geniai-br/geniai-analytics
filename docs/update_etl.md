# 🔄 Atualizar ETL para Consumir as Novas Views

## 📋 Visão Geral

Após deploy das views no banco de produção, vamos atualizar o pipeline ETL para:

1. ✅ Extrair dados da nova view `vw_conversations_analytics_final`
2. ✅ Processar e transformar os dados
3. ✅ Carregar no banco local
4. ✅ Preparar para o dashboard

---

## 🎯 Mudanças Necessárias

### **ANTES (View Antiga):**
```python
# src/features/etl_pipeline.py - VERSÃO ANTIGA

def extract_from_source():
    view_name = 'vw_conversas_por_lead'  # ← View antiga
    query = f"SELECT * FROM {view_name}"
    df = pd.read_sql(query, engine)
    # Apenas 6 colunas: conversation_id, message_compiled,
    # client_sender_id, inbox_id, client_phone, t_messages
```

### **DEPOIS (View Nova):**
```python
# src/features/etl_pipeline.py - VERSÃO NOVA

def extract_from_source():
    view_name = 'vw_conversations_analytics_final'  # ← View nova
    query = f"SELECT * FROM {view_name}"
    df = pd.read_sql(query, engine)
    # Agora tem 150+ colunas com todos os dados necessários!
```

---

## 🔨 Implementação

### **Passo 1: Atualizar src/shared/config.py**

Adicionar configuração para a view:

```python
# src/shared/config.py

class Config:
    # ... (código existente)

    # View para extração
    SOURCE_DB_VIEW: str = os.getenv('SOURCE_DB_VIEW', 'vw_conversations_analytics_final')
```

Atualizar o `.env`:

```bash
# .env
SOURCE_DB_VIEW=vw_conversations_analytics_final
```

---

### **Passo 2: Atualizar src/features/etl_pipeline.py**

Criar nova versão otimizada do ETL:

```python
"""
ETL Pipeline V2: Extract from vw_conversations_analytics_final
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.shared.config import Config

load_dotenv()


def extract_from_source(limit=None, date_filter=None):
    """
    Extract data from vw_conversations_analytics_final

    Args:
        limit: Quantidade máxima de registros (para testes)
        date_filter: Filtrar por data (ex: "2025-10-01")

    Returns:
        DataFrame com dados extraídos
    """
    print("=" * 60)
    print("EXTRACT: Buscando dados da view analytics")
    print("=" * 60)

    try:
        conn_str = Config.get_source_connection_string()
        engine = create_engine(conn_str)

        # Base query
        query = f"SELECT * FROM {Config.SOURCE_DB_VIEW}"

        # Adicionar filtros
        filters = []

        if date_filter:
            filters.append(f"conversation_date >= '{date_filter}'")

        if filters:
            query += " WHERE " + " AND ".join(filters)

        # Adicionar ordem
        query += " ORDER BY conversation_created_at DESC"

        # Adicionar limit
        if limit:
            query += f" LIMIT {limit}"

        print(f"\nQuery: {query[:100]}...")
        print(f"\nExecutando extração...")

        df = pd.read_sql(query, engine)

        print(f"\n✓ Extraídos {len(df)} registros")
        print(f"✓ Total de colunas: {len(df.columns)}")

        # Mostrar algumas colunas importantes
        important_cols = [
            'conversation_id', 'status', 'contact_name',
            'inbox_name', 'csat_rating', 'first_response_time_minutes'
        ]

        available_cols = [col for col in important_cols if col in df.columns]

        if available_cols:
            print(f"\nPreview de colunas importantes:")
            print(df[available_cols].head())

        engine.dispose()
        return df

    except Exception as e:
        print(f"✗ Erro ao extrair dados: {e}")
        import traceback
        traceback.print_exc()
        return None


def transform_data(df):
    """
    Transform extracted data (optional transformations)

    Args:
        df: DataFrame extraído

    Returns:
        DataFrame transformado
    """
    if df is None or df.empty:
        return df

    print("\n" + "=" * 60)
    print("TRANSFORM: Aplicando transformações")
    print("=" * 60)

    # Criar cópia para não alterar original
    df_transformed = df.copy()

    # Transformações opcionais:

    # 1. Converter timestamps para datetime (se necessário)
    date_columns = [
        'conversation_created_at', 'conversation_updated_at',
        'first_message_at', 'last_message_at', 'csat_created_at'
    ]

    for col in date_columns:
        if col in df_transformed.columns:
            df_transformed[col] = pd.to_datetime(df_transformed[col], errors='coerce')

    # 2. Preencher valores nulos em campos numéricos
    numeric_columns = [
        'first_response_time_seconds', 'total_messages_public',
        'user_messages_count', 'contact_messages_count'
    ]

    for col in numeric_columns:
        if col in df_transformed.columns:
            df_transformed[col] = df_transformed[col].fillna(0)

    # 3. Garantir tipos corretos em flags booleanos
    boolean_columns = [
        'is_resolved', 'is_assigned', 'has_csat',
        'is_bot_resolved', 'has_human_intervention'
    ]

    for col in boolean_columns:
        if col in df_transformed.columns:
            df_transformed[col] = df_transformed[col].fillna(False).astype(bool)

    print(f"\n✓ Transformações aplicadas")
    print(f"✓ Shape final: {df_transformed.shape}")

    return df_transformed


def load_to_local(df):
    """
    Load data to local PostgreSQL database

    Args:
        df: DataFrame to load

    Returns:
        bool: Success status
    """
    if df is None or df.empty:
        print("✗ Sem dados para carregar")
        return False

    print("\n" + "=" * 60)
    print("LOAD: Carregando dados no banco local")
    print("=" * 60)

    try:
        local_conn_str = Config.get_local_connection_string()
        engine = create_engine(local_conn_str)

        table_name = Config.LOCAL_DB_TABLE

        # Estratégias de carregamento:

        # Opção 1: REPLACE (substitui tudo - mais simples)
        # df.to_sql(table_name, engine, if_exists='replace', index=False)

        # Opção 2: APPEND (adiciona dados - cuidado com duplicatas)
        # df.to_sql(table_name, engine, if_exists='append', index=False)

        # Opção 3: Truncate + Insert (recomendado para full refresh)
        print(f"\n  Truncando tabela {table_name}...")
        with engine.begin() as conn:
            conn.execute(f"TRUNCATE TABLE {table_name}")

        print(f"  Inserindo {len(df)} registros...")
        df.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )

        print(f"\n✓ {len(df)} registros carregados em {table_name}")

        # Verificar
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        result_df = pd.read_sql(count_query, engine)
        print(f"✓ Total na tabela: {result_df['total'][0]:,}")

        engine.dispose()
        return True

    except Exception as e:
        print(f"✗ Erro ao carregar dados: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_etl(limit=None, date_filter=None):
    """
    Run complete ETL pipeline

    Args:
        limit: Limit records for testing
        date_filter: Filter by date (YYYY-MM-DD)
    """
    print("\n" + "█" * 60)
    print("  ETL PIPELINE V2: vw_conversations_analytics_final")
    print("█" * 60 + "\n")

    # 1. Extract
    df = extract_from_source(limit=limit, date_filter=date_filter)

    if df is not None and not df.empty:
        # 2. Transform
        df_transformed = transform_data(df)

        # 3. Load
        success = load_to_local(df_transformed)

        # 4. Backup CSV (opcional)
        if success:
            backup_dir = Config.DATA_DIR
            os.makedirs(backup_dir, exist_ok=True)

            csv_file = f"{backup_dir}/conversas_analytics_latest.csv"
            df_transformed.to_csv(csv_file, index=False)
            print(f"\n✓ Backup CSV salvo: {csv_file}")

    print("\n" + "█" * 60)
    print("  ETL PIPELINE CONCLUÍDO")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    # Para testes: extrair apenas 100 registros dos últimos 7 dias
    run_etl(limit=100, date_filter='2025-10-10')

    # Para produção: extrair tudo
    # run_etl()
```

---

## 🧪 Testando o Novo ETL

### **1. Teste com dados limitados:**

```bash
cd /home/isaac/projects/allpfit-analytics

# Ativar ambiente virtual
source venv/bin/activate

# Rodar ETL com limite
./venv/bin/python -c "
from src.features.etl_pipeline import run_etl
run_etl(limit=10)
"
```

### **2. Teste com filtro de data:**

```python
# Extrair apenas últimos 7 dias
run_etl(date_filter='2025-10-10')
```

### **3. Teste completo:**

```python
# Extrair tudo (cuidado: pode ser muitos dados!)
run_etl()
```

---

## 📊 Criar Tabela no Banco Local

Antes de rodar o ETL, criar a tabela no banco local:

```sql
-- Conectar ao banco local
psql -U seu_usuario -d allpfit_analytics

-- Criar tabela (estrutura será criada automaticamente pelo pandas)
-- Ou criar manualmente para ter controle dos tipos:

CREATE TABLE conversas_lead (
    conversation_id INTEGER PRIMARY KEY,
    display_id INTEGER,
    status VARCHAR(50),
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    inbox_name VARCHAR(255),
    inbox_channel_type VARCHAR(50),
    assignee_name VARCHAR(255),
    csat_rating INTEGER,
    first_response_time_seconds INTEGER,
    first_response_time_minutes NUMERIC,
    is_bot_resolved BOOLEAN,
    has_human_intervention BOOLEAN,
    total_messages_public INTEGER,
    user_messages_count INTEGER,
    contact_messages_count INTEGER,
    conversation_date DATE,
    conversation_created_at TIMESTAMP,
    message_compiled JSONB,
    -- ... adicionar mais campos conforme necessário
    -- Ou deixar o pandas criar automaticamente
);

-- Criar índices para performance
CREATE INDEX idx_conversation_date ON conversas_lead(conversation_date);
CREATE INDEX idx_status ON conversas_lead(status);
CREATE INDEX idx_inbox_name ON conversas_lead(inbox_name);
CREATE INDEX idx_is_resolved ON conversas_lead(is_resolved);
```

---

## 🔄 Automação do ETL

### **Opção 1: Cron Job (Linux)**

```bash
# Editar crontab
crontab -e

# Adicionar linha para rodar a cada hora
0 * * * * cd /home/isaac/projects/allpfit-analytics && ./venv/bin/python -m src.features.etl_pipeline >> logs/etl.log 2>&1
```

### **Opção 2: Script Python com Schedule**

```python
# scripts/scheduler.py
import schedule
import time
from src.features.etl_pipeline import run_etl

def job():
    print("Iniciando ETL agendado...")
    run_etl()

# Rodar a cada hora
schedule.every().hour.do(job)

# Ou rodar todos os dias às 6h
# schedule.every().day.at("06:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## ✅ Checklist Pós-Implementação

- [ ] Config atualizado (.env + config.py)
- [ ] ETL atualizado (etl_pipeline.py)
- [ ] Banco local configurado (tabela criada)
- [ ] Teste com dados limitados (sucesso)
- [ ] Teste completo (sucesso)
- [ ] Verificar dados no banco local
- [ ] Configurar automação (cron/schedule)
- [ ] Dashboard pode consultar banco local

---

## 🎯 Próximo Passo

Após ETL funcionando:

1. ✅ Dados sendo extraídos e carregados no banco local
2. ✅ Criar dashboard Streamlit
3. ✅ Implementar os 60+ KPIs mapeados

**Documentação:** Ver `docs/create_dashboard.md` (próximo)

---

**Criado em:** 2025-10-17
**Versão:** 1.0
