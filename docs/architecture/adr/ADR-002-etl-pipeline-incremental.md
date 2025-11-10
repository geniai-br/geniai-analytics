# ADR-002: Pipeline ETL V3 Incremental com Watermark

**Status:** Aceito
**Data:** 2025-11-04
**Decisores:** Equipe GenIAI
**Contexto Técnico:** Python 3.11, PostgreSQL 15, Pandas 2.0, psycopg2

---

## Contexto e Problema

O sistema precisa sincronizar dados do Chatwoot (banco remoto) para o banco local de analytics:

### Requisitos
1. **Volume:** ~300.000+ conversas, crescendo ~2.000/dia
2. **Frequência:** Atualização a cada hora (24x/dia)
3. **Performance:** Execução em < 10 segundos (não bloquear dashboards)
4. **Confiabilidade:** Retry automático, auditoria de execuções
5. **Dados Mutáveis:** Conversas podem ser atualizadas (status, CSAT, resolução)
6. **Economia:** Minimizar carga no banco remoto (read-only user)

### Problema
Como sincronizar eficientemente dados mutáveis de um banco remoto sem:
- Refazer carga completa (300k rows = 2-3 minutos)
- Perder atualizações de conversas antigas
- Criar duplicatas
- Sobrecarregar banco remoto

---

## Alternativas Consideradas

### Opção 1: Full Load (Carga Completa)
```python
df = pd.read_sql("SELECT * FROM vw_conversations_analytics_final", conn)
df.to_sql("conversations_analytics", conn, if_exists='replace')
```
- **Prós:** Simples, garante consistência total
- **Contras:**
  - 300k rows = 2-3 minutos
  - Sobrecarga no banco remoto
  - Downtime do dashboard
  - Ineficiente para 24 execuções/dia
- **Decisão:** ❌ Rejeitado - inviável para produção

### Opção 2: Incremental Simples (Apenas Novos)
```python
last_id = get_max_id()
df = pd.read_sql(f"SELECT * FROM ... WHERE id > {last_id}", conn)
```
- **Prós:** Rápido para novos registros
- **Contras:**
  - **Perde atualizações** de conversas antigas (status, CSAT)
  - Não detecta mudanças
- **Decisão:** ❌ Rejeitado - dados incompletos

### Opção 3: CDC (Change Data Capture) com Triggers
```sql
CREATE TRIGGER conversation_changes
AFTER UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION notify_change();
```
- **Prós:** Captura mudanças em real-time
- **Contras:**
  - Requer permissões de DBA no banco remoto
  - Usuário read-only não pode criar triggers
  - Complexidade operacional
- **Decisão:** ❌ Rejeitado - permissões insuficientes

### Opção 4: Incremental com Watermark (Timestamp-Based) ✅
```python
watermark = get_last_watermark()  # 2025-11-10 10:00:00
df = pd.read_sql(f"""
    SELECT * FROM vw_conversations_analytics_final
    WHERE updated_at > '{watermark}'
    ORDER BY updated_at ASC
""", conn)
# UPSERT: INSERT novos, UPDATE existentes
```
- **Prós:**
  - Captura novos E atualizações
  - Performance: apenas dados modificados
  - Não requer permissões especiais
  - Auditável (watermark tracking)
- **Contras:**
  - Requer campo `updated_at` na fonte
  - Lógica de UPSERT mais complexa
- **Decisão:** ✅ **ESCOLHIDO**

---

## Decisão

Implementar **ETL Pipeline V3 Incremental com Watermark Management:**

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  ETL Pipeline V3 - Modular                                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Watermark Manager  ←──────┐                             │
│     - get_last_watermark()     │  Auditoria                  │
│     - create_etl_execution()   │                             │
│     - update_etl_execution()   └──→  etl_control (tabela)   │
│                                                               │
│  2. Extractor                                                │
│     - test_connection()                                      │
│     - extract_incremental(watermark_start)                   │
│     - extract_full()                                         │
│                                                               │
│  3. Transformer                                              │
│     - transform_data(df)                                     │
│     - validate_data(df)                                      │
│     - clean_columns()                                        │
│                                                               │
│  4. Loader                                                   │
│     - load_upsert(df) ← INSERT + UPDATE                     │
│     - load_full(df)                                          │
│     - batch_processing(1000 rows)                            │
│                                                               │
│  5. Logger                                                   │
│     - setup_logger()                                         │
│     - log_execution_summary()                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Componentes-Chave

