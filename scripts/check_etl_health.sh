#!/bin/bash
#
# Verificar saúde do ETL
#
# Este script verifica:
# - Status do timer systemd
# - Última execução
# - Logs de erro
# - Estatísticas do banco
#

set -e

PROJECT_DIR="/home/isaac/projects/allpfit-analytics"

echo "=================================================="
echo "  ETL Health Check - AllpFit Analytics"
echo "=================================================="

echo ""
echo "1️⃣  Status do Timer Systemd:"
echo "-----------------------------------"
systemctl status allpfit-etl.timer --no-pager || true

echo ""
echo "2️⃣  Próximas Execuções:"
echo "-----------------------------------"
systemctl list-timers allpfit-etl.timer --no-pager || echo "Timer não está ativo"

echo ""
echo "3️⃣  Última Execução (systemd):"
echo "-----------------------------------"
journalctl -u allpfit-etl.service -n 20 --no-pager || echo "Nenhum log encontrado"

echo ""
echo "4️⃣  Estatísticas do ETL (banco de dados):"
echo "-----------------------------------"
psql -U isaac -d allpfit -c "
SELECT
    id,
    started_at,
    status,
    load_type,
    rows_extracted,
    rows_inserted,
    rows_updated,
    duration_seconds
FROM etl_control
ORDER BY started_at DESC
LIMIT 5;
" || echo "Erro ao consultar banco"

echo ""
echo "5️⃣  Total de Conversas no Banco Local:"
echo "-----------------------------------"
psql -U isaac -d allpfit -c "
SELECT COUNT(*) as total_conversas FROM conversas_analytics;
" || echo "Erro ao consultar banco"

echo ""
echo "=================================================="
echo "  Health Check Concluído"
echo "=================================================="
