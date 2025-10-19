-- ============================================================================
-- VIEW 2/6: vw_messages_compiled_complete
-- Descrição: Mensagens compiladas em JSON + informações básicas da conversa
-- Performance: ⚡⚡ MÉDIA (agregação de mensagens)
-- Baseado na view original vw_conversas_por_lead
-- ============================================================================

CREATE OR REPLACE VIEW vw_messages_compiled_complete AS

SELECT
    m.conversation_id,

    -- ========================================
    -- MESSAGE_COMPILED: JSON com todas as mensagens
    -- ========================================
    jsonb_agg(
        jsonb_build_object(
            'message_id', m.id,
            'text', m.content,
            'sender', m.sender_type,
            'sender_id', m.sender_id,
            'sent_at', m.created_at,
            'message_type', m.message_type,
            'content_type', m.content_type,
            'status', m.status,
            'private', m.private,
            'sentiment', m.sentiment,
            'source_id', m.source_id
        ) ORDER BY m.created_at
    ) AS message_compiled,

    -- ========================================
    -- CAMPOS DA VIEW ORIGINAL (compatibilidade)
    -- ========================================

    -- client_sender_id: Primeiro contato que enviou mensagem
    (ARRAY_AGG(m.sender_id ORDER BY m.created_at)
     FILTER (WHERE m.sender_type = 'Contact'))[1] AS client_sender_id,

    -- inbox_id: ID do canal
    MIN(m.inbox_id) AS inbox_id,

    -- client_phone: Telefone do cliente (busca na tabela contacts)
    (
        SELECT c.phone_number
        FROM contacts c
        WHERE c.id = (
            ARRAY_AGG(m.sender_id ORDER BY m.created_at)
            FILTER (WHERE m.sender_type = 'Contact')
        )[1]
        LIMIT 1
    ) AS client_phone,

    -- t_messages: Total de mensagens
    COUNT(*) AS t_messages,

    -- ========================================
    -- CAMPOS ADICIONAIS ÚTEIS
    -- ========================================

    -- Total de mensagens por tipo (incluindo privadas)
    COUNT(*) FILTER (WHERE m.private = false) AS total_messages_public,
    COUNT(*) FILTER (WHERE m.private = true) AS total_messages_private,

    -- Primeira e última mensagem (timestamps)
    MIN(m.created_at) AS first_message_at,
    MAX(m.created_at) AS last_message_at

FROM messages m

GROUP BY m.conversation_id;

-- ============================================================================
-- COMENTÁRIOS E GRANTS
-- ============================================================================

COMMENT ON VIEW vw_messages_compiled_complete IS
'View com mensagens compiladas em JSON por conversa.
Mantém compatibilidade com vw_conversas_por_lead original.
Adiciona campos extras: timestamps, contadores públicos/privados.
Performance: Média devido à agregação JSONB.';

GRANT SELECT ON vw_messages_compiled_complete TO hetzner_dev_isaac_read;
