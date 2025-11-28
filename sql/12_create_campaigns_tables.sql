-- ============================================================================
-- FASE 10: Sistema de Campanhas de Disparo
-- ============================================================================
-- Descrição: Cria tabelas para gerenciamento de campanhas de remarketing
--            com exportação CSV para sistema de disparo externo
--
-- Tabelas:
--   1. campaigns - Configuração de campanhas (template + contexto promocional)
--   2. campaign_leads - Variáveis geradas por lead
--   3. campaign_exports - Log de exportações CSV
--
-- Autor: Isaac (via Claude Code)
-- Data: 2025-11-26
-- Versão: 1.0
-- ============================================================================

-- Verificar conexão
SELECT current_database(), current_user, now() as execution_time;

-- ============================================================================
-- 1. TABELA: campaigns
-- ============================================================================
-- Armazena configurações de campanhas de remarketing
-- Cada tenant pode ter múltiplas campanhas

CREATE TABLE IF NOT EXISTS campaigns (
    -- Identificação
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Dados da campanha
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,

    -- Template META/WhatsApp (usado no Disparador)
    -- Formato: "Olá, {{1}}. Vi que {{2}}. Hoje {{3}}. Confirme abaixo!"
    template_text TEXT NOT NULL,
    template_variable_count INTEGER DEFAULT 3 CHECK (template_variable_count >= 1 AND template_variable_count <= 10),

    -- Contexto Promocional (JSON para a IA gerar variáveis)
    -- Exemplo: {"promocao": "40% off", "preco": "R$ 119", "validade": "30/Nov"}
    promotional_context JSONB NOT NULL DEFAULT '{}',

    -- Período de vigência
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    -- Status da campanha
    -- draft: rascunho (não processa leads)
    -- active: ativa (processa leads)
    -- paused: pausada temporariamente
    -- ended: encerrada (após end_date ou manual)
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'ended')),

    -- Métricas agregadas (atualizadas via trigger ou aplicação)
    leads_total INTEGER DEFAULT 0,
    leads_processed INTEGER DEFAULT 0,
    leads_exported INTEGER DEFAULT 0,
    total_cost_brl NUMERIC(10, 4) DEFAULT 0,

    -- Última exportação
    last_export_at TIMESTAMP,
    last_export_count INTEGER DEFAULT 0,

    -- Auditoria
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),

    -- Constraints
    CONSTRAINT campaigns_tenant_slug_unique UNIQUE(tenant_id, slug),
    CONSTRAINT campaigns_date_range_valid CHECK (end_date >= start_date)
);

-- Comentários
COMMENT ON TABLE campaigns IS 'Campanhas de remarketing para exportação CSV ao Disparador';
COMMENT ON COLUMN campaigns.slug IS 'Identificador URL-friendly único por tenant';
COMMENT ON COLUMN campaigns.template_text IS 'Template META/WhatsApp com variáveis {{1}}, {{2}}, {{3}}';
COMMENT ON COLUMN campaigns.promotional_context IS 'Contexto JSON para IA gerar variáveis personalizadas';
COMMENT ON COLUMN campaigns.status IS 'draft=rascunho, active=ativa, paused=pausada, ended=encerrada';

