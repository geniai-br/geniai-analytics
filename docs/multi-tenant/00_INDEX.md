# 📚 ÍNDICE - DOCUMENTAÇÃO MULTI-TENANT

> **Projeto:** GeniAI Multi-Tenant SaaS Platform
> **Última Atualização:** 2025-11-05
> **Status:** 🟢 Fase 1 Completa | 📋 Fase 2 Planejada

---

## 📂 DOCUMENTOS DO PROJETO

### 🎯 Planejamento e Cronograma

#### [00_CRONOGRAMA_MASTER.md](./00_CRONOGRAMA_MASTER.md)
**O que é:** Cronograma completo do projeto (6 fases)
**Quando usar:** Para entender o escopo geral e timelines
**Destaques:**
- ✅ Fase 0: Setup (completa)
- ✅ Fase 1: Banco de Dados (completa)
- 📋 Fase 2: Autenticação & UX (planejada - **NOVA ESTRATÉGIA**)
- 🔜 Fases 3-6: ETL, Dashboards, Deploy

---

### 🗄️ Banco de Dados

#### [DB_DOCUMENTATION.md](./DB_DOCUMENTATION.md) ⭐ **NOVO**
**O que é:** Documentação completa do banco `geniai_analytics`
**Quando usar:** Para consultar estrutura, queries, credenciais
**Destaques:**
- 🔐 Credenciais de acesso
- 📊 9 tabelas documentadas
- 👥 Usuários e tenants cadastrados
- 🔒 Explicação de RLS (Row-Level Security)
- 📖 Queries úteis
- 🧪 Dados de teste

**Acesso Rápido:**
```bash
# Conectar ao banco
PGPASSWORD='AllpFit2024@Analytics' psql -U isaac -h localhost -d geniai_analytics

# Ver tenants
SELECT id, name, slug FROM tenants;

# Ver usuários
SELECT email, role FROM users ORDER BY tenant_id;
```

---

#### [01_ARQUITETURA_DB.md](./01_ARQUITETURA_DB.md)
**O que é:** Design detalhado da arquitetura do banco
**Quando usar:** Para entender decisões arquiteturais (por que single database, RLS, etc.)

---

### 🎨 Design e UX

#### [02_UX_FLOW.md](./02_UX_FLOW.md) ⭐ **NOVO**
**O que é:** Fluxo completo de UX por role (admin vs cliente)
**Quando usar:** Para implementar interfaces e navegação
**Destaques:**
- 👥 4 personas definidas
- 🗺️ Fluxos detalhados por role
- 🖼️ Wireframes ASCII
- 🔧 Componentes reutilizáveis
- 💬 Estados e interações

**Fluxos principais:**
1. **Admin GeniAI:** Login → Painel Admin → Selecionar Cliente → Dashboard
2. **Cliente:** Login → Dashboard Direto (seus dados)

---

### 📊 Progresso e Status

#### [PROGRESS.md](./PROGRESS.md)
**O que é:** Log de progresso do projeto (atualizado frequentemente)
**Quando usar:** Para ver o que já foi feito e próximos passos
**Destaques:**
- ✅ Fase 1: 100% completa (9 tabelas, RLS, 555 conversas migradas)
- 📋 Fase 2: Revertida e replanejada (2025-11-05)
- 📈 Progresso visual (barras de status)

---

#### [README.md](./README.md)
**O que é:** Guia de introdução ao projeto multi-tenant
**Quando usar:** Primeiro contato com o projeto

---

## 🚀 QUICK START - FASE 2

### 1️⃣ Contexto Atual
- ✅ Banco `geniai_analytics` criado e populado
- ✅ 2 tenants: GeniAI Admin (0) e AllpFit (1)
- ✅ 4 usuários com senhas hasheadas (bcrypt)
- ✅ RLS configurado e testado

