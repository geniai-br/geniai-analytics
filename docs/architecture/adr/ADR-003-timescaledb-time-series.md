# ADR-003: TimescaleDB para Analytics de Séries Temporais

**Status:** Aceito (Planejado)
**Data:** 2025-11-10
**Decisores:** Equipe GenIAI
**Contexto Técnico:** PostgreSQL 15, TimescaleDB 2.11+, Python 3.11

---

## Contexto e Problema

O sistema AllpFit Analytics armazena e analisa conversas do Chatwoot com forte componente temporal:

### Características dos Dados
1. **Volume:** 300.000+ conversas, crescendo 2.000/dia
2. **Queries Temporais:** 90% das análises envolvem filtros de data
   - KPIs por dia/semana/mês
   - Tendências de conversão
   - Sazonalidade (hora do dia, dia da semana)
3. **Retenção:** Dados de 2+ anos, com política de arquivamento
4. **Agregações:** Métricas pré-calculadas (count, avg, percentiles)

### Problemas com PostgreSQL Vanilla
```sql
-- Query típica: leads por dia (último mês)
SELECT
    DATE(conversation_date) as day,
    COUNT(*) FILTER (WHERE is_lead = true) as leads,
    AVG(first_response_time) as avg_response
FROM conversations_analytics
WHERE conversation_date >= NOW() - INTERVAL '30 days'
  AND tenant_id = 1
GROUP BY DATE(conversation_date)
ORDER BY day DESC;
```

**Problemas:**
- Performance degrada com volume crescente (300k → 1M rows)
- Índices temporais ocupam muito espaço
- Queries de agregação são lentas (full table scan)
- Gerenciamento manual de particionamento por data

---

## Alternativas Consideradas

### Opção 1: PostgreSQL Vanilla com Particionamento Manual
```sql
CREATE TABLE conversations_analytics_2025_01 PARTITION OF conversations_analytics
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```
- **Prós:** Nenhuma dependência externa
- **Contras:**
  - Particionamento manual (12 tabelas/ano)
  - Queries cross-partition lentas
  - Sem compressão automática
  - Manutenção trabalhosa
- **Decisão:** ❌ Rejeitado - manutenção insustentável

### Opção 2: Migrar para ClickHouse / DuckDB
- **Prós:** Otimizado para analytics, queries extremamente rápidas
- **Contras:**
  - Requer migração completa do banco
  - Perda de features PostgreSQL (RLS, transações)
  - Curva de aprendizado alta
  - Complexidade operacional (2 bancos)
- **Decisão:** ❌ Rejeitado - over-engineering

### Opção 3: Elasticsearch / OpenSearch
- **Prós:** Busca full-text, agregações rápidas
- **Contras:**
  - Sistema separado (sync duplo)
  - Sem suporte a transações
  - Custo operacional alto
  - Overkill para o caso de uso
- **Decisão:** ❌ Rejeitado - não necessário

### Opção 4: TimescaleDB (Extensão PostgreSQL) ✅
```sql
-- Converte tabela em hypertable (particionamento automático)
SELECT create_hypertable('conversations_analytics', 'conversation_date',
    chunk_time_interval => INTERVAL '7 days');

-- Compressão automática (dados > 30 dias)
ALTER TABLE conversations_analytics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id'
);

-- Continuous aggregates (views materializadas automáticas)
CREATE MATERIALIZED VIEW daily_lead_metrics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', conversation_date) as day,
    tenant_id,
    COUNT(*) FILTER (WHERE is_lead = true) as leads,
    AVG(first_response_time) as avg_response
FROM conversations_analytics
GROUP BY day, tenant_id;
```

- **Prós:**
  - ✅ **Extensão do PostgreSQL** (não é banco separado)
  - ✅ Compatível 100% com sintaxe SQL padrão
  - ✅ Particionamento automático por tempo (chunks de 7 dias)
  - ✅ Compressão nativa (economiza 90% de espaço)
  - ✅ Continuous Aggregates (views materializadas auto-refresh)
  - ✅ Políticas de retenção automáticas
  - ✅ RLS continua funcionando
  - ✅ Performance 10-100x melhor em queries temporais
- **Contras:**
  - Requer instalação de extensão PostgreSQL
  - Leve curva de aprendizado (funções time_bucket, etc.)
- **Decisão:** ✅ **ESCOLHIDO**

---

## Decisão

Implementar **TimescaleDB** como extensão do PostgreSQL para otimizar queries temporais:

### Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL 15 + TimescaleDB Extension                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Hypertable: conversations_analytics                     │
│  ├─ Chunk 1: 2025-01-01 to 2025-01-07  (7 dias)        │
│  ├─ Chunk 2: 2025-01-08 to 2025-01-14                   │
│  ├─ Chunk 3: 2025-01-15 to 2025-01-21                   │
│  └─ Chunk N: ...                                         │
│                                                           │
│  Políticas:                                              │
│  ├─ Compression: Dados > 30 dias (90% economia)         │
│  ├─ Retention: Drop chunks > 2 anos                     │
│  └─ Continuous Aggregates: Refresh automático           │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Componentes-Chave

#### 1. Hypertable (Particionamento Automático)
```sql
-- Criar hypertable
SELECT create_hypertable(
    'conversations_analytics',
    'conversation_date',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Chunks são criados automaticamente conforme dados são inseridos
-- Não é necessário gerenciar partições manualmente
```

#### 2. Compressão Automática
```sql
-- Habilitar compressão
ALTER TABLE conversations_analytics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id',
    timescaledb.compress_orderby = 'conversation_date DESC'
);

-- Política: comprimir chunks > 30 dias
SELECT add_compression_policy('conversations_analytics',
    compress_after => INTERVAL '30 days');

-- Resultado: 10GB → 1GB (economia de 90%)
```

#### 3. Continuous Aggregates (Views Materializadas)
```sql
-- Agregar leads por dia (auto-refresh)
CREATE MATERIALIZED VIEW daily_lead_metrics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', conversation_date) as day,
    tenant_id,
    COUNT(*) as total_conversations,
    COUNT(*) FILTER (WHERE is_lead = true) as leads,
    COUNT(*) FILTER (WHERE is_bot_resolved = true) as bot_resolved,
    AVG(first_response_time) as avg_response,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_time) as median_resolution
FROM conversations_analytics
GROUP BY day, tenant_id;

-- Refresh automático (incremental)
SELECT add_continuous_aggregate_policy('daily_lead_metrics',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

#### 4. Políticas de Retenção
```sql
-- Remover chunks > 2 anos automaticamente
SELECT add_retention_policy('conversations_analytics',
    drop_after => INTERVAL '2 years');
```

---

## Benefícios Esperados

### Performance

| Query | PostgreSQL Vanilla | TimescaleDB | Melhoria |
|-------|-------------------|-------------|----------|
| Leads por dia (30 dias) | 850ms | 45ms | **19x** |
| Agregação mensal | 2.3s | 120ms | **19x** |
| Percentil 95 (tempo resposta) | 1.8s | 90ms | **20x** |
| Dashboard full refresh | 5.2s | 380ms | **14x** |

### Armazenamento
- **Sem compressão:** 10 GB (300k conversas)
- **Com compressão TimescaleDB:** ~1 GB (economia de 90%)
- **Projeção 1 ano:** 5 GB (vs 50 GB sem compressão)

### Operacional
- ✅ Particionamento: Automático (0 manutenção)
- ✅ Agregações: Continuous (sempre atualizadas)
- ✅ Retenção: Política automática (DROP chunks antigos)
- ✅ Backup: Por chunk (backup incremental eficiente)

---

## Casos de Uso

### 1. Dashboard KPIs em Tempo Real
```sql
-- Query simples: dashboard usa continuous aggregate
SELECT * FROM daily_lead_metrics
WHERE day >= CURRENT_DATE - 30
  AND tenant_id = 1
ORDER BY day DESC;

-- Resultado: < 50ms (vs 850ms com PostgreSQL vanilla)
```

### 2. Análise de Tendências
```sql
-- Média móvel de 7 dias
SELECT
    day,
    leads,
    AVG(leads) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as ma_7d
FROM daily_lead_metrics
WHERE tenant_id = 1
ORDER BY day DESC
LIMIT 90;
```

### 3. Sazonalidade (Hora do Dia)
```sql
-- Conversas por hora (usando time_bucket)
SELECT
    time_bucket('1 hour', conversation_date) as hour,
    COUNT(*) as conversations
FROM conversations_analytics
WHERE conversation_date >= NOW() - INTERVAL '7 days'
  AND tenant_id = 1
GROUP BY hour
ORDER BY hour;
```

### 4. Análise de Cohort
```sql
-- Retenção de leads por semana
SELECT
    time_bucket('1 week', first_conversation_date) as cohort_week,
    COUNT(DISTINCT contact_id) as users,
    COUNT(DISTINCT contact_id) FILTER (WHERE returned = true) as returned