-- Índices
CREATE INDEX IF NOT EXISTS idx_campaigns_tenant_id ON campaigns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_tenant_status ON campaigns(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_campaigns_status_dates ON campaigns(status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at DESC);

-- ============================================================================
-- 2. TABELA: campaign_leads
-- ============================================================================
-- Armazena as variáveis geradas pela IA para cada lead de uma campanha

CREATE TABLE IF NOT EXISTS campaign_leads (
    -- Identificação
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL,

    -- Dados do lead (copiados para independência)
    contact_phone VARCHAR(30) NOT NULL,
    contact_name VARCHAR(255),

    -- Variáveis geradas pela IA (conforme template)
    -- var1 = {{1}} = nome/primeiro nome
    -- var2 = {{2}} = contexto personalizado
    -- var3 = {{3}} = oferta/CTA
    var1 VARCHAR(50),
    var2 TEXT,
    var3 TEXT,

    -- Preview da mensagem final renderizada
    message_preview TEXT,

    -- Status do processamento
    -- pending: aguardando processamento pela IA
    -- processing: em processamento
    -- processed: variáveis geradas com sucesso
    -- exported: incluído em pelo menos uma exportação CSV
    -- error: falha na geração (ver error_message)
    -- skipped: pulado por regra de negócio
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'exported', 'error', 'skipped')),
    error_message TEXT,

    -- Metadados da geração IA
    generation_metadata JSONB DEFAULT '{}',
    /*
    Exemplo:
    {
        "model": "gpt-4o-mini",
        "tokens_input": 250,
        "tokens_output": 150,
        "tokens_total": 400,
        "cost_brl": 0.0008,
        "duration_seconds": 2.5,
        "attempt": 1
    }
    */

    -- Contadores de exportação
    export_count INTEGER DEFAULT 0,
    last_exported_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Comentários
COMMENT ON TABLE campaign_leads IS 'Leads de campanhas com variáveis geradas pela IA';
COMMENT ON COLUMN campaign_leads.var1 IS 'Variável {{1}} - tipicamente primeiro nome do lead';
COMMENT ON COLUMN campaign_leads.var2 IS 'Variável {{2}} - contexto personalizado da conversa';
COMMENT ON COLUMN campaign_leads.var3 IS 'Variável {{3}} - oferta/CTA da campanha';
COMMENT ON COLUMN campaign_leads.message_preview IS 'Preview da mensagem final com variáveis substituídas';
COMMENT ON COLUMN campaign_leads.generation_metadata IS 'Metadados da geração: modelo, tokens, custo, tempo';

-- Índices
CREATE INDEX IF NOT EXISTS idx_campaign_leads_campaign_id ON campaign_leads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_leads_status ON campaign_leads(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_campaign_leads_conversation ON campaign_leads(conversation_id);
CREATE INDEX IF NOT EXISTS idx_campaign_leads_phone ON campaign_leads(contact_phone);
CREATE INDEX IF NOT EXISTS idx_campaign_leads_created_at ON campaign_leads(created_at DESC);

-- Constraint única: um lead só pode estar uma vez em cada campanha
CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_leads_unique
ON campaign_leads(campaign_id, conversation_id);

-- ============================================================================
-- 3. TABELA: campaign_exports
-- ============================================================================
-- Log de todas as exportações CSV realizadas

CREATE TABLE IF NOT EXISTS campaign_exports (
    -- Identificação
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

    -- Dados da exportação
    file_name VARCHAR(255) NOT NULL,
    leads_count INTEGER NOT NULL CHECK (leads_count > 0),
    file_size_bytes INTEGER,

    -- Quem exportou
    exported_by INTEGER REFERENCES users(id),
    exported_at TIMESTAMP DEFAULT NOW(),

    -- Metadados da exportação
    metadata JSONB DEFAULT '{}',
    /*
    Exemplo:
    {
        "leads_ids": [1, 2, 3, 4, 5],
        "filters_applied": {"status": "processed", "not_exported": true},
        "format": "csv",
        "encoding": "utf-8",
        "total_cost_brl": 0.05
    }
    */

    -- Notas opcionais
    notes TEXT
);

-- Comentários
COMMENT ON TABLE campaign_exports IS 'Log de exportações CSV de campanhas';
COMMENT ON COLUMN campaign_exports.file_name IS 'Nome do arquivo exportado (ex: campanha_blackfriday_20251126_1430.csv)';
COMMENT ON COLUMN campaign_exports.metadata IS 'Metadados: IDs dos leads, filtros aplicados, formato';

-- Índices
CREATE INDEX IF NOT EXISTS idx_campaign_exports_campaign_id ON campaign_exports(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_exports_exported_at ON campaign_exports(exported_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaign_exports_exported_by ON campaign_exports(exported_by);

-- ============================================================================
-- 4. ROW-LEVEL SECURITY (RLS)
-- ============================================================================
-- Garantir isolamento de dados por tenant

-- Habilitar RLS nas tabelas
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_exports ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- Policies para CAMPAIGNS
-- ----------------------------------------------------------------------------

-- Policy: Clientes só veem campanhas do próprio tenant
DROP POLICY IF EXISTS campaigns_tenant_isolation ON campaigns;
CREATE POLICY campaigns_tenant_isolation ON campaigns
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::INTEGER);

-- Policy: Super admin vê todas as campanhas
DROP POLICY IF EXISTS campaigns_super_admin ON campaigns;
CREATE POLICY campaigns_super_admin ON campaigns
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'super_admin');

-- ----------------------------------------------------------------------------
-- Policies para CAMPAIGN_LEADS
-- ----------------------------------------------------------------------------

-- Policy: Clientes só veem leads de campanhas do próprio tenant
DROP POLICY IF EXISTS campaign_leads_tenant_isolation ON campaign_leads;
CREATE POLICY campaign_leads_tenant_isolation ON campaign_leads
    FOR ALL
    USING (
        campaign_id IN (
            SELECT id FROM campaigns
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::INTEGER
        )
    );

-- Policy: Super admin vê todos os leads
DROP POLICY IF EXISTS campaign_leads_super_admin ON campaign_leads;
CREATE POLICY campaign_leads_super_admin ON campaign_leads
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'super_admin');