### 2️⃣ O que Implementar Agora
Confira: [00_CRONOGRAMA_MASTER.md - Fase 2](./00_CRONOGRAMA_MASTER.md#fase-2)

**Resumo:**
1. **auth/auth.py** - Autenticação + sessões
2. **auth/middleware.py** - Proteção de rotas + RLS
3. **dashboards/login_page.py** - Tela de login (tema dark)
4. **dashboards/admin_panel.py** - Painel admin (seleção de clientes)
5. **dashboards/client_dashboard.py** - Dashboard do cliente
6. **dashboards/app.py** - Router principal

### 3️⃣ Design Base
Copiar tema dark da **porta 8503**: [src/app/config.py](../../src/app/config.py)

Cores:
- Azul: `#1E90FF`
- Laranja: `#FF8C00`
- Background: `#0E1117`
- Cards: `#1A1F2E`

---

## 📖 COMO USAR ESTA DOCUMENTAÇÃO

### Para Desenvolvimento
1. **Antes de codificar:** Leia o cronograma da fase atual
2. **Durante desenvolvimento:** Consulte DB_DOCUMENTATION.md e UX_FLOW.md
3. **Ao implementar UI:** Siga wireframes do UX_FLOW.md
4. **Queries SQL:** Use exemplos do DB_DOCUMENTATION.md

### Para Revisão
1. Verificar PROGRESS.md para ver status
2. Comparar código implementado com cronograma
3. Validar UX contra fluxos documentados

### Para Novo Desenvolvedor
**Ordem de leitura recomendada:**
1. README.md (contexto geral)
2. DB_DOCUMENTATION.md (entender banco)
3. 00_CRONOGRAMA_MASTER.md (visão geral do projeto)
4. 02_UX_FLOW.md (entender experiência do usuário)
5. PROGRESS.md (ver o que já foi feito)

---

## 🔥 DESTAQUES DA NOVA ESTRATÉGIA (Fase 2)

### ✅ O que mudou?
**Antes:** Tentativa de implementação genérica
**Agora:** Foco em UX diferenciado por role

### 🎯 Principais Decisões

1. **Admin GeniAI tem painel de seleção**
   - Vê overview geral
   - Seleciona cliente para ver dashboard
   - Pode voltar ao painel

2. **Cliente vai direto para dashboard**
   - Sem painel intermediário
   - Vê apenas seus dados
   - Logo/cores personalizadas

3. **Código modular e reutilizável**
   - Componentes compartilhados (header, KPIs)
   - Funções helpers para queries
   - Base copiada da porta 8503

4. **Segurança via RLS**
   - Middleware configura `app.current_tenant_id`
   - PostgreSQL filtra automaticamente
   - Admin usa policy especial (vê tudo)

---

## 📞 REFERÊNCIAS EXTERNAS

### Banco de Dados
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)

### Streamlit
- [Streamlit Docs](https://docs.streamlit.io/)
- [Session State Guide](https://docs.streamlit.io/library/api-reference/session-state)

### Segurança
- [bcrypt Documentation](https://github.com/pyca/bcrypt/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

## 📁 ESTRUTURA DE PASTAS

```
docs/multi-tenant/
├── 00_INDEX.md                  # ← Você está aqui
├── 00_CRONOGRAMA_MASTER.md      # Cronograma 6 fases
├── 01_ARQUITETURA_DB.md         # Design do banco
├── 02_UX_FLOW.md                # Fluxos de UX
├── DB_DOCUMENTATION.md          # Docs do banco (completo)
├── PROGRESS.md                  # Log de progresso
└── README.md                    # Introdução

sql/multi_tenant/
├── 01_create_database.sql       # Scripts SQL
├── 02_create_schema.sql
├── ...
└── README.md

src/multi_tenant/
├── auth/                        # (Fase 2 - a implementar)
│   ├── auth.py
│   └── middleware.py
└── dashboards/                  # (Fase 2 - a implementar)
    ├── app.py
    ├── login_page.py
    ├── admin_panel.py
    └── client_dashboard.py
```

---

## ✅ CHECKLIST RÁPIDO

### Antes de Iniciar Fase 2
- [x] Banco `geniai_analytics` criado
- [x] Usuários cadastrados (admin@geniai, isaac@allpfit, etc.)
- [x] RLS testado e funcionando
- [x] Documentação lida (este índice)
- [x] Design da porta 8503 analisado
- [ ] Ambiente virtual ativo
- [ ] bcrypt instalado (`pip install bcrypt`)

### Durante Implementação
- [ ] Seguir estrutura de arquivos do cronograma
- [ ] Testar cada módulo antes de prosseguir
- [ ] Commitar frequentemente
- [ ] Atualizar PROGRESS.md

### Ao Finalizar Fase 2
- [ ] Login funcional
- [ ] Admin vê painel de clientes
- [ ] Cliente vê dashboard direto
- [ ] RLS configurado automaticamente
- [ ] Logout funcionando
- [ ] Documentar problemas/soluções encontrados

---

## 🆘 TROUBLESHOOTING

### Problema: "Não consigo conectar no banco"
**Solução:** Ver [DB_DOCUMENTATION.md - Credenciais](./DB_DOCUMENTATION.md#credenciais-de-acesso)

### Problema: "RLS não está filtrando"
**Solução:** Verificar se `app.current_tenant_id` está configurado (ver middleware)

### Problema: "Senha não valida"
**Solução:** Verificar hash no banco (`SELECT LEFT(password_hash, 20) FROM users`)

### Problema: "Sessão expira muito rápido"
**Solução:** Ajustar `expires_hours` em `create_session()` (padrão: 24h)

---

**Mantido por:** Isaac (via Claude Code)
**Última atualização:** 2025-11-05
**Versão:** 1.0