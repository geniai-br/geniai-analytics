# ETL Pipeline V3 - Documentação Completa

## 📋 Visão Geral

O **ETL Pipeline V3** é um sistema de extração, transformação e carga **incremental** que sincroniza dados do Chatwoot (banco remoto) para o banco local PostgreSQL.

### ✨ Características Principais

- ✅ **Extração Incremental** - Busca apenas dados novos/atualizados
- ✅ **UPSERT Inteligente** - INSERT para novos, UPDATE para existentes
- ✅ **Watermark Automático** - Controle de ponto de sincronização
- ✅ **Auditoria Completa** - Tabela `etl_control` rastreia todas execuções
- ✅ **Logging Estruturado** - Logs em arquivo com rotação
- ✅ **Agendamento** - Suporte nativo para systemd timer
- ✅ **Resiliência** - Tratamento de erros e retry automático

---

## 🏗️ Arquitetura

```
┌────────────────────┐
│ BANCO REMOTO       │
│ (Chatwoot/Render)  │
│ vw_conversations_  │
│  analytics_final   │
└─────────┬──────────┘
          │ EXTRACT (incremental)
          │ WHERE updated_at > watermark
          ▼
┌────────────────────┐
│  ETL PIPELINE V3   │
│  ┌──────────────┐  │
│  │ Extractor    │  │ - Conexão com banco remoto
│  └──────┬───────┘  │ - Query incremental
│         ▼          │
│  ┌──────────────┐  │
│  │ Transformer  │  │ - Limpeza de dados
│  └──────┬───────┘  │ - Tratamento de NaT/NaN
│         ▼          │
│  ┌──────────────┐  │
│  │ Loader       │  │ - UPSERT (INSERT ou UPDATE)
│  └──────┬───────┘  │ - Controle de duplicatas
│         ▼          │
│  ┌──────────────┐  │
│  │ Watermark    │  │ - Atualiza ponto de controle
│  │ Manager      │  │ - Registra em etl_control
│  └──────────────┘  │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ BANCO LOCAL        │
│ (PostgreSQL)       │
│ conversas_         │
│  analytics         │
└────────────────────┘
```

---

## 📁 Estrutura de Arquivos

```
src/features/
├── etl_pipeline_v3.py          # Pipeline principal (entry point)
├── etl/
│   ├── __init__.py
│   ├── extractor.py            # Extração incremental do remoto
│   ├── transformer.py          # Transformação e limpeza
│   ├── loader.py               # UPSERT no banco local
│   ├── watermark_manager.py   # Gerenciamento de watermark
│   └── logger.py               # Sistema de logs

sql/local_schema/
└── 02_create_etl_control.sql   # Tabela de controle

systemd/
├── allpfit-etl.service         # Definição do serviço
└── allpfit-etl.timer           # Timer (executa às 3h)

scripts/
├── setup_systemd.sh            # Instala e ativa timer
├── run_etl_manual.sh           # Executa ETL manualmente
└── check_etl_health.sh         # Verifica saúde do ETL

logs/etl/
├── etl_YYYYMMDD.log            # Logs diários
└── etl_latest.log              # Último log (symlink)
```

---

## 🚀 Uso

### 1. Execução Manual

```bash
# Modo incremental (padrão)
bash scripts/run_etl_manual.sh

# OU diretamente:
source venv/bin/activate
python3 src/features/etl_pipeline_v3.py --triggered-by manual
```

### 2. Carga Completa (Force Full Load)

```bash
# Ignora watermark e carrega tudo
python3 src/features/etl_pipeline_v3.py --triggered-by manual --full
```

### 3. Agendamento Automático (systemd timer)

```bash
# Instalar e ativar (apenas primeira vez)
sudo bash scripts/setup_systemd.sh

# Verificar status
systemctl status allpfit-etl.timer

# Ver próximas execuções
systemctl list-timers allpfit-etl.timer

# Executar manualmente via systemd
sudo systemctl start allpfit-etl.service

# Ver logs
journalctl -u allpfit-etl.service -f
```

