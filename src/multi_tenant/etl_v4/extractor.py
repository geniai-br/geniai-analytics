"""
Extractor - ETL V4 Multi-Tenant
===============================

Responsável por extrair dados da view remota do Chatwoot (vw_conversations_analytics_final).

Funcionalidades:
    - Extração por tenant (filtrado por inbox_ids)
    - Extração incremental (com watermark)
    - Processamento em chunks (evitar memory error)
    - Logging estruturado

Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RemoteExtractor:
    """Extrai dados do banco remoto Chatwoot"""

    def __init__(self, remote_engine: Engine = None):
        """
        Inicializa o extractor.

        Args:
            remote_engine: Engine SQLAlchemy conectada ao banco remoto.
                          Se None, cria automaticamente usando variáveis de ambiente.
        """
        self.remote_engine = remote_engine or self._create_remote_engine()
        logger.info("RemoteExtractor inicializado")

    def _create_remote_engine(self) -> Engine:
        """Cria engine de conexão com banco remoto"""
        host = os.getenv('REMOTE_DB_HOST', '178.156.206.184')
        port = os.getenv('REMOTE_DB_PORT', '5432')
        database = os.getenv('REMOTE_DB_NAME', 'chatwoot')
        user = os.getenv('REMOTE_DB_USER', 'hetzner_hyago_read')
        password = os.getenv('REMOTE_DB_PASSWORD', 'c1d46b41391f')

        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        engine = create_engine(
            connection_string,
            pool_size=3,  # Máximo 3 conexões simultâneas
            max_overflow=2,  # +2 em picos
            pool_timeout=30,  # Timeout de 30s
            pool_pre_ping=True,  # Verificar conexão antes de usar
            echo=False  # Não logar queries SQL (usar logger em vez disso)
        )

        logger.info(f"Engine remota criada: {host}:{port}/{database}")
        return engine

    def get_tenant_inbox_ids(self, local_engine: Engine, tenant_id: int) -> List[int]:
        """
        Busca inbox_ids de um tenant no banco local.

        Args:
            local_engine: Engine do banco local
            tenant_id: ID do tenant

        Returns:
            Lista de inbox_ids

        Raises:
            ValueError: Se tenant não possui inboxes
        """
        query = text("""
            SELECT inbox_id
            FROM inbox_tenant_mapping
            WHERE tenant_id = :tenant_id
              AND is_active = TRUE
            ORDER BY inbox_id
        """)

        with local_engine.connect() as conn:
            result = conn.execute(query, {'tenant_id': tenant_id})
            inbox_ids = [row[0] for row in result]

        if not inbox_ids:
            raise ValueError(f"Tenant {tenant_id} não possui inboxes ativos")

        logger.info(f"Tenant {tenant_id}: {len(inbox_ids)} inboxes encontrados: {inbox_ids}")
        return inbox_ids

    def extract_conversations(
        self,
        inbox_ids: List[int],
        watermark_start: Optional[datetime] = None,
        watermark_end: Optional[datetime] = None,
        chunk_size: int = 10000
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Extrai conversas de múltiplos inboxes em chunks.

        Args:
            inbox_ids: Lista de inbox_ids para extrair
            watermark_start: Data mínima (extração incremental)
            watermark_end: Data máxima (opcional, default=NOW)
            chunk_size: Tamanho do chunk (default=10000)

        Yields:
            DataFrame com dados de conversas (chunk por chunk)

        Example:
            >>> extractor = RemoteExtractor()
            >>> for chunk in extractor.extract_conversations([61, 64, 67]):
            ...     print(f"Processando {len(chunk)} conversas")
        """
        # Query base
        query = """
            SELECT
                -- Identificadores
                conversation_id,
                display_id,
                conversation_uuid,
                account_id,
                inbox_id,
                contact_id,
                assignee_id,
                team_id,
                campaign_id,

                -- Timestamps
                conversation_created_at,
                conversation_updated_at,
                last_activity_at,
                first_reply_created_at,
                mc_first_message_at,
                mc_last_message_at,
                conversation_date,

                -- Informações de contato
                contact_name,
                contact_email,
                COALESCE(contact_phone, client_phone) as contact_phone,
                contact_identifier,

                -- Informações do inbox
                inbox_name,
                inbox_channel_type,
                account_name,

                -- Métricas de mensagens
                t_messages as total_messages,
                user_messages_count as agent_messages,
                contact_messages_count as contact_messages,
                private_notes_count,

                -- Status e classificação
                status,
                status_label_pt as status_label,
                priority,
                priority_label,

                -- Flags booleanas
                is_resolved,
                is_open,
                is_pending,
                is_assigned,
                has_team,
                has_human_intervention,
                is_bot_resolved,

                -- CSAT
                csat_rating,
                csat_feedback,
                csat_nps_category,

                -- Métricas temporais
                first_response_time_seconds,
                resolution_time_seconds,
                conversation_duration_seconds,

                -- Análise de mensagens
                first_message_text,
                last_message_text,
                message_compiled

            FROM vw_conversations_analytics_final
            WHERE inbox_id = ANY(:inbox_ids)
        """

        # Adicionar filtro de watermark se fornecido
        params = {'inbox_ids': inbox_ids}

        if watermark_start:
            query += " AND conversation_updated_at > :watermark_start"
            params['watermark_start'] = watermark_start

        if watermark_end:
            query += " AND conversation_updated_at <= :watermark_end"
            params['watermark_end'] = watermark_end

        # Ordenar por data para watermark
        query += " ORDER BY conversation_updated_at ASC"

        # Log da extração
        logger.info(f"Iniciando extração de conversas")
        logger.info(f"  Inboxes: {inbox_ids}")
        logger.info(f"  Watermark start: {watermark_start}")
        logger.info(f"  Watermark end: {watermark_end or 'NOW()'}")
        logger.info(f"  Chunk size: {chunk_size}")

        # Executar query em chunks
        offset = 0
        total_extracted = 0

        while True:
            # Adicionar LIMIT/OFFSET
            chunk_query = query + f" LIMIT {chunk_size} OFFSET {offset}"

            # Executar query
            try:
                df = pd.read_sql(
                    text(chunk_query),
                    self.remote_engine,
                    params=params
                )

                if df.empty:
                    logger.info(f"Extração finalizada: {total_extracted} conversas extraídas")
                    break

                total_extracted += len(df)
                logger.info(f"Chunk extraído: {len(df)} conversas (total: {total_extracted})")

                yield df

                offset += chunk_size

            except Exception as e:
                logger.error(f"Erro ao extrair chunk (offset={offset}): {str(e)}")
                raise

    def extract_by_tenant(
        self,
        local_engine: Engine,
        tenant_id: int,
        watermark_start: Optional[datetime] = None,
        watermark_end: Optional[datetime] = None,
        chunk_size: int = 10000
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Extrai conversas de um tenant específico.

        Args:
            local_engine: Engine do banco local (para buscar inbox_ids)
            tenant_id: ID do tenant
            watermark_start: Data mínima (extração incremental)
            watermark_end: Data máxima (opcional)
            chunk_size: Tamanho do chunk

        Yields:
            DataFrame com dados de conversas do tenant

        Example:
            >>> extractor = RemoteExtractor()
            >>> for chunk in extractor.extract_by_tenant(local_engine, tenant_id=1):
            ...     print(f"Tenant 1: {len(chunk)} conversas")
        """
        # Buscar inboxes do tenant
        inbox_ids = self.get_tenant_inbox_ids(local_engine, tenant_id)

        # Extrair conversas desses inboxes
        logger.info(f"Extraindo dados do tenant {tenant_id}")
        yield from self.extract_conversations(
            inbox_ids=inbox_ids,
            watermark_start=watermark_start,
            watermark_end=watermark_end,
            chunk_size=chunk_size
        )

    def test_connection(self) -> bool:
        """
        Testa conexão com banco remoto.

        Returns:
            True se conexão OK, False caso contrário
        """
        try:
            with self.remote_engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).scalar()
                logger.info(f"Conexão remota OK: {result}")
                return True
        except Exception as e:
            logger.error(f"Erro ao conectar no banco remoto: {str(e)}")
            return False


# Exemplo de uso
if __name__ == "__main__":
    import sys
    sys.path.append('/home/tester/projetos/allpfit-analytics')

    from sqlalchemy import create_engine as create_local_engine

    # Configurar engines (URL encoding para @ na senha)
    from urllib.parse import quote_plus
    password = quote_plus("AllpFit2024@Analytics")
    LOCAL_DB_URL = f"postgresql://isaac:{password}@localhost:5432/geniai_analytics"
    local_engine = create_local_engine(LOCAL_DB_URL)

    # Criar extractor
    extractor = RemoteExtractor()

    # Testar conexão
    if not extractor.test_connection():
        logger.error("Falha ao conectar no banco remoto")
        sys.exit(1)

    # Exemplo: Extrair 10 conversas do AllpFit (tenant_id=1)
    logger.info("=" * 80)
    logger.info("TESTE: Extraindo primeiras 10 conversas do AllpFit")
    logger.info("=" * 80)

    try:
        for chunk in extractor.extract_by_tenant(
            local_engine=local_engine,
            tenant_id=1,
            chunk_size=10  # Apenas 10 para teste
        ):
            print(f"\nExtração de teste: {len(chunk)} conversas")
            print(f"Colunas: {list(chunk.columns)}")
            print(f"\nPrimeira conversa:")
            print(chunk.iloc[0].to_dict())
            break  # Apenas 1 chunk para teste

        logger.info("Teste concluído com sucesso!")

    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        sys.exit(1)
