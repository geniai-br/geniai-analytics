# GeniAI Analytics - Visão Geral do Projeto

> **Plataforma Multi-Tenant de Analytics para Chatwoot**
>
> Sistema SaaS de análise de conversas com Inteligência Artificial

---

## 📋 O QUE É O PROJETO

O **GeniAI Analytics** é uma plataforma multi-tenant de análise de conversas desenvolvida para empresas que utilizam o **Chatwoot** como sistema de atendimento ao cliente.

A plataforma permite que múltiplos clientes (academias, escolas, clínicas, lojas, etc.) analisem suas conversas de forma **isolada, segura e inteligente**, utilizando IA generativa para extrair insights e otimizar estratégias de conversão.

---

## 🎯 PROBLEMA QUE RESOLVE

### Desafios Comuns no Atendimento Digital

1. **Volume alto de conversas** - Milhares de mensagens por mês impossíveis de analisar manualmente
2. **Dados dispersos** - Informações espalhadas entre WhatsApp, Instagram, Telegram, Email
3. **Falta de insights** - Dificuldade em identificar padrões, oportunidades e gargalos
4. **Remarketing manual** - Tempo perdido identificando leads para reengajamento
5. **Sem visibilidade de ROI** - Impossível medir efetividade do atendimento

### Nossa Solução

- ✅ **Consolidação automática** de conversas de múltiplos canais (WhatsApp, Instagram, Telegram)
- ✅ **Dashboard interativo** com métricas de conversão, engajamento e performance
- ✅ **Análise por IA** de sentimento, intenção e classificação de leads
- ✅ **Exportação de dados** para remarketing e CRM
- ✅ **Multi-tenant** - Cada cliente vê apenas seus próprios dados

---

## 🏗️ ARQUITETURA DO SISTEMA

### Stack Tecnológico

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND                          │
├─────────────────────────────────────────────────────┤
│  Streamlit                                          │
│  - Dashboard interativo multi-tenant                │
│  - Autenticação por tenant                          │
│  - Visualizações Plotly                             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   BACKEND                           │
├─────────────────────────────────────────────────────┤
│  Python 3.11+                                       │
│  - ETL Pipeline (extração incremental)              │
│  - Integração OpenAI (GPT-4o-mini)                  │
│  - Row-Level Security (RLS)                         │
│  - Autenticação bcrypt                              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                   DATABASE                          │
├─────────────────────────────────────────────────────┤
│  PostgreSQL 14+ com RLS                             │
│  - TimescaleDB (hypertables para séries temporais)  │
│  - Isolamento por tenant (Row-Level Security)       │
│  - 9 tabelas (tenants, users, conversations, etc)   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│               FONTE DE DADOS                        │
├─────────────────────────────────────────────────────┤
│  Chatwoot (Open Source)                             │
│  - Banco PostgreSQL remoto                          │
│  - Conversas de múltiplos canais                    │
│  - Inboxes por cliente                              │
└─────────────────────────────────────────────────────┘
```

### Componentes Principais

#### 1. **ETL Pipeline** (`src/etl/`)
- Extração incremental de conversas do Chatwoot
- Transformação e enriquecimento de dados
- Carga no banco multi-tenant com isolamento por tenant
- Automação via Systemd Timers (execução a cada 30 minutos)

#### 2. **Dashboard Multi-Tenant** (`src/multi_tenant/dashboards/`)
- Interface web responsiva com Streamlit
- Autenticação por email/senha com sessões seguras
- Visualizações interativas (Plotly, tabelas, cards)
- Filtros dinâmicos (por inbox, data, status, classificação IA)

#### 3. **Análise com IA** (`src/multi_tenant/ai/`)
- Integração com OpenAI GPT-4o-mini
- Análise de sentimento e intenção
- Classificação de leads (Alto/Médio/Baixo interesse)
- Score de conversão (0-100%)

#### 4. **Banco de Dados** (`sql/`)
- PostgreSQL com Row-Level Security (RLS)
- Isolamento total entre clientes (tenants)
- TimescaleDB para otimização de séries temporais
- Backup automático e auditoria

---

## 🔐 MULTI-TENANCY E SEGURANÇA

### Estratégia de Isolamento

O sistema utiliza **Single Database com Row-Level Security (RLS)** para garantir isolamento total entre clientes:

```sql
-- Cada tabela possui tenant_id
CREATE TABLE conversations_analytics (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,  -- ← Identifica o cliente
    conversation_id INTEGER,
    contact_name VARCHAR(255),
    ...
);