-- ----------------------------------------------------------------------------
-- Policies para CAMPAIGN_EXPORTS
-- ----------------------------------------------------------------------------

-- Policy: Clientes só veem exports de campanhas do próprio tenant
DROP POLICY IF EXISTS campaign_exports_tenant_isolation ON campaign_exports;
CREATE POLICY campaign_exports_tenant_isolation ON campaign_exports
    FOR ALL
    USING (
        campaign_id IN (
            SELECT id FROM campaigns
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::INTEGER
        )
    );

-- Policy: Super admin vê todos os exports
DROP POLICY IF EXISTS campaign_exports_super_admin ON campaign_exports;
CREATE POLICY campaign_exports_super_admin ON campaign_exports
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'super_admin');

-- ============================================================================
-- 5. FUNÇÃO: Atualizar updated_at automaticamente
-- ============================================================================

-- Trigger function (reutiliza se já existir)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para campaigns
DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
CREATE TRIGGER update_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para campaign_leads
DROP TRIGGER IF EXISTS update_campaign_leads_updated_at ON campaign_leads;
CREATE TRIGGER update_campaign_leads_updated_at
    BEFORE UPDATE ON campaign_leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. FUNÇÃO: Gerar slug a partir do nome
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_campaign_slug(campaign_name TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN lower(
        regexp_replace(
            regexp_replace(
                unaccent(campaign_name),
                '[^a-zA-Z0-9\s-]', '', 'g'
            ),
            '\s+', '-', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_campaign_slug IS 'Gera slug URL-friendly a partir do nome da campanha';

-- ============================================================================
-- 7. VERIFICAÇÃO FINAL
-- ============================================================================

-- Verificar tabelas criadas
SELECT
    table_name,
    (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('campaigns', 'campaign_leads', 'campaign_exports')
ORDER BY table_name;

-- Verificar índices
SELECT
    tablename,
    indexname
FROM pg_indexes
WHERE tablename IN ('campaigns', 'campaign_leads', 'campaign_exports')
ORDER BY tablename, indexname;

-- Verificar RLS
SELECT
    tablename,
    policyname,
    permissive,
    cmd
FROM pg_policies
WHERE tablename IN ('campaigns', 'campaign_leads', 'campaign_exports')
ORDER BY tablename, policyname;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
-- Próximos passos:
-- 1. Executar: psql -U johan_geniai -d geniai_analytics -f sql/12_create_campaigns_tables.sql
-- 2. Verificar criação das tabelas
-- 3. Implementar backend (CampaignService, VariableGenerator, CSVExporter)
-- ============================================================================