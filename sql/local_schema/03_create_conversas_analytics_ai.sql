-- ============================================================================
-- TABELA: conversas_analytics_ai
-- Descrição: Armazena análises de IA das conversas para leads não convertidos
-- Relacionamento: 1:1 com conversas_analytics (conversation_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversas_analytics_ai (
    id SERIAL PRIMARY KEY,

    -- Relacionamento
    conversation_id INTEGER NOT NULL UNIQUE,

    -- Campos extraídos pela IA da conversa
    condicao_fisica TEXT,                    -- Condição física do lead (ex: "sedentário", "ativo")
    objetivo TEXT,                           -- Objetivo na academia (ex: "perda de peso", "ganho de massa")

    -- Análises geradas pela IA
    analise_ia TEXT NOT NULL,                -- Resumo breve da conversa
    sugestao_disparo TEXT NOT NULL,          -- Mensagem sugerida para follow-up/remarketing
    probabilidade_conversao INTEGER NOT NULL CHECK (probabilidade_conversao BETWEEN 0 AND 5),

    -- Metadados
    data_atualizacao_telefone TIMESTAMP,     -- Data da última atualização de telefone (futuro)

    -- Controle de análise
    analisado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    modelo_ia VARCHAR(50) NOT NULL,          -- Modelo usado (ex: "gpt-4")
    versao_prompt INTEGER DEFAULT 1,         -- Versão do prompt usado

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraint de FK
    CONSTRAINT fk_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversas_analytics(conversation_id)
        ON DELETE CASCADE
);

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Índice principal por conversation_id (já é UNIQUE, mas explícito)
CREATE INDEX IF NOT EXISTS idx_analytics_ai_conversation_id
    ON conversas_analytics_ai(conversation_id);

-- Índice por probabilidade de conversão (para filtrar leads quentes)
CREATE INDEX IF NOT EXISTS idx_analytics_ai_probabilidade
    ON conversas_analytics_ai(probabilidade_conversao DESC);

-- Índice por data de análise (para controle)
CREATE INDEX IF NOT EXISTS idx_analytics_ai_analisado_em
    ON conversas_analytics_ai(analisado_em DESC);

-- ============================================================================
-- TRIGGER PARA ATUALIZAR updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_conversas_analytics_ai_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversas_analytics_ai_updated_at
    BEFORE UPDATE ON conversas_analytics_ai
    FOR EACH ROW
    EXECUTE FUNCTION update_conversas_analytics_ai_updated_at();

-- ============================================================================
-- VIEW: vw_leads_nao_convertidos_com_ia
-- Descrição: Combina conversas_analytics + conversas_analytics_ai
-- ============================================================================

CREATE OR REPLACE VIEW vw_leads_nao_convertidos_com_ia AS
SELECT
    ca.conversation_id,
    ca.contact_name,
    ca.contact_phone,
    ca.conversation_created_at AS data_primeiro_contato,
    ca.last_activity_at AS data_ultima_conversa,
    ca.message_compiled AS conversa_compilada,

    -- Dados da IA
    ai.condicao_fisica,
    ai.objetivo,
    ai.analise_ia,
    ai.sugestao_disparo,
    ai.probabilidade_conversao,
    ai.data_atualizacao_telefone,
    ai.analisado_em,
    ai.modelo_ia

FROM conversas_analytics ca
LEFT JOIN conversas_analytics_ai ai ON ca.conversation_id = ai.conversation_id
WHERE ca.contact_messages_count > 0  -- Apenas leads que engajaram
ORDER BY ai.probabilidade_conversao DESC NULLS LAST, ca.last_activity_at DESC;

-- ============================================================================
-- COMENTÁRIOS
-- ============================================================================

COMMENT ON TABLE conversas_analytics_ai IS
'Análises de IA das conversas para identificar leads não convertidos de alto potencial';

COMMENT ON COLUMN conversas_analytics_ai.condicao_fisica IS
'Condição física do lead extraída da conversa pela IA';

COMMENT ON COLUMN conversas_analytics_ai.objetivo IS
'Objetivo do lead na academia (perda de peso, ganho de massa, etc)';

COMMENT ON COLUMN conversas_analytics_ai.analise_ia IS
'Resumo breve da conversa gerado pela IA';

COMMENT ON COLUMN conversas_analytics_ai.sugestao_disparo IS
'Mensagem personalizada sugerida pela IA para follow-up ou remarketing';

COMMENT ON COLUMN conversas_analytics_ai.probabilidade_conversao IS
'Probabilidade de conversão do lead (0=baixa, 5=alta) classificada pela IA';

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT ON conversas_analytics_ai TO hetzner_dev_isaac_read;
GRANT SELECT ON vw_leads_nao_convertidos_com_ia TO hetzner_dev_isaac_read;
