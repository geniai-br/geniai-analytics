#!/bin/bash
# Status rápido do ETL (versão simplificada)

echo ""
echo "🔄 ETL Status:"
PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -c "
SELECT
    '   Última execução: ' || TO_CHAR(MAX(started_at), 'DD/MM HH24:MI') || ' (' ||
    CASE
        WHEN MAX(started_at) > NOW() - INTERVAL '2 hours' THEN '✅ OK'
        ELSE '⚠️  ATRASADO'
    END || ')'
FROM etl_control WHERE status = 'success';
"

PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -c "
SELECT
    '   Total conversas: ' || COUNT(*) ||
    ' | Última: ' || TO_CHAR(MAX(conversation_date), 'DD/MM')
FROM conversas_analytics;
"

echo ""
