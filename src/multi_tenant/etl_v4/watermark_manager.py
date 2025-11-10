"""
Watermark Manager - ETL V4 Multi-Tenant
=======================================

Responsável por gerenciar watermarks (marcas d'água) e controle de execuções do ETL.

Funcionalidades:
    - Get/Set watermark por tenant
    - Criar/Atualizar registros de execução ETL
    - Advisory locks (evitar execução simultânea)
    - Logging estruturado

Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WatermarkManager:
    """Gerencia watermarks e controle de execuções do ETL"""

    def __init__(self, local_engine: Engine):
        """
        Inicializa o manager.

        Args:
            local_engine: Engine SQLAlchemy conectada ao banco local
        """
        self.local_engine = local_engine
        self.active_locks = {}  # {tenant_id: lock_id}
        logger.info("WatermarkManager inicializado")

    def get_last_watermark(self, tenant_id: int) -> Optional[datetime]:
        """
        Retorna o último watermark (última extração bem-sucedida) para um tenant.

        Args:
            tenant_id: ID do tenant

        Returns:
            Datetime do último watermark, ou None se nunca executou

        Example:
            >>> manager = WatermarkManager(engine)
            >>> watermark = manager.get_last_watermark(1)
            >>> print(f"Última extração: {watermark}")
        """
        query = text("""
            SELECT watermark_end
            FROM etl_control
            WHERE tenant_id = :tenant_id
              AND status = 'success'
              AND watermark_end IS NOT NULL
            ORDER BY watermark_end DESC
            LIMIT 1
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id}).fetchone()

            if result and result[0]:
                watermark = result[0]
                logger.info(f"Tenant {tenant_id}: último watermark = {watermark}")
                return watermark
            else:
                logger.info(f"Tenant {tenant_id}: nenhum watermark encontrado (full sync necessário)")
                return None

    def create_execution(
        self,
        tenant_id: int,
        load_type: str = 'incremental',
        watermark_start: Optional[datetime] = None,
        watermark_end: Optional[datetime] = None,
        triggered_by: str = 'manual'
    ) -> int:
        """
        Cria um novo registro de execução do ETL.

        Args:
            tenant_id: ID do tenant
            load_type: Tipo de carga ('incremental' ou 'full')
            watermark_start: Data inicial da extração
            watermark_end: Data final da extração (default=NOW)
            triggered_by: Quem disparou a execução

        Returns:
            ID da execução criada

        Example:
            >>> manager = WatermarkManager(engine)
            >>> execution_id = manager.create_execution(1, 'incremental')
            >>> print(f"Execução {execution_id} iniciada")
        """
        query = text("""
            INSERT INTO etl_control (
                tenant_id,
                started_at,
                load_type,
                is_full_load,
                status,
                triggered_by,
                watermark_start,
                watermark_end,
                source_system,
                target_table,
                etl_version
            ) VALUES (
                :tenant_id,
                NOW(),
                :load_type,
                :is_full_load,
                'running',
                :triggered_by,
                :watermark_start,
                :watermark_end,
                'chatwoot',
                'conversations_analytics',
                'v4'
            )
            RETURNING id
        """)

        is_full_load = (load_type == 'full' or watermark_start is None)

        with self.local_engine.begin() as conn:
            result = conn.execute(
                query,
                {
                    'tenant_id': tenant_id,
                    'load_type': load_type,
                    'is_full_load': is_full_load,
                    'triggered_by': triggered_by,
                    'watermark_start': watermark_start,
                    'watermark_end': watermark_end
                }
            )
            execution_id = result.fetchone()[0]

        logger.info(
            f"Execução {execution_id} criada: tenant={tenant_id}, "
            f"type={load_type}, watermark_start={watermark_start}"
        )

        return execution_id

    def update_execution(
        self,
        execution_id: int,
        status: str,
        stats: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict] = None
    ):
        """
        Atualiza um registro de execução do ETL.

        Args:
            execution_id: ID da execução
            status: Status da execução ('running', 'success', 'error')
            stats: Estatísticas da execução (records_extracted, inserted, updated)
            error_message: Mensagem de erro (se status='error')
            error_details: Detalhes do erro em JSON

        Example:
            >>> manager = WatermarkManager(engine)
            >>> manager.update_execution(
            ...     execution_id=1,
            ...     status='success',
            ...     stats={'records_extracted': 100, 'records_inserted': 80, 'records_updated': 20}
            ... )
        """
        if stats is None:
            stats = {}

        query = text("""
            UPDATE etl_control
            SET
                finished_at = NOW(),
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER,
                status = :status,
                records_extracted = :records_extracted,
                records_inserted = :records_inserted,
                records_updated = :records_updated,
                records_failed = :records_failed,
                error_message = :error_message,
                error_details = :error_details,
                openai_api_calls = :openai_api_calls,
                openai_total_tokens = :openai_total_tokens,
                openai_cost_brl = :openai_cost_brl
            WHERE id = :execution_id
        """)

        with self.local_engine.begin() as conn:
            conn.execute(
                query,
                {
                    'execution_id': execution_id,
                    'status': status,
                    'records_extracted': stats.get('records_extracted', 0),
                    'records_inserted': stats.get('records_inserted', 0),
                    'records_updated': stats.get('records_updated', 0),
                    'records_failed': stats.get('records_failed', 0),
                    'error_message': error_message,
                    'error_details': error_details,
                    'openai_api_calls': stats.get('openai_api_calls', 0),
                    'openai_total_tokens': stats.get('openai_total_tokens', 0),
                    'openai_cost_brl': stats.get('openai_cost_brl', 0.0)
                }
            )

        log_msg = (
            f"Execução {execution_id} atualizada: status={status}, "
            f"extracted={stats.get('records_extracted', 0)}, "
            f"inserted={stats.get('records_inserted', 0)}, "
            f"updated={stats.get('records_updated', 0)}"
        )

        # Adicionar info OpenAI ao log se houver
        if stats.get('openai_api_calls', 0) > 0:
            log_msg += (
                f", openai_calls={stats.get('openai_api_calls', 0)}, "
                f"openai_tokens={stats.get('openai_total_tokens', 0)}, "
                f"openai_cost=R$ {stats.get('openai_cost_brl', 0.0):.4f}"
            )

        logger.info(log_msg)

    def acquire_lock(self, tenant_id: int, timeout_seconds: int = 0) -> bool:
        """
        Tenta adquirir um advisory lock para o tenant (evita execução simultânea).

        Args:
            tenant_id: ID do tenant
            timeout_seconds: Tempo máximo de espera (0 = não espera)

        Returns:
            True se conseguiu o lock, False caso contrário

        Example:
            >>> manager = WatermarkManager(engine)
            >>> if manager.acquire_lock(1):
            ...     try:
            ...         # Executar ETL
            ...         pass
            ...     finally:
            ...         manager.release_lock(1)
            ... else:
            ...     print("ETL já está rodando para este tenant")
        """
        # Gerar lock_id único baseado no tenant_id
        # Usar hash para garantir que seja um inteiro dentro do range do PostgreSQL
        lock_id = abs(hash(f"etl_tenant_{tenant_id}")) % 2147483647

        # Tentar adquirir lock
        if timeout_seconds > 0:
            # pg_advisory_lock (espera até conseguir ou timeout)
            query = text("""
                SET statement_timeout = :timeout_ms;
                SELECT pg_advisory_lock(:lock_id);
                RESET statement_timeout;
            """)
            try:
                with self.local_engine.begin() as conn:
                    conn.execute(
                        query,
                        {
                            'lock_id': lock_id,
                            'timeout_ms': timeout_seconds * 1000
                        }
                    )
                self.active_locks[tenant_id] = lock_id
                logger.info(f"Lock adquirido para tenant {tenant_id} (lock_id={lock_id})")
                return True
            except Exception as e:
                logger.warning(f"Falha ao adquirir lock para tenant {tenant_id}: {str(e)}")
                return False
        else:
            # pg_try_advisory_lock (retorna imediatamente)
            query = text("SELECT pg_try_advisory_lock(:lock_id)")

            with self.local_engine.connect() as conn:
                result = conn.execute(query, {'lock_id': lock_id}).scalar()

                if result:
                    self.active_locks[tenant_id] = lock_id
                    logger.info(f"Lock adquirido para tenant {tenant_id} (lock_id={lock_id})")
                    return True
                else:
                    logger.warning(
                        f"Lock NÃO adquirido para tenant {tenant_id} "
                        f"(ETL já está rodando)"
                    )
                    return False

    def release_lock(self, tenant_id: int) -> bool:
        """
        Libera o advisory lock de um tenant.

        Args:
            tenant_id: ID do tenant

        Returns:
            True se liberou com sucesso, False caso contrário

        Example:
            >>> manager = WatermarkManager(engine)
            >>> manager.release_lock(1)
        """
        if tenant_id not in self.active_locks:
            logger.warning(f"Tentativa de liberar lock não adquirido para tenant {tenant_id}")
            return False

        lock_id = self.active_locks[tenant_id]

        query = text("SELECT pg_advisory_unlock(:lock_id)")

        try:
            with self.local_engine.connect() as conn:
                result = conn.execute(query, {'lock_id': lock_id}).scalar()

                if result:
                    del self.active_locks[tenant_id]
                    logger.info(f"Lock liberado para tenant {tenant_id} (lock_id={lock_id})")
                    return True
                else:
                    logger.warning(f"Falha ao liberar lock para tenant {tenant_id}")
                    return False
        except Exception as e:
            logger.error(f"Erro ao liberar lock para tenant {tenant_id}: {str(e)}")
            return False

    def get_execution_history(
        self,
        tenant_id: Optional[int] = None,
        limit: int = 10
    ) -> list:
        """
        Retorna histórico de execuções do ETL.

        Args:
            tenant_id: ID do tenant (None = todos)
            limit: Número máximo de registros

        Returns:
            Lista de dicionários com histórico

        Example:
            >>> manager = WatermarkManager(engine)
            >>> history = manager.get_execution_history(tenant_id=1, limit=5)
            >>> for exec in history:
            ...     print(f"ID: {exec['id']}, Status: {exec['status']}")
        """
        query = """
            SELECT
                id,
                tenant_id,
                started_at,
                finished_at,
                duration_seconds,
                load_type,
                is_full_load,
                status,
                triggered_by,
                watermark_start,
                watermark_end,
                records_extracted,
                records_inserted,
                records_updated,
                records_failed,
                error_message
            FROM etl_control
        """

        if tenant_id is not None:
            query += " WHERE tenant_id = :tenant_id"

        query += " ORDER BY started_at DESC LIMIT :limit"

        params = {'limit': limit}
        if tenant_id is not None:
            params['tenant_id'] = tenant_id

        with self.local_engine.connect() as conn:
            result = conn.execute(text(query), params)

            history = []
            for row in result:
                history.append({
                    'id': row[0],
                    'tenant_id': row[1],
                    'started_at': row[2],
                    'finished_at': row[3],
                    'duration_seconds': row[4],
                    'load_type': row[5],
                    'is_full_load': row[6],
                    'status': row[7],
                    'triggered_by': row[8],
                    'watermark_start': row[9],
                    'watermark_end': row[10],
                    'records_extracted': row[11],
                    'records_inserted': row[12],
                    'records_updated': row[13],
                    'records_failed': row[14],
                    'error_message': row[15]
                })

            return history


