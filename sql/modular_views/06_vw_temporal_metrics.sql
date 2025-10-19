-- ============================================================================
-- VIEW 6/6: vw_temporal_metrics
-- Descrição: Metadados temporais para análise de sazonalidade e padrões
-- Performance: ⚡⚡⚡ MUITO RÁPIDA (cálculos simples sobre timestamps)
-- ============================================================================

CREATE OR REPLACE VIEW vw_temporal_metrics AS

SELECT
    c.id AS conversation_id,

    -- ========================================
    -- DATA E HORA (COMPONENTES)
    -- ========================================

    -- Data completa (apenas dia)
    c.created_at::DATE AS conversation_date,

    -- Ano
    EXTRACT(YEAR FROM c.created_at)::INTEGER AS conversation_year,

    -- Mês (1-12)
    EXTRACT(MONTH FROM c.created_at)::INTEGER AS conversation_month,

    -- Dia do mês (1-31)
    EXTRACT(DAY FROM c.created_at)::INTEGER AS conversation_day,

    -- Dia da semana (0=domingo, 6=sábado)
    EXTRACT(DOW FROM c.created_at)::INTEGER AS conversation_day_of_week,

    -- Hora (0-23)
    EXTRACT(HOUR FROM c.created_at)::INTEGER AS conversation_hour,

    -- Minuto (0-59)
    EXTRACT(MINUTE FROM c.created_at)::INTEGER AS conversation_minute,

    -- Semana do ano (1-53)
    EXTRACT(WEEK FROM c.created_at)::INTEGER AS conversation_week_of_year,

    -- Trimestre (1-4)
    EXTRACT(QUARTER FROM c.created_at)::INTEGER AS conversation_quarter,

    -- ========================================
    -- LABELS E CATEGORIAS TEMPORAIS
    -- ========================================

    -- Nome do dia da semana
    CASE EXTRACT(DOW FROM c.created_at)::INTEGER
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terça'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sábado'
    END AS conversation_day_name,

    -- Nome do dia da semana (abreviado)
    CASE EXTRACT(DOW FROM c.created_at)::INTEGER
        WHEN 0 THEN 'Dom'
        WHEN 1 THEN 'Seg'
        WHEN 2 THEN 'Ter'
        WHEN 3 THEN 'Qua'
        WHEN 4 THEN 'Qui'
        WHEN 5 THEN 'Sex'
        WHEN 6 THEN 'Sáb'
    END AS conversation_day_abbr,

    -- Nome do mês
    CASE EXTRACT(MONTH FROM c.created_at)::INTEGER
        WHEN 1 THEN 'Janeiro'
        WHEN 2 THEN 'Fevereiro'
        WHEN 3 THEN 'Março'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Maio'
        WHEN 6 THEN 'Junho'
        WHEN 7 THEN 'Julho'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro'
        WHEN 11 THEN 'Novembro'
        WHEN 12 THEN 'Dezembro'
    END AS conversation_month_name,

    -- Nome do mês (abreviado)
    CASE EXTRACT(MONTH FROM c.created_at)::INTEGER
        WHEN 1 THEN 'Jan'
        WHEN 2 THEN 'Fev'
        WHEN 3 THEN 'Mar'
        WHEN 4 THEN 'Abr'
        WHEN 5 THEN 'Mai'
        WHEN 6 THEN 'Jun'
        WHEN 7 THEN 'Jul'
        WHEN 8 THEN 'Ago'
        WHEN 9 THEN 'Set'
        WHEN 10 THEN 'Out'
        WHEN 11 THEN 'Nov'
        WHEN 12 THEN 'Dez'
    END AS conversation_month_abbr,

    -- ========================================
    -- PERÍODOS DO DIA
    -- ========================================

    -- Período do dia (4 categorias)
    CASE
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 6 AND 11 THEN 'Manhã'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 12 AND 17 THEN 'Tarde'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 18 AND 23 THEN 'Noite'
    END AS conversation_period,

    -- Período do dia (detalhado - 6 categorias)
    CASE
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 6 AND 8 THEN 'Manhã Cedo'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 9 AND 11 THEN 'Manhã'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 12 AND 14 THEN 'Meio-dia'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 15 AND 17 THEN 'Tarde'
        WHEN EXTRACT(HOUR FROM c.created_at) BETWEEN 18 AND 23 THEN 'Noite'
    END AS conversation_period_detailed,

    -- ========================================
    -- FLAGS BOOLEANOS TEMPORAIS
    -- ========================================

    -- É dia útil? (segunda a sexta)
    (EXTRACT(DOW FROM c.created_at)::INTEGER BETWEEN 1 AND 5) AS is_weekday,

    -- É fim de semana? (sábado ou domingo)
    (EXTRACT(DOW FROM c.created_at)::INTEGER IN (0, 6)) AS is_weekend,

    -- É horário comercial? (9h-18h em dia útil)
    (
        EXTRACT(DOW FROM c.created_at)::INTEGER BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM c.created_at) BETWEEN 9 AND 17
    ) AS is_business_hours,

    -- É horário estendido? (8h-20h em dia útil)
    (
        EXTRACT(DOW FROM c.created_at)::INTEGER BETWEEN 1 AND 5
        AND EXTRACT(HOUR FROM c.created_at) BETWEEN 8 AND 19
    ) AS is_extended_hours,

    -- É noite/madrugada? (20h-6h)
    (
        EXTRACT(HOUR FROM c.created_at) >= 20
        OR EXTRACT(HOUR FROM c.created_at) < 6
    ) AS is_night_time,

    -- É horário de almoço? (12h-14h)
    (EXTRACT(HOUR FROM c.created_at) BETWEEN 12 AND 13) AS is_lunch_time,

    -- É início do mês? (primeiros 10 dias)
    (EXTRACT(DAY FROM c.created_at) <= 10) AS is_start_of_month,

    -- É fim do mês? (últimos 10 dias)
    (
        EXTRACT(DAY FROM c.created_at) >
        EXTRACT(DAY FROM (DATE_TRUNC('month', c.created_at) + INTERVAL '1 month - 10 days')::DATE)
    ) AS is_end_of_month,

    -- ========================================
    -- DATAS RELATIVAS
    -- ========================================

    -- Dias desde criação até hoje
    (CURRENT_DATE - c.created_at::DATE)::INTEGER AS days_since_creation,

    -- É de hoje?
    (c.created_at::DATE = CURRENT_DATE) AS is_today,

    -- É de ontem?
    (c.created_at::DATE = CURRENT_DATE - 1) AS is_yesterday,

    -- É desta semana?
    (c.created_at >= DATE_TRUNC('week', CURRENT_DATE)) AS is_this_week,

    -- É deste mês?
    (c.created_at >= DATE_TRUNC('month', CURRENT_DATE)) AS is_this_month,

    -- É deste ano?
    (EXTRACT(YEAR FROM c.created_at) = EXTRACT(YEAR FROM CURRENT_DATE)) AS is_this_year,

    -- ========================================
    -- FORMATAÇÕES ÚTEIS
    -- ========================================

    -- Data formatada (YYYY-MM-DD)
    TO_CHAR(c.created_at, 'YYYY-MM-DD') AS conversation_date_formatted,

    -- Data e hora formatada (YYYY-MM-DD HH24:MI)
    TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') AS conversation_datetime_formatted,

    -- Ano-Mês (para agrupamentos)
    TO_CHAR(c.created_at, 'YYYY-MM') AS conversation_year_month,

    -- Ano-Semana (para agrupamentos)
    TO_CHAR(c.created_at, 'IYYY-IW') AS conversation_year_week

FROM conversations c;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_temporal_metrics IS
'View de métricas temporais para análise de sazonalidade e padrões.
Inclui: componentes de data/hora, categorias, períodos, flags booleanos.
Performance: Muito rápida, apenas cálculos sobre timestamps.
Uso: Análise de tendências, heatmaps, filtros temporais.';

GRANT SELECT ON vw_temporal_metrics TO hetzner_dev_isaac_read;
