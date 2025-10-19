-- ============================================================================
-- VIEW 1/6: vw_conversations_base_complete
-- Descrição: Dados base das conversas com JOINs de tabelas relacionadas
-- Performance: ⚡⚡⚡ MUITO RÁPIDA (apenas JOINs simples, sem agregação)
-- ============================================================================

CREATE OR REPLACE VIEW vw_conversations_base_complete AS

SELECT
    -- ========================================
    -- IDENTIFICADORES PRINCIPAIS
    -- ========================================
    c.id AS conversation_id,
    c.display_id,
    c.uuid AS conversation_uuid,
    c.identifier AS conversation_identifier,
    c.account_id,

    -- ========================================
    -- STATUS E CLASSIFICAÇÃO
    -- ========================================
    c.status,
    c.priority,
    c.snoozed_until,
    c.sla_policy_id,

    -- ========================================
    -- ATRIBUIÇÃO
    -- ========================================
    c.assignee_id,
    c.team_id,
    c.campaign_id,

    -- ========================================
    -- RELACIONAMENTOS
    -- ========================================
    c.contact_id,
    c.inbox_id,
    c.contact_inbox_id,

    -- ========================================
    -- DATAS E TIMESTAMPS
    -- ========================================
    c.created_at AS conversation_created_at,
    c.updated_at AS conversation_updated_at,
    c.last_activity_at,
    c.first_reply_created_at,
    c.waiting_since,
    c.contact_last_seen_at,
    c.agent_last_seen_at,
    c.assignee_last_seen_at,

    -- ========================================
    -- LABELS E ATRIBUTOS
    -- ========================================
    c.cached_label_list,
    c.additional_attributes AS conversation_additional_attributes,
    c.custom_attributes AS conversation_custom_attributes,

    -- ========================================
    -- INFORMAÇÕES DO CONTATO
    -- ========================================
    cont.name AS contact_name,
    cont.email AS contact_email,
    cont.phone_number AS contact_phone,
    cont.identifier AS contact_identifier,
    cont.contact_type,
    cont.middle_name AS contact_middle_name,
    cont.last_name AS contact_last_name,
    cont.location AS contact_location,
    cont.country_code AS contact_country,
    cont.blocked AS contact_blocked,
    cont.created_at AS contact_created_at,
    cont.updated_at AS contact_updated_at,
    cont.last_activity_at AS contact_last_activity_at,
    cont.additional_attributes AS contact_additional_attributes,
    cont.custom_attributes AS contact_custom_attributes,

    -- ========================================
    -- INFORMAÇÕES DO INBOX (CANAL)
    -- ========================================
    i.name AS inbox_name,
    i.channel_type AS inbox_channel_type,
    i.channel_id AS inbox_channel_id,
    i.business_name AS inbox_business_name,
    i.timezone AS inbox_timezone,
    i.enable_auto_assignment AS inbox_auto_assignment_enabled,
    i.greeting_enabled AS inbox_greeting_enabled,
    i.greeting_message AS inbox_greeting_message,
    i.email_address AS inbox_email_address,
    i.working_hours_enabled AS inbox_working_hours_enabled,
    i.out_of_office_message AS inbox_out_of_office_message,
    i.csat_survey_enabled AS inbox_csat_enabled,
    i.allow_messages_after_resolved AS inbox_allow_messages_after_resolved,
    i.portal_id AS inbox_portal_id,
    i.sender_name_type AS inbox_sender_name_type,

    -- ========================================
    -- INFORMAÇÕES DO AGENTE (ASSIGNEE)
    -- ========================================
    u.name AS assignee_name,
    u.display_name AS assignee_display_name,
    u.email AS assignee_email,
    u.availability AS assignee_availability,
    u.type AS assignee_type,
    u.custom_attributes AS assignee_custom_attributes,

    -- ========================================
    -- INFORMAÇÕES DO TIME
    -- ========================================
    t.name AS team_name,
    t.description AS team_description,
    t.allow_auto_assign AS team_allow_auto_assign,

    -- ========================================
    -- INFORMAÇÕES DA CONTA
    -- ========================================
    acc.name AS account_name,
    acc.locale AS account_locale,
    acc.domain AS account_domain,
    acc.support_email AS account_support_email,
    acc.status AS account_status,

    -- ========================================
    -- INFORMAÇÕES DO CONTACT_INBOX
    -- ========================================
    ci.source_id AS contact_inbox_source_id,
    ci.hmac_verified AS contact_inbox_hmac_verified,
    ci.pubsub_token AS contact_inbox_pubsub_token

FROM conversations c

-- JOINs obrigatórios e opcionais
LEFT JOIN contacts cont ON cont.id = c.contact_id
LEFT JOIN inboxes i ON i.id = c.inbox_id
LEFT JOIN users u ON u.id = c.assignee_id
LEFT JOIN teams t ON t.id = c.team_id
LEFT JOIN accounts acc ON acc.id = c.account_id
LEFT JOIN contact_inboxes ci ON ci.id = c.contact_inbox_id;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_conversations_base_complete IS
'View base com todos os dados principais das conversas e relacionamentos.
Incluí JOINs com: contacts, inboxes, users, teams, accounts, contact_inboxes.
Performance: Rápida, sem agregações.
Uso: Base para outras views e consultas diretas.';

GRANT SELECT ON vw_conversations_base_complete TO hetzner_dev_isaac_read;
