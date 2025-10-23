# 📅 Histórico de Sessões - AllpFit Analytics

## Sessão Atual: 23/10/2025

### 🎯 Objetivos da Sessão
Continuação do desenvolvimento anterior. Implementar rastreamento de conversões CRM e melhorias no dashboard.

---

## 📋 Cronologia Detalhada

### **1. Integração CRM - Identificação de Conversões**

#### Contexto Inicial:
- Dashboard funcionando com métricas básicas
- 482 conversas analisadas pela IA
- Sem rastreamento de conversões (vendas)

#### Problema a Resolver:
> "Quantos leads do bot realmente viraram clientes na academia?"

#### Tentativa 1: API EVO CRM
- **Ação:** Conectar com API EVO para buscar membros
- **Credenciais fornecidas:**
  - DNS: allpfit
  - Token: AF61C223-2C8D-4619-94E3-0A5A37D1CD8D
- **Resultado:** 2685 membros ativos encontrados
- **Match inicial:** 2 conversões (ambas falsas - já eram membros antes do bot)
- **Problema:** Telefones em formatos diferentes, causando poucos matches

#### Tentativa 2 (ABANDONADA): Google Calendar
- **Objetivo:** Buscar visitas agendadas no Google Calendar
- **Problema:** OAuth2 complexo em ambiente servidor
- **Decisão:** Usuário pediu para esquecer ("esqueca isso")

#### Solução Final: Excel + Normalização Inteligente
- **Arquivo recebido:** `base_evo.xlsx` (198 clientes do CRM)
- **Desafio:** Telefones com formatos variados
  - Excel: "55 83988439500" ou "55 (83) 99886-9874"
  - Bot: "+558388439500" ou "+558393255303"

**Normalização Implementada:**
1. Remove tudo que não é dígito
2. Remove DDI (55) e DDD (83)
3. **Gera 2 versões:** com 9 e sem 9
   - Com 9: 988439500
   - Sem 9: 88439500
4. Tenta match com ambas as versões
5. Evita duplicatas usando `set()`

**Resultado:** ✅ **7 conversões identificadas (3.5% taxa)**

---

### **2. Correção do ETL (Parou no Dia 21)**

#### Problema Identificado:
```
Última atualização: 21/10/2025
Total conversas: 482 (desatualizado)
```

#### Diagnóstico:
- ETL v3 funciona perfeitamente
- **Cron NÃO estava configurado** ❌

#### Solução:
```bash
# Cron configurado:
0 * * * * cd /home/isaac/projects/allpfit-analytics && python3 src/features/etl_pipeline_v3.py --triggered-by scheduler

# Erro no primeiro teste: faltava cd no diretório
# Corrigido adicionando cd antes do python
```

#### Resultado:
- ✅ ETL rodando automaticamente a cada hora
- ✅ Dados atualizados (495 conversas)
- ✅ +13 novas conversas sincronizadas

---

### **3. Scripts de Monitoramento**

#### Criados:
1. **monitor_etl.sh** - Monitor completo
   - Agendamento (cron)
   - Próxima execução
   - Últimas 5 execuções
   - Status dos dados
   - Log recente
   - Erros nas últimas 24h

2. **etl_status.sh** - Status rápido
   - Última execução
   - Total conversas

3. **MONITORAMENTO_ETL.md** - Documentação

#### Ajustes de Timezone:
- **Problema:** Horários mostravam UTC (servidor)
- **Solução:** Converter para SP (-3h)
- **Implementação:** `started_at - INTERVAL '3 hours'`

---

### **4. Dashboard - Melhorias e Correções**

#### A) Adicionados Tooltips Explicativos
Todos os KPIs e gráficos agora têm explicações no ícone "?":

**KPIs Principais:**
- Total Contatos: 📊 "Número de leads únicos..."
- Agente AI: 🤖 "Conversas 100% bot..."
- Humano: 👤 "Conversas com intervenção..."
- Visitas: 📅 "Leads que agendaram..."
- Vendas/Tráfego: 🎯 "Leads que conversaram antes..."
- Vendas/Geral: 💼 "Total de clientes no CRM..."

**Métricas Diárias:**
- Novos Leads: 📈 "Primeiro contato HOJE"
- Visitas Dia: 🏋️ "Agendadas para HOJE"
- Vendas Dia: 💰 "Conversões HOJE"
- Total Conversas: 💬 "Novas + reabertas"
- Novas: 🆕 "Iniciadas HOJE"
- Reabertas: 🔄 "Voltaram a conversar"

**Gráficos:**
- Média Leads: "Últimos 30 dias com linha de média"
- Distribuição: "Por período do dia (Manhã/Tarde/Noite)"

#### B) Correção de Taxa de Conversão
**Erro identificado:** Taxa calculada sobre total_contatos

