#!/bin/bash
#
# Restart Dashboard - AllpFit Analytics
#
# Este script reinicia o dashboard Streamlit em produção
#

set -e

PROJECT_DIR="/home/isaac/projects/allpfit-analytics"

echo "=================================================="
echo "  Reiniciando Dashboard AllpFit Analytics"
echo "=================================================="

cd "$PROJECT_DIR"

echo ""
echo "1️⃣  Parando processo Streamlit atual..."

# Encontrar e matar processo streamlit
PIDS=$(ps aux | grep "streamlit run src/app/dashboard.py" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "   ⚠️  Nenhum processo Streamlit rodando"
else
    for PID in $PIDS; do
        kill $PID
        echo "   ✅ Processo $PID finalizado"
    done
    sleep 2
fi

echo ""
echo "2️⃣  Limpando cache Python..."
find src/app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find src/app -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Cache limpo"

echo ""
echo "3️⃣  Iniciando novo processo Streamlit..."

# Ativar virtualenv e iniciar streamlit
source venv/bin/activate

# Iniciar streamlit em background
nohup streamlit run src/app/dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    > logs/dashboard.log 2>&1 &

NEW_PID=$!

sleep 3

echo "   ✅ Dashboard iniciado (PID: $NEW_PID)"

echo ""
echo "4️⃣  Verificando saúde..."

# Aguardar até 10 segundos para o servidor iniciar
for i in {1..10}; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "   ✅ Dashboard online e respondendo!"
        break
    fi
    echo "   ⏳ Aguardando inicialização... ($i/10)"
    sleep 1
done

echo ""
echo "=================================================="
echo "  ✅ Dashboard Reiniciado com Sucesso!"
echo "=================================================="

echo ""
echo "📊 URLs:"
echo "   Local:     http://localhost:8501"
echo "   Produção:  https://analytcs.geniai.online"
echo ""
echo "📝 Logs:"
echo "   tail -f logs/dashboard.log"
echo ""
echo "🔍 Processos:"
echo "   ps aux | grep streamlit"
echo ""
