"""
Transformer - ETL V4 Multi-Tenant
=================================

Responsável por transformar e normalizar dados extraídos do Chatwoot.

Funcionalidades:
    - Adicionar tenant_id aos dados
    - Normalizar tipos de dados
    - Mapeamento de colunas (remoto → local)
    - Usar proxies temporários para colunas ausentes
    - Logging estruturado

Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationTransformer:
    """Transforma dados de conversas do formato remoto para o formato local"""

    def __init__(self, tenant_id: int):
        """
        Inicializa o transformer.

        Args:
            tenant_id: ID do tenant para o qual os dados serão transformados
        """
        self.tenant_id = tenant_id
        logger.info(f"ConversationTransformer inicializado para tenant {tenant_id}")

    def transform_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforma um chunk de dados extraídos.

        Args:
            df: DataFrame com dados extraídos do banco remoto

        Returns:
            DataFrame transformado e pronto para carga

        Example:
            >>> transformer = ConversationTransformer(tenant_id=1)
            >>> df_transformed = transformer.transform_chunk(df_extracted)
        """
        if df.empty:
            logger.warning("DataFrame vazio recebido para transformação")
            return df

        logger.info(f"Transformando {len(df)} conversas para tenant {self.tenant_id}")

        # Adicionar tenant_id
        df['tenant_id'] = self.tenant_id

        # Transformar JSON (message_compiled) para string se necessário
        if 'message_compiled' in df.columns:
            df['message_compiled'] = df['message_compiled'].apply(
                lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
            )

        # Normalizar tipos de dados
        df = self._normalize_datatypes(df)

        # Campos calculados (se não existirem)
        df = self._add_calculated_fields(df)

        # ⚠️ PROXIES TEMPORÁRIOS: Colunas ausentes no banco remoto
        # Estes campos serão sempre NULL/False por enquanto
        # TODO: Implementar análise de texto/IA na Fase 4
        logger.debug("Aplicando proxies temporários para colunas ausentes")
        # (Não precisamos adicionar aqui pois o banco já tem defaults)

        logger.info(f"Transformação concluída: {len(df)} conversas processadas")
        return df

    def _normalize_datatypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza tipos de dados para match com o schema do banco local.

        Args:
            df: DataFrame com dados extraídos

        Returns:
            DataFrame com tipos normalizados
        """
        # Converter timestamps para datetime
        timestamp_cols = [
            'conversation_created_at',
            'conversation_updated_at',
            'last_activity_at',
            'first_reply_created_at',
            'mc_first_message_at',
            'mc_last_message_at',
        ]

        for col in timestamp_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Converter UUID para string
        if 'conversation_uuid' in df.columns:
            df['conversation_uuid'] = df['conversation_uuid'].astype(str)

        # Converter inteiros (preencher NaN com None para PostgreSQL)
        integer_cols = [
            'conversation_id', 'display_id', 'account_id', 'inbox_id',
            'contact_id', 'assignee_id', 'team_id', 'campaign_id',
            'status', 'priority', 'csat_rating',
            'first_response_time_seconds', 'resolution_time_seconds'
        ]

        for col in integer_cols:
            if col in df.columns:
                # Converter para float primeiro (suporta NaN), depois para Int64 (nullable integer)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].astype('Int64')  # Nullable integer type

        # Converter floats
        if 'agent_messages' in df.columns:
            df['agent_messages'] = pd.to_numeric(df['agent_messages'], errors='coerce').fillna(0).astype(int)

        if 'contact_messages' in df.columns:
            df['contact_messages'] = pd.to_numeric(df['contact_messages'], errors='coerce').fillna(0).astype(int)

        if 'total_messages' in df.columns:
            df['total_messages'] = pd.to_numeric(df['total_messages'], errors='coerce').fillna(0).astype(int)

        if 'private_notes_count' in df.columns:
            df['private_notes_count'] = pd.to_numeric(df['private_notes_count'], errors='coerce').fillna(0).astype(int)

        # Converter strings (truncar se necessário)
        string_cols = {
            'contact_name': 255,
            'contact_email': 255,
            'contact_phone': 50,
            'contact_identifier': 255,
            'inbox_name': 255,
            'inbox_channel_type': 50,
            'account_name': 255,
            'status_label': 50,
            'priority_label': 20,
            'csat_nps_category': 50,
        }

        for col, max_len in string_cols.items():
            if col in df.columns:
                df[col] = df[col].astype(str).str[:max_len]
                df[col] = df[col].replace({'nan': None, 'None': None, '': None})

        # Converter booleanos
        boolean_cols = [
            'is_resolved', 'is_open', 'is_pending', 'is_assigned',
            'has_team', 'has_human_intervention', 'is_bot_resolved'
        ]

        for col in boolean_cols:
            if col in df.columns:
                df[col] = df[col].fillna(False).astype(bool)

        return df

    def _add_calculated_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adiciona campos calculados que não existem na view remota.

        Args:
            df: DataFrame com dados transformados

        Returns:
            DataFrame com campos calculados
        """
        # Calcular conversation_date a partir de conversation_created_at
        if 'conversation_date' not in df.columns and 'conversation_created_at' in df.columns:
            df['conversation_date'] = pd.to_datetime(df['conversation_created_at']).dt.date

        # Calcular conversation_year, month, day, etc
        if 'conversation_created_at' in df.columns:
            dt = pd.to_datetime(df['conversation_created_at'])

            if 'conversation_year' not in df.columns:
                df['conversation_year'] = dt.dt.year

            if 'conversation_month' not in df.columns:
                df['conversation_month'] = dt.dt.month

            if 'conversation_day' not in df.columns:
                df['conversation_day'] = dt.dt.day

            if 'conversation_day_of_week' not in df.columns:
                df['conversation_day_of_week'] = dt.dt.dayofweek

            if 'conversation_hour' not in df.columns:
                df['conversation_hour'] = dt.dt.hour

            if 'conversation_minute' not in df.columns:
                df['conversation_minute'] = dt.dt.minute

        # Calcular first_response_time_minutes a partir de seconds
        if 'first_response_time_seconds' in df.columns and 'first_response_time_minutes' not in df.columns:
            df['first_response_time_minutes'] = (
                pd.to_numeric(df['first_response_time_seconds'], errors='coerce') / 60.0
            ).round(1)

        # Calcular user_messages_count e contact_messages_count se não existirem
        if 'agent_messages' in df.columns and 'user_messages_count' not in df.columns:
            df['user_messages_count'] = df['agent_messages']

        if 'contact_messages' in df.columns and 'contact_messages_count' not in df.columns:
            df['contact_messages_count'] = df['contact_messages']

        # Flags calculadas
        if 'user_messages_count' in df.columns and 'has_user_messages' not in df.columns:
            df['has_user_messages'] = df['user_messages_count'] > 0

        if 'contact_messages_count' in df.columns and 'has_contact_messages' not in df.columns:
            df['has_contact_messages'] = df['contact_messages_count'] > 0

        if 'private_notes_count' in df.columns and 'has_private_notes' not in df.columns:
            df['has_private_notes'] = df['private_notes_count'] > 0

        if 'contact_messages_count' in df.columns and 'has_contact_reply' not in df.columns:
            df['has_contact_reply'] = df['contact_messages_count'] > 0

        # Calcular ratios
        if 'user_messages_count' in df.columns and 'total_messages' in df.columns:
            total = pd.to_numeric(df['total_messages'], errors='coerce').replace(0, np.nan)
            df['user_message_ratio'] = (
                pd.to_numeric(df['user_messages_count'], errors='coerce') / total
            ).fillna(0).round(2)

        if 'contact_messages_count' in df.columns and 'total_messages' in df.columns:
            total = pd.to_numeric(df['total_messages'], errors='coerce').replace(0, np.nan)
            df['contact_message_ratio'] = (
                pd.to_numeric(df['contact_messages_count'], errors='coerce') / total
            ).fillna(0).round(2)

        return df

    def get_column_mapping(self) -> Dict[str, str]:
        """
        Retorna mapeamento de colunas: remoto → local.

        Returns:
            Dicionário com mapeamento {coluna_local: coluna_remota}
        """
        return {
            # Identificadores
            'tenant_id': 'tenant_id',  # Adicionado pelo transformer
            'conversation_id': 'conversation_id',
            'display_id': 'display_id',
            'conversation_uuid': 'conversation_uuid',
            'account_id': 'account_id',
            'account_name': 'account_name',
            'inbox_id': 'inbox_id',
            'inbox_name': 'inbox_name',
            'inbox_channel_type': 'inbox_channel_type',
            'contact_id': 'contact_id',
            'contact_name': 'contact_name',
            'contact_email': 'contact_email',
            'contact_phone': 'contact_phone',
            'contact_identifier': 'contact_identifier',
            'assignee_id': 'assignee_id',
            'team_id': 'team_id',
            'campaign_id': 'campaign_id',

            # Timestamps
            'conversation_created_at': 'conversation_created_at',
            'conversation_updated_at': 'conversation_updated_at',
            'last_activity_at': 'last_activity_at',
            'first_reply_created_at': 'first_reply_created_at',
            'mc_first_message_at': 'mc_first_message_at',
            'mc_last_message_at': 'mc_last_message_at',
            'conversation_date': 'conversation_date',

            # Status
            'status': 'status',
            'status_label_pt': 'status_label',
            'priority': 'priority',
            'priority_label': 'priority_label',

            # Flags
            'is_resolved': 'is_resolved',
            'is_open': 'is_open',
            'is_pending': 'is_pending',
            'is_assigned': 'is_assigned',
            'has_team': 'has_team',
            'has_human_intervention': 'has_human_intervention',
            'is_bot_resolved': 'is_bot_resolved',

            # Métricas
            't_messages': 'total_messages',
            'user_messages_count': 'agent_messages',
            'contact_messages_count': 'contact_messages',
            'private_notes_count': 'private_notes_count',
            'first_response_time_seconds': 'first_response_time_seconds',
            'resolution_time_seconds': 'resolution_time_seconds',
            'conversation_duration_seconds': 'conversation_duration_seconds',

            # CSAT
            'csat_rating': 'csat_rating',
            'csat_feedback': 'csat_feedback',
            'csat_nps_category': 'csat_nps_category',

            # Mensagens
            'first_message_text': 'first_message_text',
            'last_message_text': 'last_message_text',
            'message_compiled': 'message_compiled',
        }


