"""
Loader - ETL V4 Multi-Tenant
============================

Responsável por carregar dados transformados no banco local.

Funcionalidades:
    - UPSERT (INSERT ... ON CONFLICT UPDATE)
    - Unique key: (tenant_id, conversation_id)
    - Batch inserts usando pandas to_sql
    - Atualização de etl_inserted_at e etl_updated_at
    - Logging estruturado

Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
from typing import Dict, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationLoader:
    """Carrega dados de conversas no banco local usando UPSERT"""

    def __init__(self, local_engine: Engine):
        """
        Inicializa o loader.

        Args:
            local_engine: Engine SQLAlchemy conectada ao banco local
        """
        self.local_engine = local_engine
        logger.info("ConversationLoader inicializado")

    def load_chunk(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Carrega um chunk de dados usando UPSERT.

        Args:
            df: DataFrame com dados transformados

        Returns:
            Dicionário com estatísticas: {'inserted': X, 'updated': Y}

        Example:
            >>> loader = ConversationLoader(engine)
            >>> stats = loader.load_chunk(df_transformed)
            >>> print(f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
        """
        if df.empty:
            logger.warning("DataFrame vazio recebido para carga")
            return {'inserted': 0, 'updated': 0}

        logger.info(f"Carregando {len(df)} conversas no banco local")

        # Preparar dados para insert
        df_prepared = self._prepare_for_insert(df)

        # Executar UPSERT
        inserted, updated = self._upsert_conversations(df_prepared)

        logger.info(f"Carga concluída: {inserted} inseridas, {updated} atualizadas")

        return {
            'inserted': inserted,
            'updated': updated,
            'total': len(df)
        }

    def _prepare_for_insert(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara DataFrame para inserção no PostgreSQL.

        Args:
            df: DataFrame com dados transformados

        Returns:
            DataFrame preparado para inserção
        """
        df_copy = df.copy()

        # Substituir NaN por None (PostgreSQL NULL)
        df_copy = df_copy.replace({np.nan: None, pd.NaT: None})

        # Garantir que campos obrigatórios existem
        required_fields = ['tenant_id', 'conversation_id']
        for field in required_fields:
            if field not in df_copy.columns:
                raise ValueError(f"Campo obrigatório ausente: {field}")

        # Remover colunas que não existem na tabela de destino
        # (etl_inserted_at e etl_updated_at são gerados pelo banco)
        columns_to_drop = []
        for col in df_copy.columns:
            if col in ['etl_inserted_at', 'etl_updated_at']:
                columns_to_drop.append(col)

        if columns_to_drop:
            df_copy = df_copy.drop(columns=columns_to_drop)

        logger.debug(f"DataFrame preparado: {len(df_copy)} linhas, {len(df_copy.columns)} colunas")

        return df_copy

    def _upsert_conversations(self, df: pd.DataFrame) -> Tuple[int, int]:
        """
        Executa UPSERT (INSERT ... ON CONFLICT UPDATE) no PostgreSQL.

        Args:
            df: DataFrame preparado para inserção

        Returns:
            Tupla (inserted_count, updated_count)
        """
        if df.empty:
            return 0, 0

        # Get conversation_ids to check which already exist
        # Convert numpy types to Python native types
        conversation_ids = [int(x) for x in df['conversation_id'].tolist()]
        tenant_id = int(df['tenant_id'].iloc[0])

        try:
            with self.local_engine.begin() as conn:
                # Set role to etl_service to bypass RLS
                conn.execute(text("SET ROLE etl_service"))

                # 1. Count existing records
                count_existing_query = text("""
                    SELECT COUNT(*)
                    FROM conversations_analytics
                    WHERE tenant_id = :tenant_id
                      AND conversation_id = ANY(:conversation_ids)
                """)

                existing_count = conn.execute(
                    count_existing_query,
                    {
                        'tenant_id': tenant_id,
                        'conversation_ids': conversation_ids
                    }
                ).scalar()

                # 2. Build UPSERT query
                # Get all columns except primary key
                columns = [col for col in df.columns if col not in ['id']]

                # Build column list
                columns_str = ', '.join(columns)

                # Build placeholders (:col1, :col2, ...)
                placeholders_str = ', '.join([f':{col}' for col in columns])

                # Build UPDATE SET clause
                update_set = []
                for col in columns:
                    if col not in ['tenant_id', 'conversation_id']:
                        update_set.append(f"{col} = EXCLUDED.{col}")

                # Add etl_updated_at update
                update_set.append("etl_updated_at = NOW()")
                update_set_str = ', '.join(update_set)

                # UPSERT query
                upsert_query = text(f"""
                    INSERT INTO conversations_analytics ({columns_str})
                    VALUES ({placeholders_str})
                    ON CONFLICT (tenant_id, conversation_id)
                    DO UPDATE SET {update_set_str}
                """)

                # 3. Execute UPSERT for each row
                logger.debug(f"Executando UPSERT para {len(df)} conversas...")

                # Convert DataFrame to list of dicts
                records = df.to_dict('records')

                # Execute batch insert
                conn.execute(upsert_query, records)

                # 4. Calculate statistics
                inserted_count = len(df) - existing_count
                updated_count = existing_count

                logger.debug(f"UPSERT concluído: {inserted_count} inseridas, {updated_count} atualizadas")

                return inserted_count, updated_count

        except Exception as e:
            logger.error(f"Erro ao executar UPSERT: {str(e)}")
            raise

    def get_existing_conversation_ids(
        self,
        tenant_id: int,
        conversation_ids: list
    ) -> set:
        """
        Verifica quais conversation_ids já existem no banco.

        Args:
            tenant_id: ID do tenant
            conversation_ids: Lista de conversation_ids para verificar

        Returns:
            Set de conversation_ids que já existem

        Example:
            >>> loader = ConversationLoader(engine)
            >>> existing = loader.get_existing_conversation_ids(1, [5804, 5805])
            >>> print(f"Já existem: {existing}")
        """
        if not conversation_ids:
            return set()

        query = text("""
            SELECT conversation_id
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
              AND conversation_id = ANY(:conversation_ids)
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(
                query,
                {
                    'tenant_id': tenant_id,
                    'conversation_ids': conversation_ids
                }
            )
            existing = {row[0] for row in result}

        logger.debug(f"Tenant {tenant_id}: {len(existing)}/{len(conversation_ids)} conversas já existem")

        return existing

    def get_load_statistics(self, tenant_id: int) -> Dict[str, any]:
        """
        Retorna estatísticas de dados carregados para um tenant.

        Args:
            tenant_id: ID do tenant

        Returns:
            Dicionário com estatísticas

        Example:
            >>> loader = ConversationLoader(engine)
            >>> stats = loader.get_load_statistics(1)
            >>> print(f"Total: {stats['total_conversations']}")
        """
        query = text("""
            SELECT
                COUNT(*) as total_conversations,
                MIN(conversation_created_at) as first_conversation,
                MAX(conversation_created_at) as last_conversation,
                MIN(etl_inserted_at) as first_load,
                MAX(etl_updated_at) as last_update,
                COUNT(DISTINCT inbox_id) as total_inboxes
            FROM conversations_analytics
            WHERE tenant_id = :tenant_id
        """)

        with self.local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id}).fetchone()

            if result:
                return {
                    'tenant_id': tenant_id,
                    'total_conversations': result[0],
                    'first_conversation': result[1],
                    'last_conversation': result[2],
                    'first_load': result[3],
                    'last_update': result[4],
                    'total_inboxes': result[5]
                }
            else:
                return {
                    'tenant_id': tenant_id,
                    'total_conversations': 0,
                    'first_conversation': None,
                    'last_conversation': None,
                    'first_load': None,
                    'last_update': None,
                    'total_inboxes': 0
                }


