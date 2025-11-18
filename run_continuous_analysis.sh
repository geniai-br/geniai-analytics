#!/bin/bash
export OPENAI_API_KEY='***REMOVED***'

echo "🚀 Iniciando análise contínua - $(date)" | tee -a analysis_log.txt
echo "Processando todos os leads pendentes em lotes de 50..." | tee -a analysis_log.txt
echo "" | tee -a analysis_log.txt

# Loop até não haver mais leads pendentes
while true; do
    # Contar leads pendentes (apenas is_lead = true)
    PENDENTES=$(PGPASSWORD='vlVMVM6UNz2yYSBlzodPjQvZh' psql -U johan_geniai -h localhost -d geniai_analytics -t -c "SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = 16 AND is_lead = true AND tipo_conversa IS NULL;")
    
    echo "📊 Leads pendentes: $PENDENTES - $(date)" | tee -a analysis_log.txt
    
    if [ $PENDENTES -eq 0 ]; then
        echo "✅ Todos os leads foram processados!" | tee -a analysis_log.txt
        break
    fi
    
    # Executar análise de um lote
    venv/bin/python3 analyze_all_leads.py 2>&1 | tee -a analysis_log.txt
    
    # Pequena pausa entre lotes
    sleep 2
done

echo "🏁 Análise completa finalizada - $(date)" | tee -a analysis_log.txt