#### 1. Watermark Manager
```python
def get_last_watermark() -> Optional[datetime]:
    """Obtém timestamp da última execução bem-sucedida"""
    query = """
        SELECT watermark_end
        FROM etl_control
        WHERE status = 'success'
        ORDER BY execution_id DESC
        LIMIT 1
    """
    return result or None  # None = Full Load
```

#### 2. Extractor (Incremental)
```python
def extract_incremental(watermark_start: datetime) -> pd.DataFrame:
    """Extrai apenas dados novos/modificados"""
    query = f"""
        SELECT * FROM vw_conversations_analytics_final
        WHERE updated_at > '{watermark_start}'
        ORDER BY updated_at ASC
        LIMIT 10000  -- Safety limit
    """
    return pd.read_sql(query, source_conn)
```

#### 3. Loader (UPSERT)
```python
def load_upsert(df: pd.DataFrame) -> bool:
    """INSERT novos, UPDATE existentes"""
    query = """
        INSERT INTO conversations_analytics (
            conversation_id, tenant_id, status, ...
        ) VALUES %s
        ON CONFLICT (tenant_id, conversation_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = EXCLUDED.updated_at,
            etl_updated_at = NOW()
    """
    execute_batch(cursor, query, df.values, page_size=1000)
```

#### 4. Tabela de Auditoria
```sql
CREATE TABLE etl_control (
    execution_id SERIAL PRIMARY KEY,
    tenant_id INTEGER,
    load_type VARCHAR(50),  -- 'incremental' ou 'full'
    triggered_by VARCHAR(50),  -- 'manual', 'scheduler', 'api'
    status VARCHAR(50),  -- 'running', 'success', 'failed'
    rows_extracted INTEGER,
    rows_loaded INTEGER,
    watermark_start TIMESTAMP,
    watermark_end TIMESTAMP,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    error_message TEXT
);
```

---

## Fluxo de Execução

### 1. Modo Incremental (Padrão)
```
├─ START (disparado por cron)
├─ Obter watermark: 2025-11-10 10:00:00
├─ EXTRACT: SELECT WHERE updated_at > '10:00'
│  └─ Resultado: 1.542 rows (2-3 segundos)
├─ TRANSFORM: Validar + Limpar (1 segundo)
├─ LOAD: UPSERT em batches de 1000 (1-2 segundos)
├─ UPDATE watermark: 2025-11-10 11:00:00
└─ END (total: 4-6 segundos)
```

### 2. Modo Full Load (Primeira Vez / --full)
```
├─ START
├─ Watermark: None (full load)
├─ EXTRACT: SELECT * (sem filtro)
│  └─ Resultado: 300.000 rows (60-90 segundos)
├─ TRANSFORM: Validar + Limpar (15-20 segundos)
├─ LOAD: UPSERT em batches (30-40 segundos)
├─ SET watermark: 2025-11-10 11:00:00
└─ END (total: 2-3 minutos)
```

---

## Consequências

### Positivas ✅

1. **Performance:** 2-5 segundos (incremental) vs 2-3 minutos (full)
2. **Economia:** 99% menos dados transferidos do banco remoto
3. **Atualização:** Captura mudanças em conversas antigas (CSAT, status)
4. **Auditoria:** Histórico completo de execuções em `etl_control`
5. **Confiabilidade:** Retry automático, rollback em caso de erro
6. **Escalabilidade:** Performance constante independente do volume total
7. **Flexibilidade:** Suporta tanto incremental quanto full load

### Negativas ❌

