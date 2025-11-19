#!/bin/bash

# Script de análise contínua - CDT Mossoró (tenant_id 14)
# Teste de validação em outro contexto de negócio

# Diretório do projeto
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/analysis_log.txt"

# Carregar .env se existir
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Verificar se OPENAI_API_KEY está configurada
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERRO: OPENAI_API_KEY não configurada!"
    echo "Configure com: export OPENAI_API_KEY='sua-chave-aqui'"
    echo "Ou adicione no arquivo .env na raiz do projeto"
    exit 1
fi

echo "🚀 Iniciando análise CDT Mossoró - $(date)" | tee -a "$LOG_FILE"
echo "Tenant ID: 14" | tee -a "$LOG_FILE"
echo "Processando todos os leads pendentes em lotes de 50..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Loop até não haver mais leads pendentes
while true; do
    # Contar leads pendentes ELEGÍVEIS (com filtro de 24h igual ao Python)
    PENDENTES=$(PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -h localhost -d geniai_analytics -t -c "SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = 14 AND is_lead = true AND tipo_conversa IS NULL AND mc_last_message_at < NOW() - INTERVAL '24 hours';")

    echo "📊 Leads pendentes CDT Mossoró: $PENDENTES - $(date)" | tee -a "$LOG_FILE"

    if [ $PENDENTES -eq 0 ]; then
        echo "✅ Todos os leads foram processados!" | tee -a "$LOG_FILE"
        break
    fi

    # Executar análise de um lote
    cd "$PROJECT_ROOT" && venv/bin/python3 scripts/testing/test_cdt_mossoro.py 2>&1 | tee -a "$LOG_FILE"

    # Pequena pausa entre lotes
    sleep 2
done

echo "🏁 Análise CDT Mossoró finalizada - $(date)" | tee -a "$LOG_FILE"