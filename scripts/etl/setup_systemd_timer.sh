#!/bin/bash

# ============================================================================
# Script de Setup do Systemd Timer para ETL GeniAI Analytics
# ============================================================================
# Instala e configura execução automática do ETL a cada 30 minutos
# ============================================================================

set -e  # Exit on error

PROJECT_DIR="/home/tester/projetos/geniai-analytics"
SERVICE_NAME="etl-geniai"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Setup Systemd Timer - ETL GeniAI Analytics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# Verificar se está rodando como root
# ============================================================================

if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script precisa ser executado como root (sudo)"
    echo "   Execute: sudo bash scripts/etl/setup_systemd_timer.sh"
    exit 1
fi

# ============================================================================
# Verificar se arquivos existem
# ============================================================================

echo "🔍 Verificando arquivos..."

if [ ! -f "$PROJECT_DIR/systemd/${SERVICE_NAME}.service" ]; then
    echo "❌ Erro: Arquivo ${SERVICE_NAME}.service não encontrado"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/systemd/${SERVICE_NAME}.timer" ]; then
    echo "❌ Erro: Arquivo ${SERVICE_NAME}.timer não encontrado"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/src/multi_tenant/etl_v4/run_all_tenants.py" ]; then
    echo "❌ Erro: Script run_all_tenants.py não encontrado"
    exit 1
fi

echo "✅ Todos os arquivos encontrados"
echo ""

# ============================================================================
# Tornar script Python executável
# ============================================================================

echo "🔧 Tornando script Python executável..."
chmod +x "$PROJECT_DIR/src/multi_tenant/etl_v4/run_all_tenants.py"
echo "✅ Script Python executável"
echo ""

# ============================================================================
# Copiar arquivos para systemd
# ============================================================================

echo "📋 Copiando arquivos para /etc/systemd/system/..."

cp "$PROJECT_DIR/systemd/${SERVICE_NAME}.service" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/${SERVICE_NAME}.timer" /etc/systemd/system/

echo "✅ Arquivos copiados"
echo ""

# ============================================================================
# Recarregar systemd
# ============================================================================

echo "🔄 Recarregando systemd..."
systemctl daemon-reload
echo "✅ Systemd recarregado"
echo ""

# ============================================================================
# Habilitar e iniciar timer
# ============================================================================

echo "⚡ Habilitando e iniciando timer..."

# Habilitar para iniciar automaticamente no boot
systemctl enable ${SERVICE_NAME}.timer

# Iniciar timer agora
systemctl start ${SERVICE_NAME}.timer

echo "✅ Timer habilitado e iniciado"
echo ""

# ============================================================================
# Verificar status
# ============================================================================

echo "🔍 Verificando status..."
echo ""

systemctl status ${SERVICE_NAME}.timer --no-pager || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SETUP CONCLUÍDO COM SUCESSO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 ETL configurado para rodar automaticamente a cada 30 minutos"
echo ""
echo "📝 Comandos úteis:"
echo "   • Ver status do timer:       systemctl status ${SERVICE_NAME}.timer"
echo "   • Ver logs:                  journalctl -u ${SERVICE_NAME}.service -f"
echo "   • Ver próximas execuções:    systemctl list-timers ${SERVICE_NAME}.timer"
echo "   • Executar manualmente:      systemctl start ${SERVICE_NAME}.service"
echo "   • Parar timer:               systemctl stop ${SERVICE_NAME}.timer"
echo "   • Desabilitar timer:         systemctl disable ${SERVICE_NAME}.timer"
echo ""
echo "🎯 Próxima execução em:"
systemctl list-timers ${SERVICE_NAME}.timer --no-pager | grep ${SERVICE_NAME}
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