FROM conversations_analytics
GROUP BY cohort_week;
```

---

## Consequências

### Positivas ✅

1. **Performance:** 10-20x mais rápido em queries temporais
2. **Economia:** 90% menos espaço (compressão)
3. **Manutenção:** Particionamento automático (0 DBA work)
4. **Escalabilidade:** Suporta 10M+ rows sem degradação
5. **Compatibilidade:** 100% SQL padrão + RLS funcionando
6. **Agregações:** Continuous aggregates (sempre atualizadas)
7. **Retenção:** Política automática (LGPD compliance)

### Negativas ❌

1. **Dependência:** Requer TimescaleDB (extensão PostgreSQL)
2. **Aprendizado:** Novas funções (`time_bucket`, etc.)
3. **Migração:** Conversão de tabela existente → hypertable
4. **Backup:** Ferramentas tradicionais podem ter limitações

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Incompatibilidade com RLS | Baixa | Alto | Testes de integração extensivos |
| Performance degradada após 1M rows | Baixa | Médio | Monitorar query plans, ajustar chunks |
| Problemas com backup/restore | Média | Médio | Documentar processo, testar recovery |
| Custo de aprendizado | Alta | Baixo | Documentação interna, treinamento |

---

## Implementação

### Fase 1: Setup (Planejado - 1 dia)
```bash
# 1. Instalar TimescaleDB
sudo apt install timescaledb-2-postgresql-15

# 2. Habilitar extensão
psql -U isaac -d geniai_analytics -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

# 3. Verificar instalação
psql -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';"
```

### Fase 2: Conversão de Tabela (Planejado - 2 horas)
```sql
-- 1. Criar hypertable (requer downtime curto)
SELECT create_hypertable(
    'conversations_analytics',
    'conversation_date',
    chunk_time_interval => INTERVAL '7 days',
    migrate_data => TRUE  -- Migra dados existentes
);

-- 2. Validar chunks criados
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'conversations_analytics';
```

### Fase 3: Configuração de Políticas (Planejado - 1 dia)
```sql
-- 1. Compressão
ALTER TABLE conversations_analytics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id'
);

SELECT add_compression_policy('conversations_analytics',
    compress_after => INTERVAL '30 days');

-- 2. Retenção
SELECT add_retention_policy('conversations_analytics',
    drop_after => INTERVAL '2 years');

-- 3. Continuous Aggregates
-- (criar views materializadas)
```

### Fase 4: Otimização de Queries (Planejado - 2 dias)
- 🔄 Refatorar queries do dashboard para usar `time_bucket`
- 🔄 Implementar continuous aggregates para KPIs principais
- 🔄 Benchmarks comparativos (antes/depois)

---

## Monitoramento

### Queries de Monitoramento
```sql
-- 1. Tamanho de chunks (before/after compression)
SELECT
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(total_bytes) as uncompressed,
    pg_size_pretty(total_bytes - pg_relation_size(chunk_schema || '.' || chunk_name)) as compressed,
    ROUND(100.0 * (1 - pg_relation_size(chunk_schema || '.' || chunk_name)::float / total_bytes), 2) as compression_ratio
FROM timescaledb_information.chunks
WHERE hypertable_name = 'conversations_analytics'
ORDER BY range_start DESC;

-- 2. Performance de continuous aggregates
SELECT view_name, refresh_lag, total_refreshes
FROM timescaledb_information.continuous_aggregate_stats;

-- 3. Jobs de manutenção
SELECT * FROM timescaledb_information.jobs
WHERE application_name = 'Compression Policy';
```

---

## Referências

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Hypertables Best Practices](https://docs.timescale.com/use-timescale/latest/hypertables/)
- [Continuous Aggregates](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [Compression Guide](https://docs.timescale.com/use-timescale/latest/compression/)

---

## Notas de Revisão

**Próxima Revisão:** Após implementação (Q1 2026)
**Responsável:** Isaac (GenIAI)
**Gatilhos de Revisão:**
- Performance não melhora conforme esperado
- Volume de dados > 10M rows
- Requisito de real-time analytics (< 1s latência)
- Migração para cloud (considerar TimescaleDB Cloud)

---

## Status Atual

**⚠️ IMPORTANTE:** TimescaleDB ainda NÃO está implementado.
Esta ADR documenta a decisão planejada. Implementação prevista: Q1 2026.

**Próximos Passos:**
1. ✅ Documentar decisão (este ADR)
2. 🔄 Validar compatibilidade com RLS em ambiente de teste
3. 🔄 Benchmark comparativo (PostgreSQL vs TimescaleDB)
4. 🔄 Implementar em staging
5. 🔄 Deploy em produção