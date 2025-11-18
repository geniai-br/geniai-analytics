#!/bin/bash

# Verificar se OPENAI_API_KEY está configurada
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERRO: OPENAI_API_KEY não configurada!"
    echo "Configure com: export OPENAI_API_KEY='sua-chave-aqui'"
    echo "Ou adicione no arquivo .env na raiz do projeto"
    exit 1
fi

# Diretório do projeto (assumindo que o script está em scripts/analysis/)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/analysis_log.txt"

echo "🚀 Iniciando análise contínua - $(date)" | tee -a "$LOG_FILE"
echo "Processando todos os leads pendentes em lotes de 50..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Loop até não haver mais leads pendentes
while true; do
    # Contar leads pendentes (apenas is_lead = true)
    PENDENTES=$(PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -h localhost -d geniai_analytics -t -c "SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = 16 AND is_lead = true AND tipo_conversa IS NULL;")
    
    echo "📊 Leads pendentes: $PENDENTES - $(date)" | tee -a "$LOG_FILE"

    if [ $PENDENTES -eq 0 ]; then
        echo "✅ Todos os leads foram processados!" | tee -a "$LOG_FILE"
        break
    fi

    # Executar análise de um lote
    cd "$PROJECT_ROOT" && venv/bin/python3 scripts/analysis/analyze_all_leads.py 2>&1 | tee -a "$LOG_FILE"

    # Pequena pausa entre lotes
    sleep 2
done

echo "🏁 Análise completa finalizada - $(date)" | tee -a "$LOG_FILE"
