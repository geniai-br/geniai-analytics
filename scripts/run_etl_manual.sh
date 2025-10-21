#!/bin/bash
#
# Executar ETL manualmente
#
# Uso:
#   bash scripts/run_etl_manual.sh          # Incremental
#   bash scripts/run_etl_manual.sh --full   # Carga completa
#

set -e

PROJECT_DIR="/home/isaac/projects/allpfit-analytics"

cd "$PROJECT_DIR"

echo "=================================================="
echo "  Executando ETL AllpFit Analytics (MANUAL)"
echo "=================================================="

# Ativar virtualenv
source venv/bin/activate

# Executar ETL
python3 src/features/etl_pipeline_v3.py --triggered-by manual "$@"

echo ""
echo "✅ ETL concluído!"
echo ""
echo "📊 Ver estatísticas:"
echo "   psql -U isaac -d allpfit -c 'SELECT * FROM vw_etl_stats LIMIT 5;'"
