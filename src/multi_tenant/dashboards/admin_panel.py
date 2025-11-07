"""
Painel Admin - Multi-Tenant
Fase 2 - GeniAI Analytics
Permite admins GeniAI selecionarem qual cliente visualizar
"""

import streamlit as st
from pathlib import Path
import sys
from sqlalchemy import text

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from multi_tenant.auth import get_database_engine, logout_user
from multi_tenant.auth.middleware import clear_session_state


# ============================================================================
# QUERIES DE DADOS
# ============================================================================

def get_active_tenants():
    """
    Retorna lista de tenants ativos (exceto GeniAI Admin)

    Returns:
        list[dict]: Lista de tenants com estatísticas
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            t.id,
            t.name,
            t.slug,
            t.inbox_ids,
            t.status,
            t.plan,
            t.created_at,
            (SELECT COUNT(*) FROM users WHERE tenant_id = t.id AND deleted_at IS NULL) AS user_count,
            (SELECT COUNT(*) FROM conversations_analytics WHERE tenant_id = t.id) AS conversation_count,
            (SELECT COUNT(DISTINCT contact_id) FROM conversations_analytics WHERE tenant_id = t.id AND contact_id IS NOT NULL) AS lead_count,
            (SELECT MAX(etl_updated_at) FROM conversations_analytics WHERE tenant_id = t.id) AS last_sync
        FROM tenants t
        WHERE t.deleted_at IS NULL
          AND t.id != 0  -- Excluir GeniAI Admin
        ORDER BY t.name
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        tenants = []

        for row in result:
            tenants.append({
                'id': row.id,
                'name': row.name,
                'slug': row.slug,
                'inbox_ids': row.inbox_ids,
                'status': row.status,
                'plan': row.plan,
                'created_at': row.created_at,
                'user_count': row.user_count or 0,
                'conversation_count': row.conversation_count or 0,
                'lead_count': row.lead_count or 0,
                'last_sync': row.last_sync,
            })

        return tenants


def get_global_metrics():
    """
    Retorna métricas agregadas de todos os clientes

    Returns:
        dict: Métricas globais
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            (SELECT COUNT(*) FROM tenants WHERE status = 'active' AND id != 0) AS active_tenants,
            (SELECT COUNT(*) FROM conversations_analytics) AS total_conversations,
            (SELECT COUNT(DISTINCT contact_id) FROM conversations_analytics WHERE contact_id IS NOT NULL) AS total_leads,
            (SELECT COUNT(*) FROM conversations_analytics WHERE status = 1) AS total_visits
        FROM tenants
        LIMIT 1
    """)

    with engine.connect() as conn:
        result = conn.execute(query).fetchone()

        if result:
            return {
                'active_tenants': result.active_tenants or 0,
                'total_conversations': result.total_conversations or 0,
                'total_leads': result.total_leads or 0,
                'total_visits': result.total_visits or 0,
            }

        return {
            'active_tenants': 0,
            'total_conversations': 0,
            'total_leads': 0,
            'total_visits': 0,
        }


# ============================================================================
# COMPONENTES UI
# ============================================================================

def render_global_metrics(metrics):
    """
    Renderiza métricas globais (overview)

    Args:
        metrics: Dict com métricas agregadas
    """
    st.subheader("📊 Overview Geral")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Clientes Ativos", metrics['active_tenants'])

    with col2:
        st.metric("Conversas Totais", f"{metrics['total_conversations']:,}".replace(',', '.'))

    with col3:
        st.metric("Leads Totais", f"{metrics['total_leads']:,}".replace(',', '.'))

    with col4:
        # Calcular taxa de conversão
        if metrics['total_conversations'] > 0:
            conversion_rate = (metrics['total_leads'] / metrics['total_conversations']) * 100
            st.metric("Taxa Conversão", f"{conversion_rate:.1f}%")
        else:
            st.metric("Taxa Conversão", "0%")


def render_tenant_card(tenant):
    """
    Renderiza card de um cliente

    Args:
        tenant: Dict com dados do tenant
    """
    with st.container():
        # Cabeçalho do card
        col1, col2 = st.columns([3, 1])

        with col1:
            # Nome e status
            status_emoji = "✅" if tenant['status'] == 'active' else "⚠️"
            st.markdown(f"### {status_emoji} {tenant['name']}")
            st.caption(f"Slug: `{tenant['slug']}` | Plano: **{tenant['plan']}**")

        with col2:
            # Botão Ver Dashboard
            if st.button("📊 Ver Dashboard", key=f"dash_{tenant['id']}", use_container_width=True):
                # Armazenar tenant selecionado
                st.session_state['selected_tenant_id'] = tenant['id']
                st.rerun()

        # Métricas do card
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Inboxes", len(tenant['inbox_ids']))

        with col2:
            st.metric("Usuários", tenant['user_count'])

        with col3:
            st.metric("Conversas", f"{tenant['conversation_count']:,}".replace(',', '.'))

        with col4:
            st.metric("Leads", f"{tenant['lead_count']:,}".replace(',', '.'))

        # Última sincronização
        if tenant['last_sync']:
            from datetime import datetime, timedelta

            # Converter UTC para SP
            last_sync_sp = tenant['last_sync'] - timedelta(hours=3)
            sync_str = last_sync_sp.strftime('%d/%m/%Y %H:%M')

            st.caption(f"📅 Última Sincronização: {sync_str}")
        else:
            st.caption("📅 Última Sincronização: Nenhuma")

        st.divider()


# ============================================================================
# SISTEMA DE AUDITORIA - FASE 5
# ============================================================================

def log_audit_action(user_id, tenant_id, action, entity_type, entity_id, old_value=None, new_value=None, ip_address=None):
    """
    Registra ação administrativa no log de auditoria

    Args:
        user_id: ID do usuário que realizou a ação
        tenant_id: ID do tenant afetado
        action: Tipo de ação (create_tenant, update_tenant, delete_tenant, etc)
        entity_type: Tipo de entidade (tenant, user, config, etc)
        entity_id: ID da entidade afetada
        old_value: Valor anterior (JSON)
        new_value: Novo valor (JSON)
        ip_address: IP do usuário
    """
    engine = get_database_engine()

    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO audit_logs
                (user_id, tenant_id, action, entity_type, entity_id, old_value, new_value, ip_address)
                VALUES (:user_id, :tenant_id, :action, :entity_type, :entity_id, :old_value, :new_value, :ip_address)
            """)

            import json

            conn.execute(query, {
                'user_id': user_id,
                'tenant_id': tenant_id,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'old_value': json.dumps(old_value) if old_value else None,
                'new_value': json.dumps(new_value) if new_value else None,
                'ip_address': ip_address
            })

    except Exception as e:
        # Não falhar se audit log der erro
        print(f"⚠️ Erro ao registrar audit log: {str(e)}")


