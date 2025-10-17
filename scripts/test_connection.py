"""
Script para testar conexão com o banco de dados externo
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def test_connection():
    print("=" * 60)
    print("TESTE DE CONEXÃO - Banco Externo (Source)")
    print("=" * 60)

    host = os.getenv('SOURCE_DB_HOST')
    port = os.getenv('SOURCE_DB_PORT')
    database = os.getenv('SOURCE_DB_NAME')
    user = os.getenv('SOURCE_DB_USER')
    password = os.getenv('SOURCE_DB_PASSWORD')
    view_name = os.getenv('SOURCE_DB_VIEW')

    print(f"\nConexão:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  User: {user}")
    print(f"  View: {view_name}")

    try:
        print("\n⏳ Conectando...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )

        print("✓ Conexão estabelecida com sucesso!\n")

        cursor = conn.cursor()

        # Teste 1: Verificar se a view existe
        print(f"📊 Testando acesso à view '{view_name}'...")
        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]
        print(f"✓ View acessível! Total de registros: {count}\n")

        # Teste 2: Buscar amostra de dados
        print("📋 Buscando amostra de 3 registros...")
        cursor.execute(f"SELECT * FROM {view_name} LIMIT 3")
        rows = cursor.fetchall()

        if rows:
            # Pegar nomes das colunas
            colnames = [desc[0] for desc in cursor.description]
            print(f"✓ Colunas encontradas: {', '.join(colnames)}\n")

            print("Primeiros registros:")
            for i, row in enumerate(rows, 1):
                print(f"\nRegistro {i}:")
                for col, val in zip(colnames, row):
                    # Limitar tamanho da exibição
                    val_str = str(val)
                    if len(val_str) > 50:
                        val_str = val_str[:50] + "..."
                    print(f"  {col}: {val_str}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✓ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        print("\n" + "=" * 60)
        print("✗ TESTE FALHOU")
        print("=" * 60)

if __name__ == "__main__":
    test_connection()