# Exemplo de uso
if __name__ == "__main__":
    import sys
    sys.path.append('/home/tester/projetos/allpfit-analytics')

    # Simular dados extraídos
    sample_data = {
        'conversation_id': [5804],
        'display_id': [20],
        'conversation_uuid': ['1f172c21-b133-4a81-9afb-92d1f8787351'],
        'account_id': [13],
        'inbox_id': [64],
        'contact_id': [5468],
        'assignee_id': [None],
        'conversation_created_at': ['2025-10-27 14:00:43'],
        'conversation_updated_at': ['2025-10-27 14:15:34'],
        'inbox_name': ['allpfitjpsulrecepcao'],
        'account_name': ['Allp Fit JP Sul'],
        'contact_name': ['558387906619'],
        'contact_phone': ['+558387906619'],
        'total_messages': [2.0],
        'agent_messages': [1.0],
        'contact_messages': [1.0],
        'status': [0],
        'status_label': ['Aberta'],
        'is_resolved': [False],
        'is_open': [True],
        'has_human_intervention': [True],
        'message_compiled': [[{'text': 'Test', 'sender': 'User'}]]
    }

    df = pd.DataFrame(sample_data)

    # Criar transformer
    transformer = ConversationTransformer(tenant_id=1)

    # Transformar dados
    logger.info("=" * 80)
    logger.info("TESTE: Transformando dados de exemplo")
    logger.info("=" * 80)

    df_transformed = transformer.transform_chunk(df)

    print("\nDados transformados:")
    print(f"Colunas: {list(df_transformed.columns)}")
    print(f"\nPrimeira linha:")
    for col in df_transformed.columns:
        print(f"  {col}: {df_transformed.iloc[0][col]}")

    # Verificar se tenant_id foi adicionado
    assert 'tenant_id' in df_transformed.columns
    assert df_transformed.iloc[0]['tenant_id'] == 1

    logger.info("Teste concluído com sucesso!")
