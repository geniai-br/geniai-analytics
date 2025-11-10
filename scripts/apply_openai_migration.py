"""
Apply OpenAI Migration
=======================

Script para aplicar migration 008_add_openai_support.sql

Usage:
    python scripts/apply_openai_migration.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco remoto
REMOTE_DB_HOST = os.getenv('REMOTE_DB_HOST')
REMOTE_DB_PORT = os.getenv('REMOTE_DB_PORT', '5432')
REMOTE_DB_NAME = os.getenv('REMOTE_DB_NAME')
REMOTE_DB_USER = os.getenv('REMOTE_DB_USER')
REMOTE_DB_PASSWORD = os.getenv('REMOTE_DB_PASSWORD')


def get_remote_engine():
    """Cria engine para banco remoto"""
    from urllib.parse import quote_plus
    password_encoded = quote_plus(REMOTE_DB_PASSWORD)
    connection_string = f"postgresql://{REMOTE_DB_USER}:{password_encoded}@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{REMOTE_DB_NAME}"
    return create_engine(connection_string)


def apply_migration():
    """Aplica migration 008_add_openai_support.sql"""

    # Ler arquivo SQL
    migration_file = Path(__file__).parent.parent / 'migrations' / '008_add_openai_support.sql'

    if not migration_file.exists():
        print(f"❌ Arquivo não encontrado: {migration_file}")
        return False

    print(f"📄 Lendo migration: {migration_file}")
    sql_content = migration_file.read_text()

    # Conectar ao banco
    print(f"🔗 Conectando ao banco: {REMOTE_DB_HOST}...")
    engine = get_remote_engine()

    try:
        with engine.connect() as conn:
            # Executar migration
            print("⚙️  Executando migration...")

            # Dividir em statements (split por comentários e comandos)
            statements = []
            current_statement = []

            for line in sql_content.split('\n'):
                # Ignorar comentários e linhas vazias
                if line.strip().startswith('--') or not line.strip():
                    continue

                current_statement.append(line)

                # Se linha termina com ;, é fim do statement
                if line.strip().endswith(';'):
                    stmt = '\n'.join(current_statement)
                    statements.append(stmt)
                    current_statement = []

            # Executar cada statement
            for i, stmt in enumerate(statements, 1):
                try:
                    print(f"  [{i}/{len(statements)}] Executando statement...")
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as e:
                    # Alguns statements podem já existir (OK)
                    if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                        print(f"  ⚠️  Statement {i} já aplicado (OK)")
                    else:
                        print(f"  ❌ Erro no statement {i}: {e}")
                        raise

            print("✅ Migration aplicada com sucesso!")

            # Verificar resultados
            print("\n📊 Verificando configuração dos tenants...")
            result = conn.execute(text("""
                SELECT
                    tenant_id,
                    tenant_name,
                    features->>'use_openai' as openai_enabled
                FROM tenant_configs
                ORDER BY tenant_id
            """))

            for row in result:
                tenant_id, tenant_name, openai_enabled = row
                emoji = "🔴" if openai_enabled == 'false' or not openai_enabled else "🟢"
                print(f"  {emoji} Tenant {tenant_id} ({tenant_name}): use_openai = {openai_enabled}")

            # Verificar novas colunas em etl_control
            print("\n📊 Verificando novas colunas em etl_control...")
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'etl_control'
                AND column_name LIKE 'openai%'
                ORDER BY ordinal_position
            """))

            for row in result:
                column_name, data_type = row
                print(f"  ✅ {column_name} ({data_type})")

            print("\n🎉 Migration completa!")
            return True

    except Exception as e:
        print(f"\n❌ Erro ao aplicar migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("  APPLY OPENAI MIGRATION - 008_add_openai_support.sql")
    print("=" * 80)
    print()

    success = apply_migration()

    if success:
        print("\n✅ SUCCESS - Migration aplicada com sucesso!")
    else:
        print("\n❌ FAILED - Erro ao aplicar migration")
        exit(1)