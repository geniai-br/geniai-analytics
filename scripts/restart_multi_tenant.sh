#!/bin/bash

# ============================================================================
# Script de Restart do Dashboard Multi-Tenant (Porta 8504)
# FASE 2 - GeniAI Analytics
# ============================================================================
# SEGURO: Mata apenas Streamlit na porta 8504, não afeta SSH!
# ============================================================================

echo "🔄 Reiniciando Dashboard Multi-Tenant (Porta 8504)..."
echo ""

# Diretório do projeto
PROJECT_DIR="/home/tester/projetos/allpfit-analytics"
cd "$PROJECT_DIR" || exit 1

# ============================================================================
# STEP 1: Matar apenas processo Streamlit na porta 8504
# ============================================================================

echo "🔍 Procurando processo Streamlit na porta 8504..."

# Buscar apenas processo Streamlit que está em LISTEN na porta 8504
PID=$(lsof -i:8504 -sTCP:LISTEN -c streamlit -t 2>/dev/null)

if [ -n "$PID" ]; then
    echo "   ⚠️  Streamlit encontrado: PID $PID"
    echo "   🔪 Matando processo Streamlit..."

    # Tentar kill graceful primeiro (SIGTERM)
    kill -15 "$PID" 2>/dev/null

    # Aguardar 3 segundos
    sleep 3

    # Verificar se ainda está rodando
    if lsof -i:8504 -sTCP:LISTEN -c streamlit -t > /dev/null 2>&1; then
        echo "   💥 Processo resistiu, forçando kill (SIGKILL)..."
        kill -9 "$PID" 2>/dev/null
        sleep 2
    fi

    echo "   ✅ Streamlit encerrado"
else
    echo "   ℹ️  Nenhum Streamlit rodando na porta 8504"
fi

echo ""

# ============================================================================
# STEP 2: Verificar se porta está liberada
# ============================================================================

echo "🔍 Verificando se porta 8504 está liberada..."

# Verificar apenas se tem algo em LISTEN (servidor)
if lsof -i:8504 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "   ❌ Porta 8504 AINDA ocupada"
    echo "   📋 Processo em LISTEN:"
    lsof -i:8504 -sTCP:LISTEN
    exit 1
else
    echo "   ✅ Porta 8504 liberada (cliente Node.js é OK)"
fi

echo ""

# ============================================================================
# STEP 3: Iniciar Streamlit Multi-Tenant
# ============================================================================

echo "🚀 Iniciando Dashboard Multi-Tenant..."

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo "   ❌ Erro: venv não encontrado"
    echo "   💡 Execute: python3 -m venv venv"
    exit 1
fi

# Verificar se arquivo app.py existe
if [ ! -f "src/multi_tenant/dashboards/app.py" ]; then
    echo "   ❌ Erro: app.py não encontrado"
    exit 1
fi

# Iniciar Streamlit em background
echo "   📊 Streamlit iniciando em background..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
nohup venv/bin/streamlit run src/multi_tenant/dashboards/app.py \
    --server.port=8504 \
    --server.headless=true \
    --server.address=0.0.0.0 \
    --browser.gatherUsageStats=false \
    > logs/streamlit_multi_tenant_${TIMESTAMP}.log 2> logs/streamlit_debug_${TIMESTAMP}.log &

# Aguardar 3 segundos para startup
sleep 3

# ============================================================================
# STEP 4: Verificar se subiu
# ============================================================================

echo ""
echo "🔍 Verificando se subiu..."

if lsof -i:8504 > /dev/null 2>&1; then
    PID=$(lsof -ti:8504 -c streamlit 2>/dev/null)
    echo "   ✅ Streamlit rodando (PID: $PID)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ SUCESSO!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 Dashboard Multi-Tenant disponível em:"
    echo "   🌐 http://localhost:8504"
    echo ""
    echo "🔐 Credenciais de Teste:"
    echo "   • Super Admin: admin@geniai.com.br / senha123"
    echo "   • Admin AllpFit: isaac@allpfit.com.br / senha123"
    echo ""
    echo "📝 Logs em: logs/streamlit_multi_tenant_*.log"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "   ❌ Falha ao iniciar Streamlit"
    echo ""
    echo "💡 Verificar logs:"
    echo "   tail -f logs/streamlit_multi_tenant_*.log"
    exit 1
fi

echo ""