# Exemplo de uso
if __name__ == "__main__":
    import sys
    sys.path.append('/home/tester/projetos/allpfit-analytics')

    from urllib.parse import quote_plus

    # Configurar engine local
    password = quote_plus("AllpFit2024@Analytics")
    LOCAL_DB_URL = f"postgresql://isaac:{password}@localhost:5432/geniai_analytics"
    local_engine = create_engine(LOCAL_DB_URL)

    # Criar manager
    manager = WatermarkManager(local_engine)

    logger.info("=" * 80)
    logger.info("TESTE: Watermark Manager")
    logger.info("=" * 80)

    try:
        # 1. Verificar último watermark
        print("\n1. Verificando último watermark do tenant 1:")
        last_watermark = manager.get_last_watermark(1)
        print(f"   Último watermark: {last_watermark}")

        # 2. Testar lock
        print("\n2. Testando advisory lock:")
        if manager.acquire_lock(1):
            print("   Lock adquirido com sucesso!")

            # Tentar adquirir novamente (deve falhar)
            print("   Tentando adquirir novamente (deve falhar):")
            if not manager.acquire_lock(1):
                print("   ✓ Corretamente bloqueado (ETL já rodando)")

            # Liberar lock
            manager.release_lock(1)
            print("   Lock liberado")
        else:
            print("   Falha ao adquirir lock (ETL já rodando?)")

        # 3. Criar execução de teste
        print("\n3. Criando execução de teste:")
        execution_id = manager.create_execution(
            tenant_id=1,
            load_type='incremental',
            watermark_start=last_watermark,
            triggered_by='test_script'
        )
        print(f"   Execução criada: ID={execution_id}")

        # 4. Atualizar execução
        print("\n4. Atualizando execução:")
        manager.update_execution(
            execution_id=execution_id,
            status='success',
            stats={
                'records_extracted': 100,
                'records_inserted': 80,
                'records_updated': 20
            }
        )
        print(f"   Execução {execution_id} atualizada com sucesso")

        # 5. Ver histórico
        print("\n5. Histórico de execuções (últimas 5):")
        history = manager.get_execution_history(tenant_id=1, limit=5)
        for exec in history:
            print(f"   ID: {exec['id']}, Status: {exec['status']}, "
                  f"Extracted: {exec['records_extracted']}, "
                  f"Duration: {exec['duration_seconds']}s")

        logger.info("Teste concluído com sucesso!")

    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        sys.exit(1)