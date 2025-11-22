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
sys.path.append('/home/tester/projetos/geniai-analytics')

# Importar módulos do ETL
from src.multi_tenant.etl_v4.extractor import RemoteExtractor
from src.multi_tenant.etl_v4.transformer import ConversationTransformer
from src.multi_tenant.etl_v4.loader import ConversationLoader
from src.multi_tenant.etl_v4.watermark_manager import WatermarkManager
from src.multi_tenant.etl_v4.inbox_sync import InboxSyncManager
from src.multi_tenant.etl_v4.remarketing_analyzer import (
    detect_and_reset_reopened_conversations,
    analyze_inactive_leads
)

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

    def _get_tenant_config(self, tenant_id: int) -> Dict[str, Any]:
        """
        Busca configuração do tenant no banco.

        Args:
            tenant_id: ID do tenant

        Returns:
            Dict com configuração do tenant
        """
        query = text("""
            SELECT
                tc.features,
                t.name as tenant_name
            FROM tenant_configs tc
            JOIN tenants t ON t.id = tc.tenant_id
            WHERE tc.tenant_id = :tenant_id
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id})
            row = result.fetchone()

            if not row:
                logger.warning(f"Configuração não encontrada para tenant {tenant_id}, usando defaults")
                return {
                    'tenant_name': f'Tenant {tenant_id}',
                    'use_openai': False,
                    'features': {}
                }

            features = row[0] if row[0] else {}
            tenant_name = row[1]

            return {
                'tenant_name': tenant_name,
                'use_openai': features.get('use_openai', False),
                'features': features
            }

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

        # Estatísticas OpenAI (rastreadas ao longo da execução)
        openai_stats = {
            'api_calls': 0,
            'total_tokens': 0,
            'cost_brl': 0.0
        }

        try:
            # 1. Ler configuração do tenant
            tenant_config = self._get_tenant_config(tenant_id)
            use_openai = tenant_config['use_openai']
            tenant_name = tenant_config['tenant_name']

            logger.info(f"Tenant: {tenant_name} (ID: {tenant_id})")
            logger.info(f"Analyzer: {'OpenAI GPT-4o-mini' if use_openai else 'Regex (keywords)'}")

            # 1.5. Sincronizar inboxes automaticamente
            logger.info("")
            logger.info("FASE 0: INBOX SYNC (Detecção Automática de Novos Inboxes)")
            logger.info("-" * 80)

            try:
                inbox_sync_manager = InboxSyncManager(
                    local_engine=self.local_engine,
                    remote_engine=self.extractor.remote_engine
                )
                sync_result = inbox_sync_manager.sync_tenant_inboxes(
                    tenant_id=tenant_id,
                    tenant_name=tenant_name
                )

                if sync_result['new_inboxes']:
                    logger.warning(
                        f"🆕 {len(sync_result['new_inboxes'])} novo(s) inbox(es) adicionado(s): "
                        f"{sync_result['new_inboxes']}"
                    )
                else:
                    logger.info("✅ Nenhum inbox novo detectado")

            except Exception as e:
                logger.warning(f"⚠️  Falha na sincronização de inboxes: {e}")
                logger.warning("   Continuando com inboxes cadastrados atualmente...")

            logger.info("-" * 80)
            logger.info("")

            # 2. Adquirir lock (evitar execução simultânea)
            logger.info("Adquirindo lock...")
            if not self.watermark_manager.acquire_lock(tenant_id):
                raise Exception(
                    f"ETL já está rodando para tenant {tenant_id}. "
                    "Aguarde a execução atual terminar."
                )
            lock_acquired = True

            # 3. Determinar watermark
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

            # 4. Criar registro de execução
            execution_id = self.watermark_manager.create_execution(
                tenant_id=tenant_id,
                load_type=load_type,
                watermark_start=watermark_start,
                watermark_end=watermark_end,
                triggered_by=triggered_by
            )

            logger.info(f"Execução {execution_id} criada")

            # 5. EXTRACT - Extrair dados do banco remoto
            logger.info("FASE 1: EXTRACT")
            logger.info("-" * 80)

            total_extracted = 0
            total_inserted = 0
            total_updated = 0
            chunk_count = 0

            # 6. Criar transformer com config do tenant (Fase 5.6 - OpenAI)
            openai_api_key = os.getenv('OPENAI_API_KEY') if use_openai else None

            transformer = ConversationTransformer(
                tenant_id=tenant_id,
                enable_lead_analysis=True,
                use_openai=use_openai,
                openai_api_key=openai_api_key
            )

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

                # 7. TRANSFORM - Transformar dados
                logger.info(f"Chunk {chunk_count}: TRANSFORM")
                df_transformed = transformer.transform_chunk(chunk)

                # 7.1 Coletar estatísticas OpenAI (se usando OpenAI)
                if use_openai and hasattr(transformer, 'lead_analyzer'):
                    analyzer = transformer.lead_analyzer
                    if hasattr(analyzer, 'get_usage_stats'):
                        usage = analyzer.get_usage_stats()
                        openai_stats['api_calls'] += usage.get('successful_calls', 0)
                        openai_stats['total_tokens'] += usage.get('total_tokens', 0)

                # 8. LOAD - Carregar dados
                logger.info(f"Chunk {chunk_count}: LOAD")
                load_stats = loader.load_chunk(df_transformed)

                total_inserted += load_stats['inserted']
                total_updated += load_stats['updated']

                logger.info(
                    f"Chunk {chunk_count}: "
                    f"{load_stats['inserted']} inseridas, "
                    f"{load_stats['updated']} atualizadas"
                )

            # FASE 3.5: RESET REOPENED CONVERSATIONS
            logger.info("")
            logger.info("FASE 3.5: RESET REOPENED CONVERSATIONS")
            logger.info("-" * 80)

            resetados_count = detect_and_reset_reopened_conversations(
                local_engine=self.local_engine,
                tenant_id=tenant_id
            )

            if resetados_count > 0:
                logger.info(f"✅ {resetados_count} conversas reabertas resetadas")
            else:
                logger.info("✅ Nenhuma conversa reaberta detectada")

            # FASE 4: ANALYZE INACTIVE LEADS (24h+)
            logger.info("")
            logger.info("FASE 4: ANALYZE INACTIVE LEADS (24h+)")
            logger.info("-" * 80)

            # Configurações de análise
            analyze_limit = int(os.getenv('ANALYZE_LEADS_LIMIT', '10'))
            analyze_max_cost = float(os.getenv('ANALYZE_LEADS_MAX_COST_BRL', '0.10'))

            remarketing_stats = analyze_inactive_leads(
                local_engine=self.local_engine,
                tenant_id=tenant_id,
                openai_api_key=openai_api_key,
                limit=analyze_limit,
                max_cost_brl=analyze_max_cost
            )

            # Adicionar estatísticas de remarketing ao OpenAI stats
            if remarketing_stats.get('analyzed_count', 0) > 0:
                openai_stats['api_calls'] += remarketing_stats['analyzed_count']
                openai_stats['total_tokens'] += remarketing_stats['total_tokens']
                openai_stats['cost_brl'] += remarketing_stats['total_cost_brl']

                logger.info(
                    f"✅ Remarketing: {remarketing_stats['analyzed_count']} leads analisados | "
                    f"Tokens: {remarketing_stats['total_tokens']} | "
                    f"Custo: R$ {remarketing_stats['total_cost_brl']:.4f}"
                )

            # 9. Calcular custo OpenAI (se usado)
            if openai_stats['total_tokens'] > 0:
                # Custo aproximado: R$ 0.0004 por 1K tokens (GPT-4o-mini)
                # Taxa USD -> BRL: ~5.50
                cost_per_1k_tokens_usd = 0.0004
                usd_to_brl = 5.50
                openai_stats['cost_brl'] = round(
                    (openai_stats['total_tokens'] / 1000.0) * cost_per_1k_tokens_usd * usd_to_brl,
                    4
                )

                logger.info(f"OpenAI Stats: {openai_stats['api_calls']} calls, "
                           f"{openai_stats['total_tokens']} tokens, "
                           f"R$ {openai_stats['cost_brl']:.4f}")

            # 10. Atualizar registro de execução (sucesso)
            stats = {
                'records_extracted': total_extracted,
                'records_inserted': total_inserted,
                'records_updated': total_updated,
                'records_failed': 0,
                'openai_api_calls': openai_stats['api_calls'],
                'openai_total_tokens': openai_stats['total_tokens'],
                'openai_cost_brl': openai_stats['cost_brl']
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