# Exemplo de uso
if __name__ == "__main__":
    import sys
    sys.path.append('/home/tester/projetos/allpfit-analytics')

    from urllib.parse import quote_plus

    # Configurar engine local
    password = quote_plus("AllpFit2024@Analytics")
    LOCAL_DB_URL = f"postgresql://isaac:{password}@localhost:5432/geniai_analytics"
    local_engine = create_engine(LOCAL_DB_URL)

    # Criar loader
    loader = ConversationLoader(local_engine)

    # Exemplo: Simular dados para teste
    sample_data = {
        'tenant_id': [1],
        'conversation_id': [99999],  # ID de teste
        'display_id': [99999],
        'inbox_id': [61],
        'inbox_name': ['Test Inbox'],
        'contact_id': [1234],
        'contact_name': ['Test Contact'],
        'contact_phone': ['+5511999999999'],
        'conversation_created_at': [pd.Timestamp.now()],
        'conversation_updated_at': [pd.Timestamp.now()],
        'conversation_date': [pd.Timestamp.now().date()],
        't_messages': [5],
        'user_messages_count': [2],
        'contact_messages_count': [3],
        'status': [0],
        'status_label_pt': ['Aberta'],
        'is_resolved': [False],
        'is_open': [True],
    }

    df_test = pd.DataFrame(sample_data)

    # Testar carga
    logger.info("=" * 80)
    logger.info("TESTE: Carregando dados de teste")
    logger.info("=" * 80)

    try:
        stats = loader.load_chunk(df_test)
        print(f"\nEstatísticas de carga:")
        print(f"  Inseridas: {stats['inserted']}")
        print(f"  Atualizadas: {stats['updated']}")
        print(f"  Total: {stats['total']}")

        # Verificar estatísticas do tenant
        tenant_stats = loader.get_load_statistics(1)
        print(f"\nEstatísticas do Tenant 1:")
        print(f"  Total de conversas: {tenant_stats['total_conversations']}")
        print(f"  Inboxes: {tenant_stats['total_inboxes']}")
        print(f"  Última atualização: {tenant_stats['last_update']}")

        logger.info("Teste concluído com sucesso!")

        # Limpar dados de teste
        with local_engine.begin() as conn:
            conn.execute(text(
                "DELETE FROM conversations_analytics WHERE conversation_id = 99999"
            ))
        logger.info("Dados de teste removidos")

    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        sys.exit(1)
