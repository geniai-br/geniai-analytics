# 📊 Monitoramento do ETL - AllpFit Analytics

## 🚀 Como Monitorar o ETL

### ⚡ Opção 1: Monitor Completo (RECOMENDADO)

```bash
cd /home/isaac/projects/allpfit-analytics
./monitor_etl.sh
```

**O que mostra:**
- ✅ Agendamento do cron
- ⏰ Próxima execução
- 📋 Últimas 5 execuções
- 📊 Status dos dados
- 📝 Log recente
- ❌ Erros nas últimas 24h

---

### ⚡ Opção 2: Status Rápido

```bash
cd /home/isaac/projects/allpfit-analytics
./etl_status.sh
```

Mostra apenas o essencial: última execução e total de conversas.

---

### ⚡ Opção 3: Via Banco de Dados

```bash
PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -c "
SELECT
    id,
    TO_CHAR(started_at, 'DD/MM HH24:MI') as quando,
    triggered_by as por,
    status,
    rows_extracted as novos,
    rows_inserted + rows_updated as processados
FROM etl_control
ORDER BY id DESC
LIMIT 5;
"
```

---

### ⚡ Opção 4: Logs em Tempo Real

```bash
# Log de hoje
tail -f /home/isaac/projects/allpfit-analytics/logs/etl/etl_$(date +%Y%m%d).log

# Log do cron (execuções automáticas)
tail -f /home/isaac/projects/allpfit-analytics/logs/etl_cron.log
```

---

## 🔍 Verificações Importantes

### ✅ ETL está rodando?

Execute o monitor e veja se:
1. **Última execução** foi há menos de 2 horas
2. **Próxima execução** está agendada
3. **Status** mostra ✅ (success)

### ❌ ETL parou?

Se a última execução foi há mais de 2 horas:

```bash
# 1. Verificar se o cron está configurado
crontab -l

# 2. Rodar manualmente para testar
cd /home/isaac/projects/allpfit-analytics
source venv/bin/activate
python3 src/features/etl_pipeline_v3.py --triggered-by manual

# 3. Ver se há erros
./monitor_etl.sh
```

---

## 🔧 Configuração Atual

### Agendamento
```
0 * * * * # Roda a cada hora (9:00, 10:00, 11:00...)
```

### Logs
- **Log do ETL:** `/home/isaac/projects/allpfit-analytics/logs/etl/etl_YYYYMMDD.log`
- **Log do Cron:** `/home/isaac/projects/allpfit-analytics/logs/etl_cron.log`
- **Banco:** Tabela `etl_control` (histórico completo)

---

## 📊 Dashboard

Para ver os dados atualizados no dashboard:
- **URL:** https://analytcs.geniai.online
- **Porta local:** http://localhost:8501

O dashboard lê diretamente da tabela `conversas_analytics`, que é atualizada pelo ETL.

---

## 🚨 Alertas

### Como saber se algo deu errado?

1. **Via Monitor:**
```bash
./monitor_etl.sh
# Veja a seção "6️⃣ ERROS RECENTES"
```

2. **Via Banco:**
```bash
PGPASSWORD='AllpFit2024@Analytics' psql -h localhost -p 5432 -U isaac -d allpfit -c "
SELECT
    TO_CHAR(started_at, 'DD/MM HH24:MI') as quando,
    error_message
FROM etl_control
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 5;
"
```

---

## 🛠️ Comandos Úteis

### Forçar execução manual
```bash
cd /home/isaac/projects/allpfit-analytics
source venv/bin/activate
python3 src/features/etl_pipeline_v3.py --triggered-by manual
```

### Carga completa (todos os dados)
```bash
python3 src/features/etl_pipeline_v3.py --full --triggered-by manual
```

### Ver cron configurado
```bash
crontab -l
```

### Editar cron
```bash
crontab -e
```

---

## 📈 Métricas de Saúde

**ETL está saudável quando:**
- ✅ Última execução < 2 horas atrás
- ✅ Status = success
- ✅ 0 erros nas últimas 24h
- ✅ Dados atualizados no dashboard
- ✅ Log do cron sem erros

**ETL precisa atenção quando:**
- ⚠️ Última execução > 2 horas atrás
- ❌ Status = failed
- ❌ Erros recorrentes no log
- ❌ Dashboard com dados desatualizados

---

## 🆘 Suporte

Se algo não estiver funcionando:

1. Execute `./monitor_etl.sh`
2. Veja a seção de erros
3. Tente rodar manualmente
4. Verifique os logs

**Contato Técnico:** Claude Code (este documento foi gerado automaticamente)
