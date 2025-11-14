#!/bin/bash

# Monitor ETL OpenAI Paralelo - Visual Atualizado a Cada 30 Segundos
# Sem necessidade de senha sudo

DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="geniai_analytics"
DB_USER="johan_geniai"
DB_PASS="vlVMVM6UNz2yYSBlzodPjQvZh"
TENANT_ID=1

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Função para desenhar barra de progresso
draw_progress_bar() {
    local percentage=$1
    local width=50
    local filled=$((percentage * width / 100))
    local empty=$((width - filled))

    echo -n "["
    for ((i=0; i<filled; i++)); do echo -n "█"; done
    for ((i=0; i<empty; i++)); do echo -n "░"; done
    echo -n "] ${percentage}%"
}

# Loop de monitoramento
while true; do
    clear

    echo -e "${BOLD}${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                  📊 MONITOR ETL OPENAI - PROCESSAMENTO PARALELO                ║"
    echo "║                    Atualizado: $(date '+%Y-%m-%d %H:%M:%S')                    ║"
    echo "╚════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # ==================== STATUS DO PROCESSO ====================
    echo -e "${BOLD}${YELLOW}┌─ 🔄 STATUS DO PROCESSO ETL${NC}"
    echo -e "${YELLOW}│${NC}"

    if ps aux | grep -E "python.*ETLPipeline" | grep -v grep > /dev/null; then
        PID=$(ps aux | grep -E "python.*ETLPipeline" | grep -v grep | awk '{print $2}' | head -1)
        ELAPSED=$(ps -p $PID -o etime= 2>/dev/null | xargs)
        CPU=$(ps -p $PID -o %cpu= 2>/dev/null | xargs)
        MEM=$(ps -p $PID -o %mem= 2>/dev/null | xargs)

        echo -e "${YELLOW}│${NC}  Status: ${GREEN}✅ RODANDO${NC}"
        echo -e "${YELLOW}│${NC}  PID: ${CYAN}$PID${NC}"
        echo -e "${YELLOW}│${NC}  Tempo decorrido: ${CYAN}$ELAPSED${NC}"
        echo -e "${YELLOW}│${NC}  CPU: ${CYAN}${CPU}%${NC}  |  Memória: ${CYAN}${MEM}%${NC}"
    else
        echo -e "${YELLOW}│${NC}  Status: ${RED}❌ NÃO ESTÁ RODANDO${NC}"
    fi
    echo -e "${YELLOW}└${NC}"
    echo ""

    # ==================== PROGRESSO DA ANÁLISE ====================
    echo -e "${BOLD}${MAGENTA}┌─ 📈 PROGRESSO DA ANÁLISE OPENAI${NC}"
    echo -e "${MAGENTA}│${NC}"

    STATS=$(PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -F' ' -c "
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE analise_ia <> '' AND analise_ia IS NOT NULL) as analisadas,
            COUNT(*) FILTER (WHERE analise_ia = '' OR analise_ia IS NULL) as pendentes,
            ROUND(COUNT(*) FILTER (WHERE analise_ia <> '' AND analise_ia IS NOT NULL)::numeric / COUNT(*) * 100, 1) as percentual
        FROM conversations_analytics
        WHERE tenant_id = $TENANT_ID;
    " 2>/dev/null)

    if [ ! -z "$STATS" ]; then
        TOTAL=$(echo $STATS | awk '{print $1}')
        ANALISADAS=$(echo $STATS | awk '{print $2}')
        PENDENTES=$(echo $STATS | awk '{print $3}')
        PERCENTUAL=$(echo $STATS | awk '{print $4}' | sed 's/\..*//')

        echo -e "${MAGENTA}│${NC}  Total de conversas: ${BOLD}$TOTAL${NC}"
        echo -e "${MAGENTA}│${NC}  ${GREEN}✓${NC} Analisadas: ${GREEN}$ANALISADAS${NC}"
        echo -e "${MAGENTA}│${NC}  ${YELLOW}⏳${NC} Pendentes: ${YELLOW}$PENDENTES${NC}"
        echo -e "${MAGENTA}│${NC}"
        echo -e "${MAGENTA}│${NC}  $(draw_progress_bar $PERCENTUAL)"

        # Estimar tempo restante
        if ps aux | grep -E "python.*ETLPipeline" | grep -v grep > /dev/null; then
            ELAPSED_SECONDS=$(ps -p $PID -o etimes= 2>/dev/null | xargs)
            if [ ! -z "$ELAPSED_SECONDS" ] && [ "$ELAPSED_SECONDS" -gt 0 ] && [ "$ANALISADAS" -gt 0 ]; then
                RATE=$(echo "scale=2; $ANALISADAS / $ELAPSED_SECONDS * 60" | bc)
                if [ ! -z "$RATE" ] && [ $(echo "$RATE > 0" | bc) -eq 1 ]; then
                    ETA_MIN=$(echo "scale=0; $PENDENTES / ($ANALISADAS / $ELAPSED_SECONDS) / 60" | bc)
                    echo -e "${MAGENTA}│${NC}  Taxa: ${CYAN}${RATE} conv/min${NC}  |  ETA: ${CYAN}~${ETA_MIN} minutos${NC}"
                fi
            fi
        fi
    fi
    echo -e "${MAGENTA}└${NC}"
    echo ""

    # ==================== ESTATÍSTICAS DE LEADS ====================
    echo -e "${BOLD}${BLUE}┌─ 🎯 ESTATÍSTICAS DE LEADS${NC}"
    echo -e "${BLUE}│${NC}"

    LEAD_STATS=$(PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -F' ' -c "
        SELECT
            COUNT(*) FILTER (WHERE is_lead = true) as leads,
            COUNT(*) FILTER (WHERE visit_scheduled = true) as visitas,
            COUNT(*) FILTER (WHERE probabilidade_conversao >= 4) as alta_prob,
            COUNT(*) FILTER (WHERE LENGTH(nome_mapeado_bot) > 0) as com_nome,
            COUNT(*) as total_analisadas
        FROM conversations_analytics
        WHERE tenant_id = $TENANT_ID AND analise_ia <> '' AND analise_ia IS NOT NULL;
    " 2>/dev/null)

    if [ ! -z "$LEAD_STATS" ]; then
        LEADS=$(echo $LEAD_STATS | awk '{print $1}')
        VISITAS=$(echo $LEAD_STATS | awk '{print $2}')
        ALTA_PROB=$(echo $LEAD_STATS | awk '{print $3}')
        COM_NOME=$(echo $LEAD_STATS | awk '{print $4}')
        TOTAL_ANALISADAS=$(echo $LEAD_STATS | awk '{print $5}')

        if [ "$TOTAL_ANALISADAS" -gt 0 ]; then
            TAXA_LEADS=$(echo "scale=1; $LEADS * 100 / $TOTAL_ANALISADAS" | bc)
            echo -e "${BLUE}│${NC}  🎯 Leads detectados: ${GREEN}${LEADS}${NC} (${TAXA_LEADS}%)"
        else
            echo -e "${BLUE}│${NC}  🎯 Leads detectados: ${GREEN}${LEADS}${NC}"
        fi

        echo -e "${BLUE}│${NC}  📅 Visitas agendadas: ${CYAN}${VISITAS}${NC}"
        echo -e "${BLUE}│${NC}  ⭐ Alta probabilidade (4-5): ${YELLOW}${ALTA_PROB}${NC}"
        echo -e "${BLUE}│${NC}  👤 Com nome mapeado: ${MAGENTA}${COM_NOME}${NC}"
    fi
    echo -e "${BLUE}└${NC}"
    echo ""

    # ==================== PROCESSAMENTO PARALELO ====================
    echo -e "${BOLD}${GREEN}┌─ ⚡ PROCESSAMENTO PARALELO (5 WORKERS)${NC}"
    echo -e "${GREEN}│${NC}"

    if [ -f /tmp/openai_parallel.log ]; then
        # Pegar última linha de progresso
        LAST_PROGRESS=$(grep "⏳" /tmp/openai_parallel.log | tail -1)
        if [ ! -z "$LAST_PROGRESS" ]; then
            CHUNK_PROGRESS=$(echo $LAST_PROGRESS | grep -oP '\d+/\d+' | head -1)
            CHUNK_PERCENT=$(echo $LAST_PROGRESS | grep -oP '\d+\.\d+%' | head -1)
            CHUNK_RATE=$(echo $LAST_PROGRESS | grep -oP '\d+\.\d+ conv/s' | head -1)
            CHUNK_ETA=$(echo $LAST_PROGRESS | grep -oP '\d+\.\d+ min' | head -1)

            echo -e "${GREEN}│${NC}  Chunk atual: ${CYAN}${CHUNK_PROGRESS}${NC} (${CHUNK_PERCENT})"
            echo -e "${GREEN}│${NC}  Taxa paralela: ${CYAN}${CHUNK_RATE}${NC}"
            echo -e "${GREEN}│${NC}  ETA chunk: ${CYAN}${CHUNK_ETA}${NC}"
        else
            echo -e "${GREEN}│${NC}  ${YELLOW}Aguardando progresso...${NC}"
        fi

        # Mostrar últimas 3 requisições HTTP bem-sucedidas
        echo -e "${GREEN}│${NC}"
        echo -e "${GREEN}│${NC}  Últimas requisições OpenAI:"
        grep "HTTP/1.1 200 OK" /tmp/openai_parallel.log | tail -3 | while read line; do
            TIMESTAMP=$(echo $line | awk '{print $1, $2}' | cut -d',' -f1)
            echo -e "${GREEN}│${NC}    ${GREEN}✓${NC} $TIMESTAMP"
        done
    fi
    echo -e "${GREEN}└${NC}"
    echo ""

    # ==================== CUSTOS OPENAI (ESTIMATIVA) ====================
    echo -e "${BOLD}${YELLOW}┌─ 💰 CUSTOS OPENAI (Estimativa)${NC}"
    echo -e "${YELLOW}│${NC}"

    if [ ! -z "$ANALISADAS" ] && [ "$ANALISADAS" -gt 0 ]; then
        # Estimativa: ~2000 tokens por conversa, R$0.000004/token para gpt-4o-mini
        TOKENS_EST=$((ANALISADAS * 2000))
        COST_EST=$(echo "scale=4; $TOKENS_EST * 0.000004" | bc)

        echo -e "${YELLOW}│${NC}  Conversas analisadas: ${CYAN}${ANALISADAS}${NC}"
        echo -e "${YELLOW}│${NC}  Tokens estimados: ${CYAN}~${TOKENS_EST}${NC}"
        echo -e "${YELLOW}│${NC}  Custo estimado: ${GREEN}R\$ ${COST_EST}${NC}"
    else
        echo -e "${YELLOW}│${NC}  ${YELLOW}Aguardando análises...${NC}"
    fi
    echo -e "${YELLOW}└${NC}"
    echo ""

    # ==================== FOOTER ====================
    echo -e "${CYAN}──────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}Atualizando a cada 30 segundos... Pressione Ctrl+C para sair${NC}"
    echo -e "${CYAN}Log completo: /tmp/openai_parallel.log${NC}"

    sleep 30
done