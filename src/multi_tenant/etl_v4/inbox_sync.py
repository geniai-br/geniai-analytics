"""
Inbox Sync - Detecção Automática de Novos Inboxes
==================================================

Detecta automaticamente novos inboxes no Chatwoot e os adiciona
ao tenant correspondente baseado no account_id.

Funcionalidades:
    - Buscar inboxes ativos no remoto por account_id
    - Comparar com inboxes cadastrados no local
    - Adicionar automaticamente novos inboxes encontrados
    - Logging detalhado de todas as operações

Autor: Isaac (via Claude Code)
Data: 2025-11-21
"""

import logging
from typing import List, Dict, Set
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class InboxSyncManager:
    """Gerencia sincronização automática de inboxes entre remoto e local"""

    def __init__(self, local_engine: Engine, remote_engine: Engine):
        """
        Inicializa o gerenciador de sincronização.

        Args:
            local_engine: Engine do banco local (geniai_analytics)
            remote_engine: Engine do banco remoto (chatwoot)
        """
        self.local_engine = local_engine
        self.remote_engine = remote_engine
        logger.info("InboxSyncManager inicializado")

    def get_remote_inboxes_by_account(self, account_id: int) -> List[Dict]:
        """
        Busca todos os inboxes ativos de um account_id no banco remoto.

        Args:
            account_id: ID da conta no Chatwoot

        Returns:
            Lista de dicts com informações dos inboxes:
            [
                {
                    'inbox_id': 94,
                    'inbox_name': 'cdtmossorodial01',
                    'channel_type': 'Channel::Whatsapp',
                    'account_id': 1
                },
                ...
            ]
        """
        query = text("""
            SELECT DISTINCT
                inbox_id,
                inbox_name,
                inbox_channel_type as channel_type,
                account_id
            FROM vw_conversations_analytics_final
            WHERE account_id = :account_id
            ORDER BY inbox_id
        """)

        with self.remote_engine.connect() as conn:
            result = conn.execute(query, {'account_id': account_id})
            inboxes = [
                {
                    'inbox_id': row[0],
                    'inbox_name': row[1],
                    'channel_type': row[2],
                    'account_id': row[3]
                }
                for row in result
            ]

        logger.info(f"Account {account_id}: {len(inboxes)} inboxes encontrados no remoto")
        return inboxes

    def get_local_tenant_inboxes(self, tenant_id: int) -> Set[int]:
        """
        Busca inbox_ids cadastrados para um tenant no banco local.

        Args:
            tenant_id: ID do tenant

        Returns:
            Set de inbox_ids
        """
        query = text("""
            SELECT inbox_ids
            FROM tenants
            WHERE id = :tenant_id
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id})
            row = result.fetchone()

            if not row or not row[0]:
                logger.warning(f"Tenant {tenant_id}: Nenhum inbox cadastrado")
                return set()

            inbox_ids = set(row[0])
            logger.info(f"Tenant {tenant_id}: {len(inbox_ids)} inboxes cadastrados localmente")
            return inbox_ids

    def get_tenant_account_id(self, tenant_id: int) -> int:
        """
        Busca o account_id de um tenant.

        Args:
            tenant_id: ID do tenant

        Returns:
            account_id do tenant

        Raises:
            ValueError: Se tenant não possui account_id configurado
        """
        query = text("""
            SELECT account_id
            FROM tenants
            WHERE id = :tenant_id
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id})
            row = result.fetchone()

            if not row or not row[0]:
                raise ValueError(
                    f"Tenant {tenant_id} não possui account_id configurado. "
                    "É necessário configurar account_id na tabela tenants."
                )

            account_id = row[0]
            logger.info(f"Tenant {tenant_id}: account_id = {account_id}")
            return account_id

    def add_inboxes_to_tenant(self, tenant_id: int, new_inbox_ids: List[int]) -> bool:
        """
        Adiciona novos inbox_ids a um tenant.

        Args:
            tenant_id: ID do tenant
            new_inbox_ids: Lista de inbox_ids para adicionar

        Returns:
            True se adicionou com sucesso, False caso contrário
        """
        if not new_inbox_ids:
            return True

        # Usar loop simples para adicionar um por um (mais seguro)
        try:
            with self.local_engine.begin() as conn:
                for inbox_id in new_inbox_ids:
                    conn.execute(
                        text("""
                            UPDATE tenants
                            SET inbox_ids = array_append(inbox_ids, :inbox_id),
                                updated_at = NOW()
                            WHERE id = :tenant_id
                              AND NOT (:inbox_id = ANY(inbox_ids))
                        """),
                        {'tenant_id': tenant_id, 'inbox_id': inbox_id}
                    )

                # Buscar inbox_ids atualizados
                result = conn.execute(
                    text("SELECT inbox_ids FROM tenants WHERE id = :tenant_id"),
                    {'tenant_id': tenant_id}
                )
                updated_inbox_ids = result.fetchone()[0]

            logger.info(
                f"✅ Tenant {tenant_id}: {len(new_inbox_ids)} novos inboxes adicionados. "
                f"Total agora: {len(updated_inbox_ids)}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao adicionar inboxes ao tenant {tenant_id}: {e}")
            return False

    def sync_tenant_inboxes(self, tenant_id: int, tenant_name: str = None) -> Dict:
        """
        Sincroniza inboxes de um tenant: detecta novos e adiciona automaticamente.

        Args:
            tenant_id: ID do tenant
            tenant_name: Nome do tenant (opcional, para logging)

        Returns:
            Dict com estatísticas da sincronização:
            {
                'tenant_id': 14,
                'tenant_name': 'CDT Mossoró',
                'account_id': 1,
                'inboxes_before': [21],
                'inboxes_remote': [21, 94],
                'new_inboxes': [94],
                'inboxes_after': [21, 94],
                'synced': True
            }
        """
        tenant_name = tenant_name or f"Tenant {tenant_id}"
        logger.info(f"🔄 Sincronizando inboxes para: {tenant_name} (ID: {tenant_id})")

        result = {
            'tenant_id': tenant_id,
            'tenant_name': tenant_name,
            'account_id': None,
            'inboxes_before': [],
            'inboxes_remote': [],
            'new_inboxes': [],
            'inboxes_after': [],
            'synced': False
        }

        try:
            # 1. Buscar account_id do tenant
            account_id = self.get_tenant_account_id(tenant_id)
            result['account_id'] = account_id

            # 2. Buscar inboxes locais (antes)
            local_inboxes = self.get_local_tenant_inboxes(tenant_id)
            result['inboxes_before'] = sorted(list(local_inboxes))

            # 3. Buscar inboxes no remoto
            remote_inboxes_data = self.get_remote_inboxes_by_account(account_id)
            remote_inbox_ids = {inbox['inbox_id'] for inbox in remote_inboxes_data}
            result['inboxes_remote'] = sorted(list(remote_inbox_ids))

            # 4. Detectar novos inboxes
            new_inbox_ids = remote_inbox_ids - local_inboxes
            result['new_inboxes'] = sorted(list(new_inbox_ids))

            # 5. Se encontrou novos, adicionar e logar detalhes
            if new_inbox_ids:
                logger.warning(
                    f"🆕 {len(new_inbox_ids)} novo(s) inbox(es) detectado(s) "
                    f"para {tenant_name}:"
                )

                # Logar detalhes de cada inbox novo
                for inbox_data in remote_inboxes_data:
                    if inbox_data['inbox_id'] in new_inbox_ids:
                        logger.warning(
                            f"   📥 Inbox {inbox_data['inbox_id']}: "
                            f"{inbox_data['inbox_name']} "
                            f"({inbox_data['channel_type']})"
                        )

                # Adicionar automaticamente
                success = self.add_inboxes_to_tenant(tenant_id, sorted(list(new_inbox_ids)))

                if success:
                    # Buscar inbox_ids atualizados
                    updated_inboxes = self.get_local_tenant_inboxes(tenant_id)
                    result['inboxes_after'] = sorted(list(updated_inboxes))
                    result['synced'] = True

                    logger.info(
                        f"✅ {tenant_name}: Sincronização concluída. "
                        f"Inboxes: {result['inboxes_before']} → {result['inboxes_after']}"
                    )
                else:
                    result['inboxes_after'] = result['inboxes_before']
                    logger.error(f"❌ {tenant_name}: Falha ao adicionar novos inboxes")

            else:
                # Nenhum inbox novo
                result['inboxes_after'] = result['inboxes_before']
                result['synced'] = True
                logger.info(f"✅ {tenant_name}: Nenhum inbox novo detectado")

        except ValueError as e:
            logger.error(f"❌ {tenant_name}: {e}")
            result['synced'] = False

        except Exception as e:
            logger.error(f"❌ {tenant_name}: Erro na sincronização: {e}")
            result['synced'] = False

        return result