1. **Complexidade:** Mais código que full load simples
2. **Dependência:** Requer campo `updated_at` confiável na fonte
3. **Testes:** Precisa testar cenários de atualização, não só inserção
4. **Monitoramento:** Requer alertas para falhas de watermark

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| updated_at não atualizado | Baixa | Alto | Validação na view remota |
| Watermark corrompido | Baixa | Médio | Backup em arquivo + tabela |
| Dados duplicados | Baixa | Médio | UNIQUE constraint (tenant_id, conversation_id) |
| Execução concorrente | Baixa | Alto | Lock na tabela etl_control |
| Batch muito grande | Média | Médio | LIMIT 10.000 no extractor |

---

## Métricas de Sucesso

### Performance
- ✅ Incremental: < 10 segundos (99% das execuções)
- ✅ Full load: < 5 minutos (primeira vez)
- ✅ Taxa de sucesso: > 99.5%

### Dados
- ✅ 0 duplicatas (validado por UNIQUE constraint)
- ✅ 0 dados perdidos (auditoria de contagem)
- ✅ Latência: < 1 hora (dados no dashboard)

### Operacional
- ✅ 24 execuções/dia (agendamento via cron)
- ✅ Logs estruturados em `logs/etl/`
- ✅ Alertas automáticos em caso de falha

---

## Implementação

### Fase 1: Modularização (Completo)
- ✅ `etl/extractor.py` (250 linhas)
- ✅ `etl/transformer.py` (180 linhas)
- ✅ `etl/loader.py` (220 linhas)
- ✅ `etl/watermark_manager.py` (150 linhas)
- ✅ `etl/logger.py` (100 linhas)

### Fase 2: Pipeline V3 (Completo)
- ✅ `etl_pipeline_v3.py` (orquestrador)
- ✅ Suporte a flags: `--full`, `--triggered-by`
- ✅ Auditoria em `etl_control`

### Fase 3: Agendamento (Completo)
- ✅ Cron job: a cada hora
- ✅ Systemd timer (alternativa)
- ✅ Scripts de monitoramento

### Fase 4: Multi-Tenant (Em Progresso)
- 🚧 ETL V4: suporte a múltiplos tenants
- 🚧 Watermark por tenant
- 🚧 Paralelização de execuções

---

## Monitoramento

### Queries de Monitoramento
```sql
-- Últimas 5 execuções
SELECT
    execution_id,
    load_type,
    status,
    rows_extracted,
    rows_loaded,
    EXTRACT(EPOCH FROM (ended_at - started_at)) as duration_seconds,
    started_at
FROM etl_control
ORDER BY execution_id DESC
LIMIT 5;

-- Taxa de sucesso (últimas 24h)
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'success') as success,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'success') / COUNT(), 2) as success_rate
FROM etl_control
WHERE started_at > NOW() - INTERVAL '24 hours';
```

### Alertas
```bash
# Script de alerta (scripts/etl/monitor.sh)
if [ $(psql -t -c "SELECT COUNT(*) FROM etl_control WHERE status='failed' AND started_at > NOW() - INTERVAL '1 hour'") -gt 0 ]; then
    echo "ALERTA: ETL falhou na última hora!"
    # Enviar notificação (email, Slack, etc.)
fi
```

---

## Referências

- [PostgreSQL UPSERT (ON CONFLICT)](https://www.postgresql.org/docs/15/sql-insert.html#SQL-ON-CONFLICT)
- [Pandas read_sql Chunking](https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html)
- [Watermark Pattern (Kafka)](https://kafka.apache.org/documentation/#streams_concepts_time)
- Documentação interna: `docs/ETL_V3_README.md`

---

## Notas de Revisão

**Próxima Revisão:** 2025-12-01
**Responsável:** Isaac (GenIAI)
**Gatilhos de Revisão:**
- Performance degradada (> 30 segundos)
- Taxa de falha > 1%
- Implementação de CDC no banco remoto
- Migração para streaming (Kafka, Debezium)