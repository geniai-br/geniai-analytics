#!/bin/bash
# Script de Monitoramento do ETL AllpFit Analytics

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  📊 MONITOR ETL - AllpFit Analytics"
echo "  🕐 Horários em: America/Sao_Paulo (SP)"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# 1. Status do Cron
echo "1️⃣  AGENDAMENTO (CRON)"
echo "────────────────────────────────────────────────────────────────────────────────"
crontab -l | grep -v "^#" | grep etl
echo ""

# 2. Próxima execução
echo "2️⃣  PRÓXIMA EXECUÇÃO"
echo "────────────────────────────────────────────────────────────────────────────────"
CURRENT_MINUTE=$(date +%M | sed 's/^0//')
CURRENT_HOUR=$(date +%H | sed 's/^0//')
NEXT_HOUR=$((CURRENT_HOUR + 1))
if [ $NEXT_HOUR -eq 24 ]; then
    NEXT_HOUR=0
fi
printf "   Agora: %s\n" "$(date '+%d/%m/%Y %H:%M:%S')"
printf "   Próxima: %s (em %d minutos)\n" "$(date '+%d/%m/%Y') ${NEXT_HOUR}:00:00" $((60 - CURRENT_MINUTE))
echo ""

# 3. Últimas 5 execuções
echo "3️⃣  ÚLTIMAS EXECUÇÕES (banco de dados)"
echo "────────────────────────────────────────────────────────────────────────────────"
PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -F'|' -c "
SELECT
    TO_CHAR(started_at - INTERVAL '3 hours', 'DD/MM HH24:MI:SS') || '|' ||
    CASE
        WHEN triggered_by = 'scheduler' THEN '🤖 Auto'
        WHEN triggered_by = 'manual' THEN '👤 Manual'
        ELSE triggered_by
    END || '|' ||
    CASE
        WHEN status = 'success' THEN '✅'
        WHEN status = 'failed' THEN '❌'
        ELSE '⏳'
    END || '|' ||
    COALESCE(rows_extracted::text, '0') || '|' ||
    COALESCE(rows_inserted::text, '0') || '|' ||
    COALESCE(rows_updated::text, '0') || '|' ||
    ROUND(COALESCE(duration_seconds, 0)::numeric, 2)::text || 's'
FROM etl_control
ORDER BY id DESC
LIMIT 5;
" | awk -F'|' 'BEGIN {
    printf "   %-17s  %-10s  %-4s  %5s  %5s  %5s  %8s\n", "Data/Hora", "Disparado", "Ok", "Extr", "Novo", "Updt", "Tempo"
    printf "   %.17s  %.10s  %.4s  %.5s  %.5s  %.5s  %.8s\n", "-----------------", "----------", "----", "-----", "-----", "-----", "--------"
}
{
    printf "   %-17s  %-10s  %-4s  %5s  %5s  %5s  %8s\n", $1, $2, $3, $4, $5, $6, $7
}'
echo ""

# 4. Status atual dos dados
echo "4️⃣  STATUS DOS DADOS"
echo "────────────────────────────────────────────────────────────────────────────────"
PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -c "
SELECT
    '   Total conversas: ' || COUNT(*)::text || '\n' ||
    '   Última conversa: ' || TO_CHAR(MAX(conversation_date), 'DD/MM/YYYY') || '\n' ||
    '   Última atualização ETL: ' || TO_CHAR(MAX(etl_updated_at) - INTERVAL '3 hours', 'DD/MM HH24:MI:SS') || ' (SP)' || '\n' ||
    '   Conversas hoje: ' || COUNT(CASE WHEN conversation_date = CURRENT_DATE THEN 1 END)::text
FROM conversas_analytics;
"
echo ""

# 5. Últimas linhas do log
echo "5️⃣  ÚLTIMAS LINHAS DO LOG (hoje)"
echo "────────────────────────────────────────────────────────────────────────────────"
LOG_TODAY="/home/isaac/projects/allpfit-analytics/logs/etl/etl_$(date +%Y%m%d).log"
if [ -f "$LOG_TODAY" ]; then
    echo "   📄 Arquivo: $LOG_TODAY"
    echo ""
    tail -5 "$LOG_TODAY" | sed 's/^/   /'
else
    echo "   ⚠️  Log de hoje ainda não foi criado"
fi
echo ""

# 6. Verificar se há erros recentes
echo "6️⃣  ERROS RECENTES"
echo "────────────────────────────────────────────────────────────────────────────────"
ERROR_COUNT=$(PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -c "
SELECT COUNT(*) FROM etl_control WHERE status = 'failed' AND started_at > NOW() - INTERVAL '24 hours';
")

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "   ❌ $ERROR_COUNT erro(s) nas últimas 24 horas"
    echo ""
    PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -t -A -c "
    SELECT
        '   ' || TO_CHAR(started_at - INTERVAL '3 hours', 'DD/MM HH24:MI') || ' (SP) - ' ||
        COALESCE(SUBSTRING(error_message, 1, 60), 'Sem mensagem')
    FROM etl_control
    WHERE status = 'failed' AND started_at > NOW() - INTERVAL '24 hours'
    ORDER BY started_at DESC
    LIMIT 3;
    "
else
    echo "   ✅ Nenhum erro nas últimas 24 horas"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Para ver log em tempo real: tail -f $LOG_TODAY"
echo "════════════════════════════════════════════════════════════════════════════════"
