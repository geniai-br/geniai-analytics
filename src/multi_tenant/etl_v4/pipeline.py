"""
Pipeline - ETL V4 Multi-Tenant
==============================

Orquestra o processo completo de ETL: Extract → Transform → Load

Funcionalidades:
    - Execução por tenant ou para todos os tenants
    - Extração incremental (com watermark)
    - Extração full (sem watermark)
    - Advisory locks (evita execução simultânea)
    - Logging estruturado e detalhado
    - Estatísticas completas

Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Adicionar diretório raiz ao path
sys.path.append('/home/tester/projetos/allpfit-analytics')

# Importar módulos do ETL
from src.multi_tenant.etl_v4.extractor import RemoteExtractor
from src.multi_tenant.etl_v4.transformer import ConversationTransformer
from src.multi_tenant.etl_v4.loader import ConversationLoader
from src.multi_tenant.etl_v4.watermark_manager import WatermarkManager

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """Orquestra o pipeline completo de ETL multi-tenant"""

    def __init__(
        self,
        local_engine: Optional[Engine] = None,
        remote_engine: Optional[Engine] = None
    ):
        """
        Inicializa o pipeline.

        Args:
            local_engine: Engine do banco local (geniai_analytics)
            remote_engine: Engine do banco remoto (chatwoot)
        """
        # Criar engines se não fornecidas
        self.local_engine = local_engine or self._create_local_engine()
        self.remote_engine = remote_engine  # Will be passed to RemoteExtractor

        # Inicializar componentes
        self.extractor = RemoteExtractor(remote_engine=self.remote_engine)
        self.watermark_manager = WatermarkManager(self.local_engine)

        logger.info("ETLPipeline inicializado")

    def _create_local_engine(self) -> Engine:
        """Cria engine para banco local usando variáveis de ambiente"""
        host = os.getenv('LOCAL_DB_HOST', 'localhost')
        port = os.getenv('LOCAL_DB_PORT', '5432')
        database = os.getenv('LOCAL_DB_NAME', 'geniai_analytics')
        # Usar johan_geniai (owner) para bypassa RLS no ETL
        user = os.getenv('LOCAL_DB_USER', 'johan_geniai')
        password = os.getenv('LOCAL_DB_PASSWORD', 'vlVMVM6UNz2yYSBlzodPjQvZh')

        # URL encode password
        password_encoded = quote_plus(password)

        connection_string = f"postgresql://{user}:{password_encoded}@{host}:{port}/{database}"

        engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True,
            echo=False
        )

        logger.info(f"Engine local criada: {host}:{port}/{database}")
        return engine

    def run_for_tenant(
        self,
        tenant_id: int,
        force_full: bool = False,
        chunk_size: int = 10000,
        triggered_by: str = 'manual'
    ) -> Dict[str, Any]:
        """
        Executa ETL para um tenant específico.

        Args:
            tenant_id: ID do tenant
            force_full: Se True, ignora watermark e faz full sync
            chunk_size: Tamanho do chunk para extração
            triggered_by: Quem disparou a execução

        Returns:
            Dicionário com estatísticas da execução

        Example:
            >>> pipeline = ETLPipeline()
            >>> stats = pipeline.run_for_tenant(tenant_id=1)
            >>> print(f"Inserted: {stats['records_inserted']}")
        """
        logger.info("=" * 80)
        logger.info(f"INICIANDO ETL - Tenant {tenant_id}")
        logger.info("=" * 80)

        execution_id = None
        lock_acquired = False

        try:
            # 1. Adquirir lock (evitar execução simultânea)
            logger.info("Adquirindo lock...")
            if not self.watermark_manager.acquire_lock(tenant_id):
                raise Exception(
                    f"ETL já está rodando para tenant {tenant_id}. "
                    "Aguarde a execução atual terminar."
                )
            lock_acquired = True

            # 2. Determinar watermark
            watermark_start = None
            load_type = 'full'

            if not force_full:
                watermark_start = self.watermark_manager.get_last_watermark(tenant_id)
                if watermark_start:
                    load_type = 'incremental'
                    logger.info(f"Extração INCREMENTAL desde {watermark_start}")
                else:
                    logger.info("Extração FULL (primeiro sync)")
            else:
                logger.info("Extração FULL (forçada)")

            watermark_end = datetime.now()

            # 3. Criar registro de execução
            execution_id = self.watermark_manager.create_execution(
                tenant_id=tenant_id,
                load_type=load_type,
                watermark_start=watermark_start,
                watermark_end=watermark_end,
                triggered_by=triggered_by
            )

            logger.info(f"Execução {execution_id} criada")

            # 4. EXTRACT - Extrair dados do banco remoto
            logger.info("FASE 1: EXTRACT")
            logger.info("-" * 80)

            total_extracted = 0
            total_inserted = 0
            total_updated = 0
            chunk_count = 0

            # Criar transformer e loader
            transformer = ConversationTransformer(tenant_id=tenant_id)
            loader = ConversationLoader(self.local_engine)

            # Extrair em chunks
            for chunk in self.extractor.extract_by_tenant(
                local_engine=self.local_engine,
                tenant_id=tenant_id,
                watermark_start=watermark_start,
                watermark_end=watermark_end,
                chunk_size=chunk_size
            ):
                chunk_count += 1
                chunk_size_actual = len(chunk)
                total_extracted += chunk_size_actual

                logger.info(f"Chunk {chunk_count}: {chunk_size_actual} conversas extraídas")

                # 5. TRANSFORM - Transformar dados
                logger.info(f"Chunk {chunk_count}: TRANSFORM")
                df_transformed = transformer.transform_chunk(chunk)

                # 6. LOAD - Carregar dados
                logger.info(f"Chunk {chunk_count}: LOAD")
                load_stats = loader.load_chunk(df_transformed)

                total_inserted += load_stats['inserted']
                total_updated += load_stats['updated']

                logger.info(
                    f"Chunk {chunk_count}: "
                    f"{load_stats['inserted']} inseridas, "
                    f"{load_stats['updated']} atualizadas"
                )

            # 7. Atualizar registro de execução (sucesso)
            stats = {
                'records_extracted': total_extracted,
                'records_inserted': total_inserted,
                'records_updated': total_updated,
                'records_failed': 0
            }

            self.watermark_manager.update_execution(
                execution_id=execution_id,
                status='success',
                stats=stats
            )

            # 8. Log final
            logger.info("=" * 80)
            logger.info("ETL CONCLUÍDO COM SUCESSO")
            logger.info("-" * 80)
            logger.info(f"Tenant: {tenant_id}")
            logger.info(f"Tipo: {load_type}")
            logger.info(f"Chunks processados: {chunk_count}")
            logger.info(f"Conversas extraídas: {total_extracted}")
            logger.info(f"Conversas inseridas: {total_inserted}")
            logger.info(f"Conversas atualizadas: {total_updated}")
            logger.info(f"Watermark: {watermark_start} → {watermark_end}")
            logger.info("=" * 80)

            return {
                'success': True,
                'execution_id': execution_id,
                'tenant_id': tenant_id,
                'load_type': load_type,
                'chunks_processed': chunk_count,
                'records_extracted': total_extracted,
                'records_inserted': total_inserted,
                'records_updated': total_updated,
                'watermark_start': watermark_start,
                'watermark_end': watermark_end
            }

        except Exception as e:
            logger.error(f"ERRO NO ETL: {str(e)}", exc_info=True)

            # Atualizar registro de execução (erro)
            if execution_id:
                self.watermark_manager.update_execution(
                    execution_id=execution_id,
                    status='error',
                    stats={
                        'records_extracted': total_extracted if 'total_extracted' in locals() else 0,
                        'records_inserted': total_inserted if 'total_inserted' in locals() else 0,
                        'records_updated': total_updated if 'total_updated' in locals() else 0,
                        'records_failed': 0
                    },
                    error_message=str(e)
                )

            return {
                'success': False,
                'execution_id': execution_id,
                'tenant_id': tenant_id,
                'error': str(e)
            }

        finally:
            # Liberar lock
            if lock_acquired:
                self.watermark_manager.release_lock(tenant_id)
                logger.info(f"Lock liberado para tenant {tenant_id}")

    def run_for_all_tenants(
        self,
        force_full: bool = False,
        chunk_size: int = 10000,
        triggered_by: str = 'scheduler'
    ) -> Dict[int, Dict[str, Any]]:
        """
        Executa ETL para todos os tenants ativos.

        Args:
            force_full: Se True, ignora watermark e faz full sync
            chunk_size: Tamanho do chunk para extração
            triggered_by: Quem disparou a execução

        Returns:
            Dicionário com estatísticas por tenant {tenant_id: stats}

        Example:
            >>> pipeline = ETLPipeline()
            >>> results = pipeline.run_for_all_tenants()
            >>> for tenant_id, stats in results.items():
            ...     print(f"Tenant {tenant_id}: {stats['records_inserted']} inseridas")
        """
        logger.info("=" * 80)
        logger.info("EXECUTANDO ETL PARA TODOS OS TENANTS")
        logger.info("=" * 80)

        # Buscar tenants ativos
        query = text("""
            SELECT DISTINCT tenant_id
            FROM inbox_tenant_mapping
            WHERE is_active = TRUE
            ORDER BY tenant_id
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query)
            tenant_ids = [row[0] for row in result]

        logger.info(f"Tenants encontrados: {tenant_ids}")

        results = {}

        for tenant_id in tenant_ids:
            logger.info("")
            logger.info(f"Processando tenant {tenant_id}...")

            try:
                stats = self.run_for_tenant(
                    tenant_id=tenant_id,
                    force_full=force_full,
                    chunk_size=chunk_size,
                    triggered_by=triggered_by
                )
                results[tenant_id] = stats
            except Exception as e:
                logger.error(f"Erro ao processar tenant {tenant_id}: {str(e)}")
                results[tenant_id] = {
                    'success': False,
                    'error': str(e)
                }

        # Log resumo
        logger.info("")
        logger.info("=" * 80)
        logger.info("RESUMO DA EXECUÇÃO")
        logger.info("=" * 80)

        for tenant_id, stats in results.items():
            if stats.get('success'):
                logger.info(
                    f"Tenant {tenant_id}: ✓ Sucesso - "
                    f"{stats['records_extracted']} extraídas, "
                    f"{stats['records_inserted']} inseridas, "
                    f"{stats['records_updated']} atualizadas"
                )
            else:
                logger.error(f"Tenant {tenant_id}: ✗ Erro - {stats.get('error', 'Unknown')}")

        logger.info("=" * 80)

        return results

    def test_connection(self) -> bool:
        """
        Testa conexões com bancos local e remoto.

        Returns:
            True se ambas as conexões estão OK
        """
        logger.info("Testando conexões...")

        # Testar banco local
        try:
            with self.local_engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).scalar()
                logger.info(f"✓ Banco local OK: {result.split(',')[0]}")
        except Exception as e:
            logger.error(f"✗ Erro ao conectar no banco local: {str(e)}")
            return False

        # Testar banco remoto
        if not self.extractor.test_connection():
            logger.error("✗ Erro ao conectar no banco remoto")
            return False

        logger.info("✓ Todas as conexões OK")
        return True


