"""
Database connection module for PostgreSQL
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConnection:
    """PostgreSQL database connection manager"""

    def __init__(self, db_type='source'):
        """
        Initialize database connection

        Args:
            db_type: 'source' for remote read-only or 'local' for local write database
        """
        if db_type == 'source':
            self.host = os.getenv('SOURCE_DB_HOST')
            self.port = os.getenv('SOURCE_DB_PORT')
            self.database = os.getenv('SOURCE_DB_NAME')
            self.user = os.getenv('SOURCE_DB_USER')
            self.password = os.getenv('SOURCE_DB_PASSWORD')
        elif db_type == 'local':
            self.host = os.getenv('LOCAL_DB_HOST')
            self.port = os.getenv('LOCAL_DB_PORT')
            self.database = os.getenv('LOCAL_DB_NAME')
            self.user = os.getenv('LOCAL_DB_USER')
            self.password = os.getenv('LOCAL_DB_PASSWORD') or None
        else:
            raise ValueError("db_type must be 'source' or 'local'")

        self.db_type = db_type
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            conn_params = {
                'database': self.database,
                'user': self.user,
            }

            # For local connections without password, use Unix socket
            if self.db_type == 'local' and not self.password:
                # Use Unix socket for local peer authentication
                conn_params['host'] = '/var/run/postgresql'
            else:
                # Use TCP/IP for remote connections
                conn_params['host'] = self.host
                conn_params['port'] = self.port
                if self.password:
                    conn_params['password'] = self.password

            self.connection = psycopg2.connect(**conn_params)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            print(f"✓ Connected to {self.db_type} database: {self.database}")
            return True
        except Exception as e:
            print(f"✗ Error connecting to database: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print(f"✓ {self.db_type.capitalize()} database connection closed")

    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results"""
        try:
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            print(f"✗ Error executing query: {e}")
            return None

    def execute_insert(self, query, data):
        """Execute INSERT query with data"""
        try:
            execute_batch(self.cursor, query, data)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"✗ Error inserting data: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
