#!/bin/bash

# Script de rotação de logs - GeniAI Analytics
# Execução recomendada: diária via cron

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"

echo "🔄 Iniciando rotação de logs - $(date)"

# 1. Rotacionar analysis_log.txt se > 10MB
ANALYSIS_LOG="$LOGS_DIR/analysis_log.txt"
if [ -f "$ANALYSIS_LOG" ]; then
    SIZE=$(stat -f%z "$ANALYSIS_LOG" 2>/dev/null || stat -c%s "$ANALYSIS_LOG" 2>/dev/null)

    if [ "$SIZE" -gt 10485760 ]; then  # 10MB
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        echo "  📦 Rotacionando analysis_log.txt ($(numfmt --to=iec-i --suffix=B $SIZE))"

        # Comprimir e arquivar
        gzip -c "$ANALYSIS_LOG" > "$LOGS_DIR/analysis_log_${TIMESTAMP}.txt.gz"

        # Limpar arquivo original
        > "$ANALYSIS_LOG"

        echo "  ✅ Criado: analysis_log_${TIMESTAMP}.txt.gz"
    else
        echo "  ℹ️  analysis_log.txt ainda pequeno ($(numfmt --to=iec-i --suffix=B $SIZE))"
    fi
fi

# 2. Remover logs do Streamlit antigos (> 7 dias)
REMOVED=$(find "$LOGS_DIR" -name "streamlit_*.log" -type f -mtime +7 -delete -print | wc -l)
if [ "$REMOVED" -gt 0 ]; then
    echo "  🗑️  Removidos $REMOVED logs do Streamlit (> 7 dias)"
fi

# 3. Remover logs do Streamlit vazios
REMOVED_EMPTY=$(find "$LOGS_DIR" -name "streamlit_*.log" -type f -size 0 -delete -print | wc -l)
if [ "$REMOVED_EMPTY" -gt 0 ]; then
    echo "  🗑️  Removidos $REMOVED_EMPTY logs vazios do Streamlit"
fi

# 4. Remover logs comprimidos antigos (> 90 dias)
REMOVED_GZ=$(find "$LOGS_DIR" -name "*.gz" -type f -mtime +90 -delete -print | wc -l)
if [ "$REMOVED_GZ" -gt 0 ]; then
    echo "  🗑️  Removidos $REMOVED_GZ logs comprimidos (> 90 dias)"
fi

# 5. Relatório final
TOTAL_FILES=$(find "$LOGS_DIR" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$LOGS_DIR" | awk '{print $1}')

echo ""
echo "📊 Resumo:"
echo "  Arquivos restantes: $TOTAL_FILES"
echo "  Espaço usado: $TOTAL_SIZE"
echo ""
echo "✅ Rotação de logs concluída - $(date)"