# CLI para execução via linha de comando
def main():
    """Função principal para execução via CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description='ETL Pipeline Multi-Tenant - GeniAI Analytics'
    )
    parser.add_argument(
        '--tenant-id',
        type=int,
        help='ID do tenant (omitir para executar para todos)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Forçar full sync (ignorar watermark)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=10000,
        help='Tamanho do chunk para extração (default: 10000)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Apenas testar conexões'
    )

    args = parser.parse_args()

    # Criar pipeline
    pipeline = ETLPipeline()

    # Testar conexões
    if args.test:
        if pipeline.test_connection():
            print("\n✓ Teste de conexões: SUCESSO")
            sys.exit(0)
        else:
            print("\n✗ Teste de conexões: FALHA")
            sys.exit(1)

    # Executar ETL
    if args.tenant_id:
        # ETL para tenant específico
        stats = pipeline.run_for_tenant(
            tenant_id=args.tenant_id,
            force_full=args.full,
            chunk_size=args.chunk_size,
            triggered_by='cli'
        )

        if stats['success']:
            print("\n" + "=" * 80)
            print("ETL CONCLUÍDO COM SUCESSO")
            print("-" * 80)
            print(f"Tenant: {stats['tenant_id']}")
            print(f"Tipo: {stats['load_type']}")
            print(f"Chunks: {stats['chunks_processed']}")
            print(f"Extraídas: {stats['records_extracted']}")
            print(f"Inseridas: {stats['records_inserted']}")
            print(f"Atualizadas: {stats['records_updated']}")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("ETL FALHOU")
            print("-" * 80)
            print(f"Erro: {stats.get('error', 'Unknown')}")
            print("=" * 80)
            sys.exit(1)
    else:
        # ETL para todos os tenants
        results = pipeline.run_for_all_tenants(
            force_full=args.full,
            chunk_size=args.chunk_size,
            triggered_by='cli'
        )

        # Verificar se todos tiveram sucesso
        all_success = all(stats.get('success', False) for stats in results.values())

        if all_success:
            print("\n✓ ETL concluído para todos os tenants")
            sys.exit(0)
        else:
            print("\n✗ ETL falhou para um ou mais tenants")
            sys.exit(1)


if __name__ == "__main__":
    main()
