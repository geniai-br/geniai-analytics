"""
ETL Pipeline: Extract from remote PostgreSQL, Load to local PostgreSQL
Uses SQLAlchemy + pandas for simpler database operations
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def extract_from_source():
    """Extract data from remote PostgreSQL source"""
    print("=" * 60)
    print("EXTRACT: Getting data from source database")
    print("=" * 60)

    # Source database connection string
    source_conn_str = f"postgresql://{os.getenv('SOURCE_DB_USER')}:{os.getenv('SOURCE_DB_PASSWORD')}@{os.getenv('SOURCE_DB_HOST')}:{os.getenv('SOURCE_DB_PORT')}/{os.getenv('SOURCE_DB_NAME')}"

    try:
        engine = create_engine(source_conn_str)
        view_name = os.getenv('SOURCE_DB_VIEW', 'vw_conversas_por_lead')

        query = f"SELECT * FROM {view_name}"
        df = pd.read_sql(query, engine)

        # Convert message_compiled from dict/json to string if needed
        if 'message_compiled' in df.columns:
            df['message_compiled'] = df['message_compiled'].astype(str)

        print(f"\n✓ Extracted {len(df)} rows from {view_name}")
        print(f"✓ Columns: {', '.join(df.columns.tolist())}")
        print(f"\nPreview:")
        print(df.head())

        engine.dispose()
        return df

    except Exception as e:
        print(f"✗ Error extracting data: {e}")
        return None


def load_to_local(df):
    """Load data to local PostgreSQL database"""
    if df is None or df.empty:
        print("✗ No data to load")
        return False

    print("\n" + "=" * 60)
    print("LOAD: Inserting data into local database")
    print("=" * 60)

    # Local database connection string (using Unix socket with specific port)
    local_user = os.getenv('LOCAL_DB_USER')
    local_db = os.getenv('LOCAL_DB_NAME')
    local_port = os.getenv('LOCAL_DB_PORT')
    local_table = os.getenv('LOCAL_DB_TABLE', 'conversas_lead')

    # Connection string for local database (Unix socket with port)
    local_conn_str = f"postgresql://{local_user}@/{local_db}?host=/var/run/postgresql&port={local_port}"

    try:
        engine = create_engine(local_conn_str)

        # Write to database
        df.to_sql(
            local_table,
            engine,
            if_exists='append',  # append data to existing table
            index=False,
            method='multi'  # faster batch insert
        )

        print(f"\n✓ Successfully loaded {len(df)} rows into {local_table}")

        # Verify
        count_query = f"SELECT COUNT(*) as total FROM {local_table}"
        result = pd.read_sql(count_query, engine)
        print(f"✓ Total rows in {local_table}: {result['total'][0]}")

        engine.dispose()
        return True

    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return False


def run_etl():
    """Run complete ETL pipeline"""
    print("\n" + "█" * 60)
    print("  ETL PIPELINE: Source → Local Database")
    print("█" * 60 + "\n")

    # Extract
    df = extract_from_source()

    if df is not None:
        # Load
        success = load_to_local(df)

        # Backup to CSV
        if success:
            output_dir = "data"
            os.makedirs(output_dir, exist_ok=True)
            csv_file = f"{output_dir}/conversas_por_lead.csv"
            df.to_csv(csv_file, index=False)
            print(f"\n✓ Backup saved to: {csv_file}")

    print("\n" + "█" * 60)
    print("  ETL PIPELINE COMPLETED")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    run_etl()
