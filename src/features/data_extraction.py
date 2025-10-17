"""
Data extraction module for pulling data from PostgreSQL views
"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import DatabaseConnection

# Load environment variables
load_dotenv()


def extract_conversas_por_lead():
    """Extract data from vw_conversas_por_lead view (source database)"""
    view_name = os.getenv('SOURCE_DB_VIEW', 'vw_conversas_por_lead')

    print(f"Starting data extraction from view: {view_name}")
    print("-" * 50)

    with DatabaseConnection(db_type='source') as db:
        # Query to select all data from the view
        query = f"SELECT * FROM {view_name};"

        # Execute query
        results = db.execute_query(query)

        if results:
            # Convert to pandas DataFrame
            df = pd.DataFrame(results)

            print(f"\n✓ Data extracted successfully!")
            print(f"  - Rows: {len(df)}")
            print(f"  - Columns: {len(df.columns)}")
            print(f"\nColumns: {', '.join(df.columns.tolist())}")
            print(f"\nFirst 5 rows preview:")
            print(df.head())

            return df
        else:
            print("✗ No data extracted")
            return None


def load_to_local_database(df):
    """Load DataFrame into local PostgreSQL database"""
    if df is None or df.empty:
        print("✗ No data to load")
        return False

    table_name = os.getenv('LOCAL_DB_TABLE', 'conversas_lead')

    print(f"\nLoading data to local database table: {table_name}")
    print("-" * 50)

    with DatabaseConnection(db_type='local') as db:
        # Prepare insert query
        columns = ['conversation_id', 'message_compiled', 'client_sender_id',
                   'inbox_id', 'client_phone', 't_messages']

        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
        """

        # Prepare data for batch insert
        data = [tuple(row[col] for col in columns) for _, row in df.iterrows()]

        # Execute batch insert
        success = db.execute_insert(insert_query, data)

        if success:
            print(f"✓ Successfully loaded {len(data)} rows into {table_name}")
            return True
        else:
            print(f"✗ Failed to load data into {table_name}")
            return False


def run_etl_pipeline():
    """Run complete ETL pipeline: Extract from source, Load to local"""
    print("=" * 50)
    print("ETL Pipeline: Source → Local Database")
    print("=" * 50)

    # Extract
    df = extract_conversas_por_lead()

    if df is not None:
        # Load to local database
        load_to_local_database(df)

        # Optionally save to CSV backup
        output_file = "data/conversas_por_lead.csv"
        os.makedirs("data", exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n✓ Backup saved to: {output_file}")

    print("\n" + "=" * 50)
    print("ETL Pipeline completed!")
    print("=" * 50)


if __name__ == "__main__":
    run_etl_pipeline()