**Antes:**
```python
perc_trafego = vendas_trafego / total_contatos  # 7/495 = 1.4% ❌
```

**Depois:**
```python
perc_trafego = vendas_trafego / vendas_geral  # 7/198 = 3.5% ✅
```

**Locais corrigidos:**
1. KPI "Vendas/Tráfego" (card superior)
2. Seção "Conversões Reais" (taxa de conversão)

#### C) Seção de Conversões Adicionada
Nova seção no dashboard mostrando:
- 7 conversões identificadas
- Taxa: 3.5%
- Tabela com: Nome (Bot), Nome (CRM), Telefone, Origem, Datas, Dias, Msgs
- Coluna **Origem** preparada para futuro (Remarketing, Disparos, etc)

#### D) Contador "Bot rodando há X dias"
- Adicionado no header do dashboard
- Calculado desde primeira conversa (25/09/2025)
- Mostra: "Bot rodando há 28 dias"

---

### **5. Tabela conversas_crm_match_real**

#### Schema Criado:
```sql
CREATE TABLE conversas_crm_match_real (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER,
    nome_bot VARCHAR(255),
    nome_crm VARCHAR(255),
    telefone VARCHAR(50),          -- Telefone completo: +558393255303
    telefone_8dig VARCHAR(20),      -- Normalizado para match
    origem VARCHAR(50) DEFAULT 'Agente IA',  -- Preparado para futuro
    conversa_criada_em TIMESTAMP,
    cadastro_crm_em DATE,
    dias_para_conversao INTEGER,
    total_mensagens INTEGER,
    conversou_antes_crm BOOLEAN,
    id_cliente_crm INTEGER,
    email_crm VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Dados Inseridos:
1. Vih (JOSÉ VINICIUS) - 6 dias - 23 msgs
2. RossanaMedeiros - 18 dias - 11 msgs
3. Moroni Diniz - 9 dias - 14 msgs
4. Jennifer Barbosa - 2 dias - 32 msgs 🌟
5. ✨✨😊 (TATIANE) - 8 dias - 6 msgs
6. Hadassa - 0 dias (mesmo dia) - 1 msg
7. Junior Fernandes 🥋 - 4 dias - 13 msgs

**Tempo médio conversão:** 6.7 dias

---

### **6. Script crossmatch_excel_crm.py**

#### Funcionalidades:
1. Carrega Excel do CRM
2. Normaliza telefones (remove DDI/DDD, gera versões)
3. Busca conversas do bot
4. Normaliza telefones do bot (mesma lógica)
5. Cruza por telefone
6. Valida se conversou ANTES do CRM
7. Salva em `conversas_crm_match_real`
8. Gera relatório em TXT

#### Execução:
```bash
python3 crossmatch_excel_crm.py
```

#### Output:
```
Total clientes Excel: 198
Total conversas bot: 480
Conversões encontradas: 7
Taxa: 3.5%
```

---

## 🗂️ Arquivos Criados/Modificados

### ✅ Criados:
- `crossmatch_excel_crm.py` - Script de crossmatch
- `monitor_etl.sh` - Monitor completo
- `etl_status.sh` - Status rápido
- `MONITORAMENTO_ETL.md` - Documentação
- `docs/project_memory_claude/` - Esta pasta

### ✏️ Modificados:
- `src/app/dashboard.py` - Conversões + tooltips + contador
- `src/app/utils/metrics.py` - 3 novas funções
- `CONTEXTO_PROJETO.md` - Atualizado
- `.gitignore` - Excel e relatórios
- `crontab` - ETL agendado

### ❌ Removidos:
- `match_leads_crm.py` - Substituído por crossmatch
- `src/features/etl_pipeline_v2.py` - Obsoleto
- `src/features/ai_analyzer.py` - Não usado
- `src/features/ai_initial_load.py` - Não usado
- `relatorio_conversoes_excel_*.txt` - Temporários

---

## 🎯 Problemas Resolvidos

1. ✅ ETL parado (cron não configurado)
2. ✅ Conversões não rastreadas (implementado crossmatch)
3. ✅ Taxa de conversão errada (corrigida base de cálculo)
4. ✅ Falta de explicações (tooltips adicionados)
5. ✅ Horários confusos (convertido para SP)
6. ✅ Normalização de telefone (com/sem 9)

---

## 📊 Estado Final

- **Dashboard:** ✅ Rodando com conversões
- **ETL:** ✅ Automático (a cada hora)
- **Conversões:** ✅ 7 rastreadas (3.5%)
- **Monitoramento:** ✅ Scripts criados
- **Documentação:** ✅ Completa

**URL Produção:** https://analytcs.geniai.online

---

**Última atualização:** 23/10/2025 11:30
