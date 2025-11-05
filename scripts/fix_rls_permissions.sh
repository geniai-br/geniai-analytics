#!/bin/bash
# Fix RLS permissions for isaac user
# This script must be run as postgres superuser or a user with CREATEROLE privileges

echo "================================================"
echo "FIX RLS PERMISSIONS - GeniAI Analytics"
echo "================================================"
echo ""
echo "Este script corrige as permissões RLS para o usuário 'isaac'"
echo "permitindo que a autenticação funcione corretamente."
echo ""
echo "OPÇÃO 1: Executar via sudo (recomendado)"
echo "  sudo -u postgres psql -d geniai_analytics -f fix_rls_permissions.sh"
echo ""
echo "OPÇÃO 2: Executar como superuser postgres"
echo "  psql -U postgres -d geniai_analytics"
echo "  Depois cole os comandos SQL abaixo:"
echo ""
echo "================================================"
echo "COMANDOS SQL:"
echo "================================================"
cat << 'EOF'

-- Opção A: Dar permissão BYPASSRLS para isaac (mais seguro para app)
ALTER ROLE isaac BYPASSRLS;

-- OU Opção B: Adicionar isaac aos roles necessários
GRANT admin_users TO isaac;
GRANT authenticated_users TO isaac;

-- Verificar se funcionou
SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'isaac';

-- Deve mostrar: isaac | t (true)

EOF

echo ""
echo "================================================"
echo "EXECUTANDO FIX AUTOMATICAMENTE..."
echo "================================================"
echo ""

# Tentar executar como postgres
if [ "$EUID" -eq 0 ]; then
    # Running as root, use sudo
    sudo -u postgres psql -d geniai_analytics << 'SQLEOF'
ALTER ROLE isaac BYPASSRLS;
SELECT 'SUCCESS: isaac agora tem BYPASSRLS' AS status;
SQLEOF
else
    # Try to run directly
    psql -U postgres -d geniai_analytics << 'SQLEOF'
ALTER ROLE isaac BYPASSRLS;
SELECT 'SUCCESS: isaac agora tem BYPASSRLS' AS status;
SQLEOF
fi

echo ""
echo "================================================"
echo "TESTE: Verificando permissões..."
echo "================================================"
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics -c "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'isaac';"

echo ""
echo "Se rolbypassrls = t, o fix foi aplicado com sucesso!"
echo "Agora você pode testar o login novamente."