def get_recent_audit_logs(limit=50):
    """
    Retorna logs de auditoria recentes

    Args:
        limit: Número máximo de logs

    Returns:
        list[dict]: Lista de logs
    """
    engine = get_database_engine()

    query = text("""
        SELECT
            a.id,
            a.action,
            a.entity_type,
            a.entity_id,
            a.created_at,
            u.full_name as user_name,
            u.email as user_email,
            t.name as tenant_name,
            a.old_value,
            a.new_value
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        LEFT JOIN tenants t ON a.tenant_id = t.id
        ORDER BY a.created_at DESC
        LIMIT :limit
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'limit': limit})

            logs = []
            for row in result:
                logs.append({
                    'id': row.id,
                    'action': row.action,
                    'entity_type': row.entity_type,
                    'entity_id': row.entity_id,
                    'created_at': row.created_at,
                    'user_name': row.user_name,
                    'user_email': row.user_email,
                    'tenant_name': row.tenant_name or 'N/A',
                    'old_value': row.old_value,
                    'new_value': row.new_value
                })

            return logs

    except Exception as e:
        st.error(f"❌ Erro ao buscar logs de auditoria: {str(e)}")
        return []


# ============================================================================
# CRUD DE TENANTS - FASE 5
# ============================================================================

def create_tenant(name, slug, inbox_ids, account_id, plan='basic'):
    """
    Cria novo tenant no banco

    Args:
        name: Nome do cliente
        slug: Slug único (URL-friendly)
        inbox_ids: Lista de inbox IDs
        account_id: ID da account no Chatwoot
        plan: Plano contratado

    Returns:
        int: ID do tenant criado ou None em caso de erro
    """
    # Usar johan_geniai (owner) para criar tenant (bypassa RLS)
    from sqlalchemy import create_engine
    owner_url = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
    engine = create_engine(owner_url)

    try:
        with engine.begin() as conn:
            # Verificar se slug já existe
            check_query = text("SELECT id FROM tenants WHERE slug = :slug AND deleted_at IS NULL")
            existing = conn.execute(check_query, {'slug': slug}).fetchone()

            if existing:
                st.error(f"❌ Erro: Slug '{slug}' já existe!")
                return None

            # Inserir tenant
            insert_query = text("""
                INSERT INTO tenants (name, slug, inbox_ids, account_id, status, plan)
                VALUES (:name, :slug, :inbox_ids, :account_id, 'active', :plan)
                RETURNING id
            """)

            result = conn.execute(insert_query, {
                'name': name,
                'slug': slug,
                'inbox_ids': inbox_ids,
                'account_id': account_id,
                'plan': plan
            })

            tenant_id = result.fetchone()[0]

            # Criar mapeamento de inboxes
            for inbox_id in inbox_ids:
                mapping_query = text("""
                    INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, is_active)
                    VALUES (:inbox_id, :tenant_id, TRUE)
                    ON CONFLICT (inbox_id) DO UPDATE SET tenant_id = :tenant_id, is_active = TRUE
                """)
                conn.execute(mapping_query, {'inbox_id': inbox_id, 'tenant_id': tenant_id})

            # Criar configurações padrão do tenant
            config_query = text("""
                INSERT INTO tenant_configs (tenant_id, primary_color, secondary_color)
                VALUES (:tenant_id, '#1E90FF', '#FF8C00')
            """)
            conn.execute(config_query, {'tenant_id': tenant_id})

        # Registrar no audit log (fora da transação)
        if 'user' in st.session_state:
            log_audit_action(
                user_id=st.session_state['user'].get('user_id'),
                tenant_id=tenant_id,
                action='create_tenant',
                entity_type='tenant',
                entity_id=tenant_id,
                new_value={'name': name, 'slug': slug, 'account_id': account_id, 'plan': plan, 'inbox_ids': inbox_ids}
            )

        return tenant_id

    except Exception as e:
        st.error(f"❌ Erro ao criar tenant: {str(e)}")
        return None


def update_tenant(tenant_id, name=None, slug=None, inbox_ids=None, status=None, plan=None):
    """
    Atualiza tenant existente

    Args:
        tenant_id: ID do tenant
        name: Novo nome (opcional)
        slug: Novo slug (opcional)
        inbox_ids: Novos inbox IDs (opcional)
        status: Novo status (opcional)
        plan: Novo plano (opcional)

    Returns:
        bool: True se sucesso, False se erro
    """
    # Usar johan_geniai (owner) para atualizar tenant (bypassa RLS)
    from sqlalchemy import create_engine
    owner_url = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
    engine = create_engine(owner_url)

    try:
        with engine.begin() as conn:
            updates = []
            params = {'tenant_id': tenant_id}

            if name:
                updates.append("name = :name")
                params['name'] = name

            if slug:
                updates.append("slug = :slug")
                params['slug'] = slug

            if inbox_ids is not None:
                updates.append("inbox_ids = :inbox_ids")
                params['inbox_ids'] = inbox_ids

            if status:
                updates.append("status = :status")
                params['status'] = status

            if plan:
                updates.append("plan = :plan")
                params['plan'] = plan

            if not updates:
                return True

            updates.append("updated_at = NOW()")

            query = text(f"""
                UPDATE tenants
                SET {', '.join(updates)}
                WHERE id = :tenant_id AND deleted_at IS NULL
            """)

            conn.execute(query, params)

            # Atualizar mapeamento de inboxes se fornecido
            if inbox_ids is not None:
                # Desativar todos os mapeamentos existentes
                deactivate_query = text("""
                    UPDATE inbox_tenant_mapping
                    SET is_active = FALSE
                    WHERE tenant_id = :tenant_id
                """)
                conn.execute(deactivate_query, {'tenant_id': tenant_id})

                # Criar/ativar novos mapeamentos
                for inbox_id in inbox_ids:
                    mapping_query = text("""
                        INSERT INTO inbox_tenant_mapping (inbox_id, tenant_id, is_active)
                        VALUES (:inbox_id, :tenant_id, TRUE)
                        ON CONFLICT (inbox_id) DO UPDATE SET tenant_id = :tenant_id, is_active = TRUE
                    """)
                    conn.execute(mapping_query, {'inbox_id': inbox_id, 'tenant_id': tenant_id})

            return True

    except Exception as e:
        st.error(f"❌ Erro ao atualizar tenant: {str(e)}")
        return False


def soft_delete_tenant(tenant_id):
    """
    Soft delete de tenant (marca como deletado)

    Args:
        tenant_id: ID do tenant

    Returns:
        bool: True se sucesso, False se erro
    """
    # Usar johan_geniai (owner) para deletar tenant (bypassa RLS)
    from sqlalchemy import create_engine
    owner_url = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
    engine = create_engine(owner_url)

    try:
        with engine.begin() as conn:
            # Adicionar sufixo ao slug para liberar o slug original
            query = text("""
                UPDATE tenants
                SET deleted_at = NOW(),
                    status = 'cancelled',
                    updated_at = NOW(),
                    slug = slug || '-deleted-' || EXTRACT(EPOCH FROM NOW())::TEXT
                WHERE id = :tenant_id AND deleted_at IS NULL
            """)

            conn.execute(query, {'tenant_id': tenant_id})

            # Desativar inboxes
            mapping_query = text("""
                UPDATE inbox_tenant_mapping
                SET is_active = FALSE
                WHERE tenant_id = :tenant_id
            """)
            conn.execute(mapping_query, {'tenant_id': tenant_id})

            return True

    except Exception as e:
        st.error(f"❌ Erro ao deletar tenant: {str(e)}")
        return False


def run_etl_for_tenant(tenant_id: int, tenant_name: str) -> bool:
    """
    Executa ETL para um tenant específico

    Args:
        tenant_id: ID do tenant
        tenant_name: Nome do tenant (para logs)

    Returns:
        bool: True se sucesso, False se erro
    """
    import subprocess
    import sys

    try:
        # Caminho do script ETL
        etl_script = "/home/tester/projetos/allpfit-analytics/src/multi_tenant/etl_v4/pipeline.py"

        # Executar ETL como subprocesso
        result = subprocess.run(
            [sys.executable, etl_script, "--tenant-id", str(tenant_id)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )

        if result.returncode == 0:
            return True
        else:
            st.error(f"❌ ETL falhou: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        st.error(f"❌ ETL excedeu o tempo limite de 5 minutos")
        return False
    except Exception as e:
        st.error(f"❌ Erro ao executar ETL: {str(e)}")
        return False


def get_available_chatwoot_accounts():
    """
    Busca accounts disponíveis no Chatwoot (banco remoto)

    Returns:
        list[dict]: Lista de accounts com inboxes
    """
    from sqlalchemy import create_engine

    # Conectar no banco remoto
    remote_url = "postgresql://hetzner_hyago_read:c1d46b41391f@178.156.206.184:5432/chatwoot"
    remote_engine = create_engine(remote_url)

    query = text("""
        SELECT
            account_id,
            account_name,
            inbox_id,
            inbox_name,
            COUNT(*) as conversation_count
        FROM vw_conversations_analytics_final
        WHERE account_id IS NOT NULL
        GROUP BY account_id, account_name, inbox_id, inbox_name
        ORDER BY account_id, inbox_id
    """)

    try:
        with remote_engine.connect() as conn:
            result = conn.execute(query)

            # Agrupar por account
            accounts = {}
            for row in result:
                acc_id = row.account_id

                if acc_id not in accounts:
                    accounts[acc_id] = {
                        'account_id': acc_id,
                        'account_name': row.account_name,
                        'inboxes': [],
                        'total_conversations': 0
                    }

                accounts[acc_id]['inboxes'].append({
                    'inbox_id': row.inbox_id,
                    'inbox_name': row.inbox_name,
                    'conversation_count': row.conversation_count
                })

                accounts[acc_id]['total_conversations'] += row.conversation_count

            return list(accounts.values())

    except Exception as e:
        st.error(f"❌ Erro ao buscar accounts do Chatwoot: {str(e)}")
        return []


def render_add_tenant_form():
    """
    Renderiza formulário para adicionar novo tenant
    """
    st.markdown("### ➕ Adicionar Novo Cliente")
    st.caption("Importar cliente do Chatwoot para o GeniAI Analytics")

    # Mostrar mensagem de sucesso se tenant foi criado
    if 'tenant_created' in st.session_state:
        tenant_info = st.session_state['tenant_created']

        # Container fixo com mensagem de sucesso
        success_container = st.container()
        with success_container:
            st.success(f"✅ Cliente **{tenant_info['name']}** criado com sucesso! (ID: {tenant_info['id']})")
            st.info(f"📊 {tenant_info['inbox_count']} inbox(es) mapeado(s): {tenant_info['inbox_ids']}")

            st.markdown("---")
            st.markdown("### 🚀 Sincronizar Dados (ETL)")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("▶️ Executar ETL Agora", type="primary", use_container_width=True):
                    with st.spinner(f"⏳ Executando ETL para {tenant_info['name']}... (pode levar alguns minutos)"):
                        success = run_etl_for_tenant(tenant_info['id'], tenant_info['name'])

                        if success:
                            st.success(f"✅ ETL concluído! Dados importados com sucesso!")
                            st.balloons()
                            import time
                            time.sleep(2)
                            del st.session_state['tenant_created']
                            st.rerun()
                        else:
                            st.error("❌ ETL falhou! Verifique os logs acima.")

            with col2:
                if st.button("⏭️ Pular ETL (executar depois)", use_container_width=True):
                    del st.session_state['tenant_created']
                    st.rerun()

            st.caption("💡 **Dica:** Você pode executar o ETL manualmente a qualquer momento na aba 'Editar Cliente'")

        st.markdown("---")

    # Buscar accounts disponíveis
    with st.spinner("🔄 Buscando clientes no Chatwoot..."):
        available_accounts = get_available_chatwoot_accounts()

    if not available_accounts:
        st.warning("⚠️ Nenhum account disponível no Chatwoot")
        return

    # Buscar tenants já cadastrados
    engine = get_database_engine()
    query = text("SELECT account_id FROM tenants WHERE deleted_at IS NULL AND account_id IS NOT NULL")
    with engine.connect() as conn:
        existing_account_ids = [row.account_id for row in conn.execute(query)]

    # Filtrar apenas accounts não cadastrados
    new_accounts = [acc for acc in available_accounts if acc['account_id'] not in existing_account_ids]

    if not new_accounts:
        st.info("✅ Todos os clientes do Chatwoot já estão cadastrados!")
        return

    # Mostrar accounts disponíveis
    st.markdown(f"**{len(new_accounts)} cliente(s) disponível(is) para importar:**")

    for acc in new_accounts:
        with st.expander(f"📦 {acc['account_name']} (Account ID: {acc['account_id']}) - {acc['total_conversations']} conversas"):
            st.markdown(f"**Inboxes ({len(acc['inboxes'])}):**")

            for inbox in acc['inboxes']:
                st.markdown(f"- `{inbox['inbox_id']}` - {inbox['inbox_name']} ({inbox['conversation_count']} conversas)")

    st.divider()

    # Selecionar account (FORA do form para atualizar dinamicamente)
    st.markdown("#### 📝 Dados do Novo Cliente")

    account_options = {f"{acc['account_name']} (ID: {acc['account_id']})": acc for acc in new_accounts}
    selected_account_name = st.selectbox(
        "Selecione o Cliente",
        options=list(account_options.keys()),
        help="Cliente do Chatwoot para importar"
    )

    selected_account = account_options[selected_account_name]

    # Formulário de criação
    with st.form("add_tenant_form"):

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Nome do Cliente",
                value=selected_account['account_name'],
                help="Nome que aparecerá no sistema",
                key=f"name_{selected_account['account_id']}"  # Key dinâmica para atualizar
            )

        with col2:
            # Gerar slug automático (sem acentuação)
            import unicodedata

            # Remover acentos e normalizar
            normalized = unicodedata.normalize('NFKD', selected_account['account_name'])
            default_slug = ''.join([c for c in normalized if not unicodedata.combining(c)])

            default_slug = default_slug.lower() \
                .replace(' ', '-') \
                .replace('cdt', 'cdt-') \
                .replace('--', '-')

            slug = st.text_input(
                "Slug (URL-friendly)",
                value=default_slug,
                help="Usado para identificação única (ex: cdt-mossoro)",
                key=f"slug_{selected_account['account_id']}"  # Key dinâmica para atualizar
            )

        # Inboxes (pré-selecionados)
        st.markdown("**Inboxes a importar:**")
        inbox_ids = [inbox['inbox_id'] for inbox in selected_account['inboxes']]

        for inbox in selected_account['inboxes']:
            st.markdown(f"✅ `{inbox['inbox_id']}` - {inbox['inbox_name']} ({inbox['conversation_count']} conversas)")

        # Plano
        plan = st.selectbox(
            "Plano",
            options=['basic', 'pro', 'enterprise'],
            index=1,  # Default: pro
            help="Plano contratado pelo cliente"
        )

        # Botão submit
        submitted = st.form_submit_button("🚀 Criar Cliente", use_container_width=True)

        if submitted:
            if not name or not slug:
                st.error("❌ Preencha todos os campos obrigatórios!")
                return

            with st.spinner("⏳ Criando tenant..."):
                tenant_id = create_tenant(
                    name=name,
                    slug=slug,
                    inbox_ids=inbox_ids,
                    account_id=selected_account['account_id'],
                    plan=plan
                )

                if tenant_id:
                    # Salvar informações na session_state para mostrar depois
                    st.session_state['tenant_created'] = {
                        'name': name,
                        'id': tenant_id,
                        'inbox_count': len(inbox_ids),
                        'inbox_ids': inbox_ids
                    }
                    st.rerun()


def render_edit_tenant_interface(tenants):
    """
    Renderiza interface para editar tenants existentes
    """
    st.markdown("### ✏️ Editar Cliente Existente")

    if not tenants:
        st.info("ℹ️ Nenhum cliente cadastrado ainda.")
        return

    # Selecionar tenant
    tenant_options = {f"{t['name']} (ID: {t['id']})": t for t in tenants}
    selected_tenant_name = st.selectbox(
        "Selecione o Cliente",
        options=list(tenant_options.keys()),
        key="edit_tenant_select"
    )

    selected_tenant = tenant_options[selected_tenant_name]

    # Mostrar informações atuais
    st.markdown("#### 📋 Informações Atuais")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Nome", selected_tenant['name'])
    with col2:
        st.metric("Slug", selected_tenant['slug'])
    with col3:
        st.metric("Status", selected_tenant['status'])

    st.caption(f"Inboxes: {selected_tenant['inbox_ids']}")
    st.caption(f"Plano: {selected_tenant['plan']}")

    st.divider()

    # Formulário de edição
    with st.form("edit_tenant_form"):
        st.markdown("#### 🔧 Atualizar Dados")

        col1, col2 = st.columns(2)

        with col1:
            new_name = st.text_input("Novo Nome", value=selected_tenant['name'])
            new_status = st.selectbox(
                "Status",
                options=['active', 'suspended', 'cancelled'],
                index=['active', 'suspended', 'cancelled'].index(selected_tenant['status'])
            )

        with col2:
            new_slug = st.text_input("Novo Slug", value=selected_tenant['slug'])
            new_plan = st.selectbox(
                "Plano",
                options=['basic', 'pro', 'enterprise'],
                index=['basic', 'pro', 'enterprise'].index(selected_tenant['plan'])
            )

        # Inboxes (editar manualmente - JSON)
        new_inbox_ids_str = st.text_input(
            "Inbox IDs (separados por vírgula)",
            value=','.join(map(str, selected_tenant['inbox_ids'])),
            help="Ex: 1,2,61,64,67"
        )

        col1, col2 = st.columns(2)

        with col1:
            update_button = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)

        with col2:
            delete_button = st.form_submit_button("🗑️ Deletar Cliente", use_container_width=True, type="secondary")

        if update_button:
            # Parsear inbox IDs
            try:
                new_inbox_ids = [int(x.strip()) for x in new_inbox_ids_str.split(',') if x.strip()]
            except ValueError:
                st.error("❌ Formato inválido para Inbox IDs!")
                return

            with st.spinner("⏳ Atualizando tenant..."):
                success = update_tenant(
                    tenant_id=selected_tenant['id'],
                    name=new_name,
                    slug=new_slug,
                    inbox_ids=new_inbox_ids,
                    status=new_status,
                    plan=new_plan
                )

                if success:
                    st.success("✅ Cliente atualizado com sucesso!")
                    import time
                    time.sleep(2)
                    st.rerun()

        if delete_button:
            st.warning(f"⚠️ Tem certeza que deseja deletar '{selected_tenant['name']}'?")

            if st.checkbox("Sim, tenho certeza", key="confirm_delete"):
                with st.spinner("⏳ Deletando tenant..."):
                    success = soft_delete_tenant(selected_tenant['id'])

                    if success:
                        st.success(f"✅ Cliente '{selected_tenant['name']}' deletado!")
                        import time
                        time.sleep(2)
                        st.rerun()


def render_advanced_metrics(tenants):
    """
    Renderiza métricas avançadas e comparativas
    """
    st.markdown("### 📊 Métricas Avançadas")

    if not tenants:
        st.info("ℹ️ Nenhum cliente cadastrado ainda.")
        return

    # Criar DataFrame para análise
    import pandas as pd

    df = pd.DataFrame([{
        'Cliente': t['name'],
        'Conversas': t['conversation_count'],
        'Leads': t['lead_count'],
        'Inboxes': len(t['inbox_ids']),
        'Usuários': t['user_count'],
        'Status': t['status'],
        'Plano': t['plan']
    } for t in tenants])

    # Adicionar taxa de conversão
    df['Taxa Conversão (%)'] = (df['Leads'] / df['Conversas'] * 100).fillna(0).round(1)

    # Gráfico de conversas por cliente
    st.markdown("#### 📈 Conversas por Cliente")
    st.bar_chart(df.set_index('Cliente')['Conversas'])

    st.divider()

    # Tabela comparativa
    st.markdown("#### 📋 Comparativo de Performance")
    st.dataframe(
        df.sort_values('Conversas', ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Estatísticas gerais
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Média de Conversas/Cliente", f"{df['Conversas'].mean():.0f}")

    with col2:
        st.metric("Média de Leads/Cliente", f"{df['Leads'].mean():.0f}")

    with col3:
        st.metric("Taxa Conversão Média", f"{df['Taxa Conversão (%)'].mean():.1f}%")


# ============================================================================
# TELA PRINCIPAL
# ============================================================================

def show_admin_panel(session):
    """
    Painel de administração GeniAI

    Permite:
    - Ver overview geral (métricas agregadas)
    - Listar todos os clientes
    - Selecionar um cliente para visualizar dashboard

    Args:
        session: Dados da sessão (user_id, tenant_id, role, etc.)
    """

    # Header
    col1, col2 = st.columns([5, 1])

    with col1:
        st.title("🎛️ Painel Admin GeniAI")
        st.caption(f"Bem-vindo, {session['full_name']} | {session['role']}")

    with col2:
        if st.button("🚪 Sair", use_container_width=True):
            engine = get_database_engine()
            logout_user(engine, session['session_id'])
            clear_session_state()
            st.rerun()

    st.divider()

    # Carregar dados
    with st.spinner("🔄 Carregando dados..."):
        metrics = get_global_metrics()
        tenants = get_active_tenants()

    # Overview Geral
    render_global_metrics(metrics)

    st.divider()

    # Lista de Clientes
    st.subheader("👥 Clientes")

    if not tenants:
        st.info("ℹ️ Nenhum cliente cadastrado ainda.")
        st.markdown("""
            **Próximos passos:**
            - Adicionar clientes na Fase 5 (Dashboard Admin completo)
            - Por enquanto, apenas visualização dos clientes existentes
        """)
    else:
        # Renderizar cards dos clientes
        for tenant in tenants:
            render_tenant_card(tenant)

    st.divider()

    # Gerenciamento de Clientes (Fase 5)
    st.subheader("⚙️ Gerenciamento de Clientes")

    tab1, tab2, tab3 = st.tabs(["➕ Adicionar Cliente", "✏️ Editar Cliente", "📊 Métricas Avançadas"])

    with tab1:
        render_add_tenant_form()

    with tab2:
        render_edit_tenant_interface(tenants)

    with tab3:
        render_advanced_metrics(tenants)


# ============================================================================
# TESTES LOCAIS
# ============================================================================

if __name__ == "__main__":
    # Configurar página
    st.set_page_config(
        page_title="Painel Admin - GeniAI",
        page_icon="🎛️",
        layout="wide"
    )

    # Aplicar CSS do config.py
    from app.config import apply_custom_css
    apply_custom_css()

    # Simular sessão de admin (para teste local)
    if 'user' not in st.session_state:
        st.session_state['user'] = {
            'user_id': 1,
            'tenant_id': 0,
            'full_name': 'Administrador GeniAI',
            'role': 'super_admin',
            'session_id': 'test-session-id',
        }

    session = st.session_state['user']
    show_admin_panel(session)