### 4. Monitoramento

```bash
# Health check completo
bash scripts/check_etl_health.sh

# Ver estatísticas no banco
psql -U isaac -d allpfit -c "SELECT * FROM vw_etl_stats LIMIT 10;"

# Ver último watermark
psql -U isaac -d allpfit -c "SELECT get_last_successful_watermark();"
```

---

## 📊 Tabela de Controle: `etl_control`

Rastreia **todas** as execuções do ETL (sucesso ou falha).

### Campos Principais

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `execution_id` | UUID | ID único da execução |
| `started_at` | TIMESTAMP | Quando começou |
| `completed_at` | TIMESTAMP | Quando terminou |
| `status` | VARCHAR | `running`, `success`, `failed` |
| `watermark_start` | TIMESTAMP | Início da janela incremental |
| `watermark_end` | TIMESTAMP | Fim da janela (último updated_at) |
| `rows_extracted` | INTEGER | Linhas extraídas do remoto |
| `rows_inserted` | INTEGER | Novas conversas inseridas |
| `rows_updated` | INTEGER | Conversas atualizadas |
| `rows_unchanged` | INTEGER | Conversas sem mudança |
| `duration_seconds` | NUMERIC | Tempo total |
| `load_type` | VARCHAR | `incremental` ou `full` |
| `triggered_by` | VARCHAR | `manual`, `scheduler`, `api` |

### Exemplos de Consultas

```sql
-- Últimas 5 execuções
SELECT * FROM vw_etl_stats LIMIT 5;

-- Execuções com erro
SELECT * FROM etl_control
WHERE status = 'failed'
ORDER BY started_at DESC;

-- Performance média (últimas 10 execuções)
SELECT
    AVG(duration_seconds) as avg_duration,
    AVG(rows_inserted + rows_updated) as avg_rows_processed
FROM etl_control
WHERE status = 'success'
  AND started_at > NOW() - INTERVAL '10 days';
```

---

## 🔄 Como Funciona o Modo Incremental

### 1. Primeira Execução (Full Load)

```
watermark_start = NULL
↓
Busca TODOS os registros da view remota
↓
Insere tudo no banco local
↓
watermark_end = MAX(conversation_updated_at) = "2025-10-21 19:38:37"
```

### 2. Segunda Execução (Incremental)

```
watermark_start = "2025-10-21 19:38:37" (último watermark_end)
↓
SELECT * FROM vw_conversations_analytics_final
WHERE conversation_updated_at > '2025-10-21 19:38:37'
↓
Retorna apenas conversas novas/atualizadas
↓
Para cada conversa:
  - Se conversation_id existe → UPDATE (se updated_at remoto > local)
  - Se conversation_id não existe → INSERT
↓
watermark_end = MAX(conversation_updated_at)
```

### 3. Sem Dados Novos

```
Extração retorna 0 linhas
↓
ETL completa sem processar nada
↓
watermark permanece o mesmo
```

---

## ⚙️ Configurações

### Variáveis de Ambiente (.env)

```env
# Banco REMOTO (Chatwoot - source)
SOURCE_DB_HOST=178.156.206.184
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=chatwoot
SOURCE_DB_USER=hetzner_dev_isaac_read
SOURCE_DB_PASSWORD=***

# Banco LOCAL (Analytics - destino)
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=allpfit
LOCAL_DB_USER=isaac
LOCAL_DB_PASSWORD=***
```

### Agendamento (systemd timer)

Arquivo: `systemd/allpfit-etl.timer`

```ini
[Timer]
# Executar diariamente às 3:00 AM
OnCalendar=*-*-* 03:00:00

# Se sistema estava desligado, executar ao ligar
Persistent=true
```

