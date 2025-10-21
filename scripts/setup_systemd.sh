#!/bin/bash
#
# Setup Systemd Timer for AllpFit ETL
#
# Este script:
# 1. Copia os arquivos .service e .timer para /etc/systemd/system/
# 2. Recarrega o systemd
# 3. Habilita e inicia o timer
#

set -e

echo "=================================================="
echo "  Configurando Systemd Timer para AllpFit ETL"
echo "=================================================="

PROJECT_DIR="/home/isaac/projects/allpfit-analytics"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script precisa ser executado como root"
    echo "   Use: sudo bash scripts/setup_systemd.sh"
    exit 1
fi

echo ""
echo "1️⃣  Copiando arquivos systemd..."

# Copiar service
cp "$PROJECT_DIR/systemd/allpfit-etl.service" /etc/systemd/system/
echo "   ✅ allpfit-etl.service copiado"

# Copiar timer
cp "$PROJECT_DIR/systemd/allpfit-etl.timer" /etc/systemd/system/
echo "   ✅ allpfit-etl.timer copiado"

echo ""
echo "2️⃣  Recarregando systemd daemon..."
systemctl daemon-reload
echo "   ✅ Daemon recarregado"

echo ""
echo "3️⃣  Habilitando timer (executar no boot)..."
systemctl enable allpfit-etl.timer
echo "   ✅ Timer habilitado"

echo ""
echo "4️⃣  Iniciando timer..."
systemctl start allpfit-etl.timer
echo "   ✅ Timer iniciado"

echo ""
echo "=================================================="
echo "  ✅ Configuração concluída!"
echo "=================================================="

echo ""
echo "📋 Informações:"
echo ""
echo "   Status do timer:"
echo "   $ systemctl status allpfit-etl.timer"
echo ""
echo "   Próximas execuções agendadas:"
echo "   $ systemctl list-timers allpfit-etl.timer"
echo ""
echo "   Executar manualmente:"
echo "   $ sudo systemctl start allpfit-etl.service"
echo ""
echo "   Ver logs:"
echo "   $ journalctl -u allpfit-etl.service -f"
echo ""
echo "   Parar timer:"
echo "   $ sudo systemctl stop allpfit-etl.timer"
echo ""

# Mostrar próximas execuções
echo "🕐 Próximas execuções agendadas:"
systemctl list-timers allpfit-etl.timer --no-pager

echo ""
echo "✅ ETL agendado para executar diariamente às 3:00 AM"
