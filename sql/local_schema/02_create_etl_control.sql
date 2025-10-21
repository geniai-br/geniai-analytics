-- ============================================================================
-- TABELA DE CONTROLE DO ETL - etl_control
-- ============================================================================
-- BANCO: LOCAL (allpfit)
-- Esta tabela registra TODAS as execuções do ETL (incremental ou full)
-- Permite rastreabilidade, monitoramento e controle de watermark
-- ============================================================================

DROP TABLE IF EXISTS etl_control CASCADE;

CREATE TABLE etl_control (
    -- ========================================
    -- IDENTIFICAÇÃO DA EXECUÇÃO
    -- ========================================
    id SERIAL PRIMARY KEY,
    execution_id UUID DEFAULT gen_random_uuid() NOT NULL,

    -- ========================================
    -- TIMESTAMPS
    -- ========================================
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- ========================================
    -- STATUS DA EXECUÇÃO
    -- ========================================
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failed'

    -- ========================================
    -- WATERMARK (Controle Incremental)
    -- ========================================
    watermark_start TIMESTAMP,  -- Início da janela (última execução bem-sucedida)
    watermark_end TIMESTAMP,    -- Fim da janela (MAX(conversation_updated_at) desta execução)

    -- ========================================
    -- ESTATÍSTICAS DE DADOS
    -- ========================================
    rows_extracted INTEGER DEFAULT 0,      -- Linhas lidas do banco remoto
    rows_inserted INTEGER DEFAULT 0,       -- Novas conversas inseridas
    rows_updated INTEGER DEFAULT 0,        -- Conversas atualizadas
    rows_unchanged INTEGER DEFAULT 0,      -- Conversas sem mudança
    rows_deleted INTEGER DEFAULT 0,        -- Conversas deletadas (futuro)

    -- ========================================
    -- PERFORMANCE
    -- ========================================
    duration_seconds NUMERIC(10,2),        -- Tempo total de execução
    extract_duration_seconds NUMERIC(10,2),
    transform_duration_seconds NUMERIC(10,2),
    load_duration_seconds NUMERIC(10,2),

    -- ========================================
    -- TIPO DE CARGA
    -- ========================================
    is_full_load BOOLEAN DEFAULT FALSE,    -- TRUE = carga completa, FALSE = incremental
    load_type VARCHAR(20),                 -- 'incremental', 'full', 'manual'

    -- ========================================
    -- ERROS E LOGS
    -- ========================================
    error_message TEXT,
    error_traceback TEXT,

    -- ========================================
    -- METADATA
    -- ========================================
    etl_version VARCHAR(20) DEFAULT 'v3.0',
    triggered_by VARCHAR(50),              -- 'scheduler', 'manual', 'api'
    hostname VARCHAR(255),                 -- Servidor que executou

    -- ========================================
    -- OBSERVAÇÕES
    -- ========================================
    notes TEXT
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

CREATE INDEX idx_etl_control_started_at ON etl_control(started_at DESC);
CREATE INDEX idx_etl_control_status ON etl_control(status);
CREATE INDEX idx_etl_control_execution_id ON etl_control(execution_id);
CREATE INDEX idx_etl_control_watermark_end ON etl_control(watermark_end DESC);

-- ============================================================================
-- COMENTÁRIOS
-- ============================================================================

COMMENT ON TABLE etl_control IS
'Tabela de controle e auditoria do ETL.
Registra todas as execuções (sucesso ou falha) e mantém watermark para carga incremental.';

COMMENT ON COLUMN etl_control.execution_id IS 'UUID único de cada execução do ETL';
COMMENT ON COLUMN etl_control.watermark_start IS 'Data/hora de início da janela incremental (última execução)';
COMMENT ON COLUMN etl_control.watermark_end IS 'Data/hora de fim da janela (MAX updated_at desta execução)';
COMMENT ON COLUMN etl_control.status IS 'Status: running, success, failed';
COMMENT ON COLUMN etl_control.is_full_load IS 'TRUE se foi carga completa (TRUNCATE+INSERT), FALSE se incremental';

-- ============================================================================
-- FUNÇÃO AUXILIAR: Obter último watermark bem-sucedido
-- ============================================================================

CREATE OR REPLACE FUNCTION get_last_successful_watermark()
RETURNS TIMESTAMP AS $$
DECLARE
    last_watermark TIMESTAMP;
BEGIN
    SELECT watermark_end INTO last_watermark
    FROM etl_control
    WHERE status = 'success'
      AND watermark_end IS NOT NULL
    ORDER BY watermark_end DESC
    LIMIT 1;

    RETURN last_watermark;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_last_successful_watermark() IS
'Retorna o watermark_end da última execução bem-sucedida do ETL.
Usado para determinar a partir de quando buscar dados incrementais.';

-- ============================================================================
-- VIEW: Estatísticas do ETL (últimas 30 execuções)
-- ============================================================================

CREATE OR REPLACE VIEW vw_etl_stats AS
SELECT
    id,
    execution_id,
    started_at,
    completed_at,
    status,
    load_type,
    rows_extracted,
    rows_inserted,
    rows_updated,
    rows_unchanged,
    duration_seconds,
    ROUND((rows_inserted + rows_updated + rows_unchanged)::NUMERIC /
          NULLIF(duration_seconds, 0), 2) AS rows_per_second,
    error_message,
    triggered_by
FROM etl_control
ORDER BY started_at DESC
LIMIT 30;

COMMENT ON VIEW vw_etl_stats IS
'View com estatísticas das últimas 30 execuções do ETL.
Útil para monitoramento e debugging.';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
