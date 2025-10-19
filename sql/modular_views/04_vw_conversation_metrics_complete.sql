-- ============================================================================
-- VIEW 4/6: vw_conversation_metrics_complete
-- Descrição: Métricas calculadas e flags booleanos por conversa
-- Performance: ⚡⚡⚡ RÁPIDA (cálculos simples, sem JOINs pesados)
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversation_metrics_complete AS

SELECT
    c.id AS conversation_id,

    -- ========================================
    -- MÉTRICAS DE TEMPO CALCULADAS
    -- ========================================

    -- Tempo até primeira resposta (segundos)
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at))::INTEGER
        ELSE NULL
    END AS first_response_time_seconds,

    -- Tempo até primeira resposta (minutos)
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN ROUND(EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) / 60.0, 1)
        ELSE NULL
    END AS first_response_time_minutes,

    -- Tempo até resolução (se resolvida)
    CASE
        WHEN c.status IN (1, 4) AND c.updated_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.updated_at - c.created_at))::INTEGER
        ELSE NULL
    END AS resolution_time_seconds,

    -- Tempo esperando (se em pending)
    CASE
        WHEN c.waiting_since IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - c.waiting_since))::INTEGER
        ELSE NULL
    END AS waiting_time_seconds,

    -- ========================================
    -- FLAGS BOOLEANOS - STATUS
    -- ========================================

    -- Está atribuída a um agente?
    (c.assignee_id IS NOT NULL) AS is_assigned,

    -- Está atribuída a um time?
    (c.team_id IS NOT NULL) AS has_team,

    -- Está resolvida?
    (c.status IN (1, 4)) AS is_resolved,

    -- Está aberta ou pendente?
    (c.status IN (0, 2)) AS is_open,

    -- Está pendente especificamente?
    (c.status = 2) AS is_pending,

    -- Está adiada (snoozed)?
    (c.snoozed_until IS NOT NULL AND c.snoozed_until > NOW()) AS is_snoozed,

    -- Tem contato identificado?
    (c.contact_id IS NOT NULL) AS has_contact,

    -- Está aguardando resposta?
    (c.waiting_since IS NOT NULL) AS is_waiting,

    -- ========================================
    -- FLAGS BOOLEANOS - PRIORIDADE E CAMPANHA
    -- ========================================

    -- Tem prioridade definida?
    (c.priority IS NOT NULL AND c.priority > 0) AS has_priority,

    -- É alta prioridade?
    (c.priority >= 3) AS is_high_priority,

    -- Veio de campanha?
    (c.campaign_id IS NOT NULL) AS is_from_campaign,

    -- ========================================
    -- FLAGS BOOLEANOS - TEMPO
    -- ========================================

    -- Resposta rápida? (<5 min)
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) < 300
        ELSE NULL
    END AS is_fast_response,

    -- Resposta lenta? (>30 min)
    CASE
        WHEN c.first_reply_created_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.first_reply_created_at - c.created_at)) > 1800
        ELSE NULL
    END AS is_slow_response,

    -- Resolução rápida? (<2 horas)
    CASE
        WHEN c.status IN (1, 4) AND c.updated_at IS NOT NULL AND c.created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.updated_at - c.created_at)) < 7200
        ELSE NULL
    END AS is_fast_resolution,

    -- Esperando muito tempo? (>1 hora)
    CASE
        WHEN c.waiting_since IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - c.waiting_since)) > 3600
        ELSE false
    END AS is_waiting_long,

    -- ========================================
    -- FLAGS BOOLEANOS - VISUALIZAÇÕES
    -- ========================================

    -- Contato viu a conversa?
    (c.contact_last_seen_at IS NOT NULL) AS contact_has_seen,

    -- Agente viu a conversa?
    (c.agent_last_seen_at IS NOT NULL) AS agent_has_seen,

    -- ========================================
    -- SCORES E CLASSIFICAÇÕES
    -- ========================================

    -- Prioridade como número (0-4)
    COALESCE(c.priority, 0) AS priority_score,

    -- Prioridade como texto
    CASE c.priority
        WHEN 0 THEN 'None'
        WHEN 1 THEN 'Low'
        WHEN 2 THEN 'Medium'
        WHEN 3 THEN 'High'
        WHEN 4 THEN 'Urgent'
        ELSE 'None'
    END AS priority_label,

    -- Status em português
    CASE c.status
        WHEN 0 THEN 'Aberta'
        WHEN 2 THEN 'Pendente'
        WHEN 1 THEN 'Resolvida'
        WHEN 4 THEN 'Fechada'
        WHEN 3 THEN 'Adiada'
        ELSE 'Desconhecido'
    END AS status_label_pt

FROM conversations c;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_conversation_metrics_complete IS
'View de métricas calculadas e flags booleanos das conversas.
Inclui: tempos de resposta, resolução, espera, status, prioridades.
Performance: Rápida, apenas cálculos sobre a tabela conversations.
NOTA: Status é INTEGER no Chatwoot: 0=open, 1=resolved, 2=pending, 3=snoozed, 4=closed';

GRANT SELECT ON vw_conversation_metrics_complete TO hetzner_dev_isaac_read;
