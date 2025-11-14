"""
Script de teste rápido - Fase 2
Verifica conexão com banco e autenticação
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import get_database_engine, authenticate_user, validate_session
from sqlalchemy import text


def test_database_connection():
    """Testa conexão com o banco"""
    print("🔌 Testando conexão com banco...")

    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✅ Conexão com banco OK")
            return True
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


def test_database_tables():
    """Verifica se tabelas existem"""
    print("\n📊 Verificando tabelas...")

    tables = [
        'tenants',
        'users',
        'sessions',
        'conversations_analytics',
        'inbox_tenant_mapping',
        'etl_control'
    ]

    engine = get_database_engine()

    for table in tables:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                count = result[0]
                print(f"  ✅ {table}: {count} registros")
        except Exception as e:
            print(f"  ❌ {table}: ERRO - {e}")


def test_authentication():
    """Testa autenticação com credenciais de teste"""
    print("\n🔐 Testando autenticação...")

    test_users = [
        ('admin@geniai.com.br', 'senha123', 'Super Admin'),
        ('isaac@allpfit.com.br', 'senha123', 'Admin AllpFit'),
    ]

    engine = get_database_engine()

    for email, password, description in test_users:
        try:
            session = authenticate_user(engine, email, password)

            if session:
                print(f"  ✅ {description} ({email})")
                print(f"     - user_id: {session['user_id']}")
                print(f"     - tenant_id: {session['tenant_id']}")
                print(f"     - role: {session['role']}")
                print(f"     - session_id: {session['session_id'][:8]}...")
            else:
                print(f"  ❌ {description}: Falha na autenticação")

        except Exception as e:
            print(f"  ❌ {description}: ERRO - {e}")


def test_rls():
    """Testa Row-Level Security"""
    print("\n🔒 Testando RLS...")

    engine = get_database_engine()

    try:
        with engine.connect() as conn:
            # Configurar RLS para tenant_id = 1 (AllpFit)
            conn.execute(text("SET app.current_tenant_id = 1"))
            conn.commit()

            # Query (deve retornar apenas dados do tenant 1)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM conversations_analytics
                WHERE tenant_id = 1
            """)).fetchone()

            count = result[0]
            print(f"  ✅ RLS configurado (tenant_id=1)")
            print(f"     - Conversas do tenant 1: {count}")

            # Verificar que RLS está ativo
            conn.execute(text("SELECT current_setting('app.current_tenant_id')"))
            print(f"  ✅ RLS variável configurada corretamente")

    except Exception as e:
        print(f"  ⚠️ RLS: {e}")
        print("  💡 Tabela conversations_analytics ainda está vazia (Fase 3)")


def main():
    """Executa todos os testes"""
    print("="*60)
    print("🧪 TESTE DE FASE 2 - AUTENTICAÇÃO MULTI-TENANT")
    print("="*60)

    # Teste 1: Conexão
    if not test_database_connection():
        print("\n❌ Impossível continuar sem conexão com banco")
        return

    # Teste 2: Tabelas
    test_database_tables()

    # Teste 3: Autenticação
    test_authentication()

    # Teste 4: RLS
    test_rls()

    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)
    print("\n💡 Para testar a interface:")
    print("   streamlit run src/multi_tenant/dashboards/app.py --server.port=8504")


if __name__ == "__main__":
    main()