Para alterar o horário:
```bash
# Editar arquivo
nano systemd/allpfit-etl.timer

# Recarregar systemd
sudo systemctl daemon-reload
sudo systemctl restart allpfit-etl.timer
```

---

## 🐛 Troubleshooting

### ETL Falhou - Como Diagnosticar?

1. **Ver logs do sistema:**
```bash
journalctl -u allpfit-etl.service -n 50
```

2. **Ver logs do ETL:**
```bash
cat logs/etl/etl_latest.log
```

3. **Ver erro no banco:**
```sql
SELECT error_message, error_traceback
FROM etl_control
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 1;
```

### Problemas Comuns

#### 1. Erro de conexão com banco remoto

```
❌ Erro: could not connect to server
```

**Solução:**
- Verificar credenciais no `.env`
- Testar conexão: `python3 -c "from src.features.etl.extractor import test_connection; test_connection()"`

#### 2. Dados duplicados

```
❌ duplicate key value violates unique constraint
```

**Solução:**
- Executar carga FULL (sobrescreve tudo):
```bash
python3 src/features/etl_pipeline_v3.py --full
```

#### 3. Timer não está executando

```bash
# Verificar status
systemctl status allpfit-etl.timer

# Se inativo:
sudo systemctl start allpfit-etl.timer
sudo systemctl enable allpfit-etl.timer
```

---

## 📈 Performance

### Benchmarks (482 conversas)

| Fase | Tempo | Taxa |
|------|-------|------|
| **Extração** | 0.34s | - |
| **Transformação** | 0.02s | - |
| **Carga (UPSERT)** | 0.43s | 1.117 registros/s |
| **TOTAL** | 0.86s | 560 registros/s |

### Escalabilidade

- ✅ **< 1.000 conversas:** Modo UPSERT linha a linha (atual)
- ⚠️ **> 10.000 conversas:** Considerar batch UPSERT com PostgreSQL `ON CONFLICT`
- ⚠️ **> 100.000 conversas:** Considerar particionamento da tabela

---

## 🔒 Segurança

1. ✅ **Usuário read-only** no banco remoto
2. ✅ **Credenciais em `.env`** (não versionado)
3. ✅ **Logs não contêm dados sensíveis**
4. ✅ **Banco local isolado**

---

## 🚧 Próximas Melhorias

### Fase 2 (Futuro)

- [ ] Alertas automáticos (Slack/Email) em caso de falha
- [ ] Dashboard web de monitoramento do ETL
- [ ] API REST para disparar ETL manualmente
- [ ] Detecção e marcação de conversas deletadas
- [ ] Batch UPSERT para melhor performance

### Fase 3 (Avançado)

- [ ] Particionamento da tabela por data
- [ ] Compressão de dados antigos
- [ ] Replicação para data warehouse
- [ ] ML para detecção de anomalias nos dados

---

## 📝 Changelog

### v3.0.0 (2025-10-21)

- ✨ **NOVO:** Extração incremental com watermark
- ✨ **NOVO:** UPSERT inteligente (INSERT ou UPDATE)
- ✨ **NOVO:** Tabela de controle `etl_control`
- ✨ **NOVO:** Logging estruturado em arquivos
- ✨ **NOVO:** Suporte para systemd timer
- ✨ **NOVO:** Scripts de gerenciamento
- 🐛 **FIX:** Tratamento correto de valores NaT/NaN
- 🐛 **FIX:** Tratamento de tipos datetime

### v2.0.0 (anterior)

- Carga completa (TRUNCATE + INSERT)
- Sem controle de execuções
- Sem logs estruturados

---

## 📞 Suporte

**Problemas ou dúvidas?**

1. Verificar logs: `bash scripts/check_etl_health.sh`
2. Consultar esta documentação
3. Verificar issues no repositório

---

**Desenvolvido por:** GenIAI
**Projeto:** AllpFit Analytics
**Versão:** 3.0.0
**Data:** 2025-10-21
