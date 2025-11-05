"""
Teste do fluxo de login completo
"""
import sys
from pathlib import Path

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import authenticate_user, validate_session, get_database_engine

def test_login_flow():
    """Testa fluxo completo de login"""

    print("\n" + "="*60)
    print("TESTE DE FLUXO DE LOGIN")
    print("="*60 + "\n")

    # Teste 1: Autenticar
    print("1. Testando autenticação...")
    engine = get_database_engine()

    email = "admin@geniai.com.br"
    password = "senha123"

    print(f"   Email: {email}")
    print(f"   Password: {password}")

    session_data = authenticate_user(engine, email, password)

    if not session_data:
        print("   ❌ FALHOU: authenticate_user retornou None")
        return False

    print(f"   ✅ Autenticado!")
    print(f"   session_id: {session_data['session_id']}")
    print(f"   user_id: {session_data['user_id']}")
    print(f"   tenant_id: {session_data['tenant_id']}")
    print(f"   role: {session_data['role']}")
    print(f"   full_name: {session_data['full_name']}")

    # Teste 2: Validar sessão
    print("\n2. Testando validação de sessão...")
    session_id = session_data['session_id']

    validated_session = validate_session(engine, session_id)

    if not validated_session:
        print(f"   ❌ FALHOU: validate_session retornou None para session_id={session_id}")
        return False

    print(f"   ✅ Sessão validada!")
    print(f"   user_id: {validated_session['user_id']}")
    print(f"   role: {validated_session['role']}")

    # Teste 3: Verificar dados no banco
    print("\n3. Verificando sessão no banco...")
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, user_id, tenant_id, expires_at FROM sessions WHERE id = :sid"),
            {'sid': session_id}
        ).fetchone()

        if not result:
            print(f"   ❌ FALHOU: Sessão não encontrada no banco")
            return False

        print(f"   ✅ Sessão existe no banco!")
        print(f"   session_id (db): {result.id}")
        print(f"   user_id (db): {result.user_id}")
        print(f"   tenant_id (db): {result.tenant_id}")
        print(f"   expires_at (db): {result.expires_at}")

    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60 + "\n")

    return True

if __name__ == "__main__":
    success = test_login_flow()
    sys.exit(0 if success else 1)