-- RLS garante que cada cliente vê apenas seus dados
CREATE POLICY tenant_isolation
ON conversations_analytics
FOR ALL
TO authenticated_users
USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
```

### Garantias de Segurança

- ✅ **Isolamento de dados** - RLS impede acesso entre tenants mesmo com bug no código
- ✅ **Autenticação segura** - Senhas com bcrypt, sessões com expiração
- ✅ **Auditoria completa** - Log de todas as ações administrativas
- ✅ **Backup automático** - Proteção contra perda de dados

---

## 🚀 FUNCIONALIDADES

### Dashboard Cliente

#### 📊 Visão Geral (Cards KPI)
- Total de conversas
- Taxa de conversão de leads
- Taxa de conversão para CRM
- Tempo médio de primeira resposta

#### 📈 Gráficos Interativos
- Evolução temporal de conversas (área)
- Distribuição de status (pizza)
- Conversões ao longo do tempo (barras empilhadas)
- Análise por inbox (agregada ou separada)

#### 🔍 Tabela de Leads
- Nome, telefone, status, inbox
- Classificação IA (Alto/Médio/Baixo)
- Score de conversão (0-100%)
- Prévia da conversa (3 primeiras mensagens)
- Filtros rápidos (6 filtros acima da tabela)

#### 💬 Conversas Completas
- Expandir até 10 conversas para leitura
- Emojis por tipo de sender (👤 Contato, 🤖 Bot, 👨‍💼 Agente)
- Timestamps e ordenação cronológica

#### 📤 Exportação
- CSV formatado para remarketing
- Inclui: nome, telefone, status, classificação IA, score

### Painel Admin (GeniAI)

#### 👥 Gestão de Tenants
- Criar/editar/desativar clientes
- Configurar inboxes por cliente
- Gerenciar planos e limites

#### 🔑 Gestão de Usuários
- Criar usuários para cada tenant
- Roles: client, admin, super_admin
- Resetar senhas

#### 📊 Métricas Cross-Tenant
- Visão consolidada de todos os clientes
- Comparação de performance entre tenants

---

## 🔄 FLUXO DE DADOS

```
1. EXTRAÇÃO (ETL)
   Chatwoot DB → ETL Pipeline → geniai_analytics DB
   - A cada 30 minutos (Systemd Timer)
   - Sincronização incremental (apenas novos dados)
   - Watermark por tenant (controle de última sincronização)

2. ANÁLISE IA (Opcional)
   Conversas novas → OpenAI GPT-4o-mini → Análise salva no DB
   - Sentimento: positivo/neutro/negativo
   - Intenção: informação/compra/suporte/reclamação
   - Classificação: Alto/Médio/Baixo interesse
   - Score: 0-100% probabilidade de conversão

3. VISUALIZAÇÃO (Dashboard)
   DB → Streamlit → Cliente vê dashboard
   - Login com email/senha
   - RLS garante isolamento por tenant
   - Cache de 5 minutos para performance
```

---

## 📊 MÉTRICAS E KPIs

### Métricas de Conversão
- **Total de Conversas**: Volume absoluto de atendimentos
- **Leads Qualificados**: Conversas com potencial comercial
- **Visitas Agendadas**: Leads que avançaram no funil
- **CRM Convertidos**: Leads que viraram clientes

### Métricas de Performance
- **Taxa de Conversão (Leads)**: % de conversas que viraram leads
- **Taxa de Conversão (CRM)**: % de leads que viraram clientes
- **Tempo Médio de Primeira Resposta**: Velocidade de atendimento
- **Score IA Médio**: Qualidade geral dos leads

### Análise por Inbox
- Métricas separadas por canal (WhatsApp, Instagram, Telegram)
- Comparação de performance entre canais
- Identificação de canais mais efetivos

---

## 🛠️ TECNOLOGIAS UTILIZADAS

### Backend
- **Python 3.11+** - Linguagem principal
- **Pandas** - Manipulação de dados
- **psycopg2** - Conexão PostgreSQL
- **OpenAI SDK** - Integração GPT-4o-mini
- **bcrypt** - Hash de senhas

### Frontend
- **Streamlit** - Framework web para dashboards
- **Plotly** - Gráficos interativos
- **st-aggrid** - Tabelas avançadas (futuro)

### Database
- **PostgreSQL 14+** - Banco relacional
- **TimescaleDB** - Extensão para séries temporais
- **Row-Level Security (RLS)** - Isolamento multi-tenant

### DevOps
- **Systemd Timers** - Automação de ETL
- **Git** - Controle de versão
- **GitHub** - Repositório remoto

---

## 📈 CASOS DE USO

### 1. Academia/CrossFit
- Analisar conversas de leads interessados em matrículas
- Identificar leads "quentes" para remarketing
- Medir taxa de conversão de trial → matrícula
- Exportar leads inativos para campanhas WhatsApp

### 2. Clínica/Consultório
- Rastrear agendamentos via WhatsApp
- Analisar motivos de cancelamento (IA)
- Medir tempo de resposta para agendamentos
- Identificar horários de maior demanda

### 3. E-commerce/Loja
- Análise de dúvidas pré-venda
- Identificar produtos com mais dúvidas
- Medir conversão de dúvida → compra
- Remarketing de carrinhos abandonados

### 4. Escola/Educação
- Acompanhar processo de matrícula
- Analisar principais dúvidas de pais
- Medir taxa de conversão por campanha
- Exportar leads para telemarketing

---

## 🔮 ROADMAP

### Fase 1-7: Sistema Base ✅ (Concluído)
- Multi-tenancy com RLS
- Dashboard genérico aplicável a qualquer segmento
- ETL automatizado
- Integração OpenAI para análise de conversas

### Fase 8: Remarketing Inteligente (Planejado)
- Identificação automática de leads inativos (24h sem resposta)
- Geração de mensagens de reengajamento com IA
- Templates contextuais (RECENTE/MEDIO/FRIO)
- Webhooks para disparo automático

### Futuro (Ideias)
- API REST para integrações
- Webhooks customizados por tenant
- Reports agendados por email
- Mobile app (React Native)
- Integração com CRMs (RD Station, HubSpot)
- Dashboards personalizados por segmento

---

## 📚 DOCUMENTAÇÃO ADICIONAL

- **[ARQUITETURA_DB.md](./ARQUITETURA_DB.md)** - Detalhes técnicos do banco de dados multi-tenant
- **[README.md](./README.md)** - Índice geral da documentação pública

---

**Desenvolvido por:** GeniAI
**Stack:** Python + PostgreSQL + Streamlit + OpenAI
**Arquitetura:** Multi-Tenant SaaS
**Licença:** Proprietária