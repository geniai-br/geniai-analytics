"""
CampaignService - Serviço de Gerenciamento de Campanhas
=======================================================

Este serviço fornece todas as operações CRUD e de negócio para
campanhas de remarketing.

Funcionalidades:
    - CRUD de campanhas
    - Gerenciamento de leads
    - Importação de leads elegíveis
    - Atualização de métricas
    - Registro de exportações

Autor: Isaac (via Claude Code)
Data: 2025-11-26
"""

import json
import logging
import re
import unicodedata
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple


def remove_accents(text: str) -> str:
    """Remove acentos de uma string usando unicodedata"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import (
    Campaign,
    CampaignLead,
    CampaignExport,
    CampaignStatus,
    CampaignType,
    CampaignTone,
    LeadStatus,
)

# Configurar logging
logger = logging.getLogger(__name__)


class CampaignService:
    """
    Serviço para gerenciamento de campanhas de remarketing.

    Responsabilidades:
        - CRUD de campanhas
        - Gerenciamento de leads de campanha
        - Importação de leads elegíveis do conversations_analytics
        - Atualização de métricas
        - Registro de exportações CSV

    Uso:
        >>> service = CampaignService(engine, tenant_id=1)
        >>> campaign = service.create_campaign(
        ...     name="Black Friday",
        ...     template_text="Olá, {{1}}. Vi que {{2}}. Hoje {{3}}!",
        ...     promotional_context={"promocao": "40% off"},
        ...     start_date=date(2025, 11, 25),
        ...     end_date=date(2025, 11, 30)
        ... )
    """

    def __init__(self, engine: Engine, tenant_id: int):
        """
        Inicializa o serviço.

        Args:
            engine: Engine SQLAlchemy conectada ao banco geniai_analytics
            tenant_id: ID do tenant para isolamento de dados
        """
        self.engine = engine
        self.tenant_id = tenant_id
        logger.info(f"CampaignService inicializado para tenant {tenant_id}")

    def _set_tenant_context(self, conn) -> None:
        """Define contexto do tenant para RLS"""
        conn.execute(text(f"SET app.current_tenant_id = {self.tenant_id}"))
        conn.execute(text("SET app.current_user_role = 'admin'"))

    def _generate_slug(self, name: str) -> str:
        """
        Gera slug URL-friendly a partir do nome.

        Args:
            name: Nome da campanha

        Returns:
            Slug gerado (ex: "black-friday-2025")
        """
        # Remove acentos
        slug = remove_accents(name.lower())
        # Remove caracteres especiais
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Substitui espaços por hífens
        slug = re.sub(r'\s+', '-', slug)
        # Remove hífens duplicados
        slug = re.sub(r'-+', '-', slug)
        # Remove hífens no início e fim
        slug = slug.strip('-')
        return slug

    # =========================================================================
    # CRUD DE CAMPANHAS
    # =========================================================================

    def create_campaign(
        self,
        name: str,
        template_text: str,
        start_date: date,
        end_date: date,
        campaign_type: CampaignType = CampaignType.PROMOTIONAL,
        tone: CampaignTone = CampaignTone.PROFESSIONAL,
        briefing: Optional[str] = None,
        promotional_context: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        created_by: Optional[int] = None,
        status: CampaignStatus = CampaignStatus.DRAFT
    ) -> Campaign:
        """
        Cria uma nova campanha.

        Args:
            name: Nome da campanha
            template_text: Template com variáveis {{1}}, {{2}}, {{3}}
            start_date: Data de início
            end_date: Data de fim
            campaign_type: Tipo da campanha (promotional, reengagement, event, etc.)
            tone: Tom da mensagem (urgente, amigavel, profissional, etc.)
            briefing: Texto livre descrevendo objetivo/contexto da campanha
            promotional_context: Detalhes estruturados JSON (campos específicos por tipo)
            description: Descrição opcional
            created_by: ID do usuário criador
            status: Status inicial (default: draft)

        Returns:
            Campaign criada com ID preenchido

        Raises:
            ValueError: Se dados inválidos
            Exception: Se erro no banco
        """
        # Validações
        if not name or not name.strip():
            raise ValueError("Nome da campanha é obrigatório")
        if not template_text or "{{" not in template_text:
            raise ValueError("Template deve conter pelo menos uma variável {{N}}")
        if end_date < start_date:
            raise ValueError("Data de fim deve ser maior ou igual à data de início")

        # Gerar slug
        slug = self._generate_slug(name)

        # Contar variáveis no template
        variable_count = len(re.findall(r'\{\{\d+\}\}', template_text))

        # Garantir que promotional_context é dict
        if promotional_context is None:
            promotional_context = {}

        query = text("""
            INSERT INTO campaigns (
                tenant_id, name, slug, description,
                campaign_type, tone, briefing,
                template_text, template_variable_count,
                promotional_context, start_date, end_date,
                status, created_by
            ) VALUES (
                :tenant_id, :name, :slug, :description,
                :campaign_type, :tone, :briefing,
                :template_text, :variable_count,
                CAST(:promotional_context AS jsonb), :start_date, :end_date,
                :status, :created_by
            )
            RETURNING id, created_at, updated_at
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "tenant_id": self.tenant_id,
                    "name": name.strip(),
                    "slug": slug,
                    "description": description,
                    "campaign_type": str(campaign_type),
                    "tone": str(tone),
                    "briefing": briefing,
                    "template_text": template_text,
                    "variable_count": variable_count,
                    "promotional_context": json.dumps(promotional_context, ensure_ascii=False),
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": str(status),
                    "created_by": created_by
                })

                row = result.fetchone()
                conn.commit()

                campaign = Campaign(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    name=name.strip(),
                    slug=slug,
                    description=description,
                    campaign_type=campaign_type,
                    tone=tone,
                    briefing=briefing,
                    template_text=template_text,
                    template_variable_count=variable_count,
                    promotional_context=promotional_context,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    created_by=created_by,
                    created_at=row[1],
                    updated_at=row[2]
                )

                logger.info(f"Campanha criada: ID={campaign.id}, Nome='{campaign.name}', Tipo={campaign_type}")
                return campaign

        except Exception as e:
            logger.error(f"Erro ao criar campanha: {e}")
            raise

    def get_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """
        Busca uma campanha por ID.

        Args:
            campaign_id: ID da campanha

        Returns:
            Campaign se encontrada, None caso contrário
        """
        query = text("""
            SELECT
                id, tenant_id, name, slug, description,
                campaign_type, tone, briefing,
                template_text, template_variable_count,
                promotional_context, start_date, end_date,
                status, leads_total, leads_processed, leads_exported,
                total_cost_brl, last_export_at, last_export_count,
                created_at, updated_at, created_by
            FROM campaigns
            WHERE id = :campaign_id AND tenant_id = :tenant_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {
                    "campaign_id": campaign_id,
                    "tenant_id": self.tenant_id
                })
                row = result.fetchone()

                if not row:
                    return None

                return Campaign(
                    id=row[0],
                    tenant_id=row[1],
                    name=row[2],
                    slug=row[3],
                    description=row[4],
                    campaign_type=CampaignType(row[5]) if row[5] else CampaignType.PROMOTIONAL,
                    tone=CampaignTone(row[6]) if row[6] else CampaignTone.PROFESSIONAL,
                    briefing=row[7],
                    template_text=row[8],
                    template_variable_count=row[9],
                    promotional_context=row[10] or {},
                    start_date=row[11],
                    end_date=row[12],
                    status=CampaignStatus(row[13]),
                    leads_total=row[14] or 0,
                    leads_processed=row[15] or 0,
                    leads_exported=row[16] or 0,
                    total_cost_brl=float(row[17] or 0),
                    last_export_at=row[18],
                    last_export_count=row[19] or 0,
                    created_at=row[20],
                    updated_at=row[21],
                    created_by=row[22]
                )

        except Exception as e:
            logger.error(f"Erro ao buscar campanha {campaign_id}: {e}")
            raise

    def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        campaign_type: Optional[CampaignType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Campaign]:
        """
        Lista campanhas do tenant.

        Args:
            status: Filtrar por status (opcional)
            campaign_type: Filtrar por tipo de campanha (opcional)
            limit: Máximo de registros
            offset: Pular registros

        Returns:
            Lista de campanhas
        """
        query_base = """
            SELECT
                id, tenant_id, name, slug, description,
                campaign_type, tone, briefing,
                template_text, template_variable_count,
                promotional_context, start_date, end_date,
                status, leads_total, leads_processed, leads_exported,
                total_cost_brl, last_export_at, last_export_count,
                created_at, updated_at, created_by
            FROM campaigns
            WHERE tenant_id = :tenant_id
        """

        params = {"tenant_id": self.tenant_id, "limit": limit, "offset": offset}

        if status:
            query_base += " AND status = :status"
            params["status"] = str(status)

        if campaign_type:
            query_base += " AND campaign_type = :campaign_type"
            params["campaign_type"] = str(campaign_type)

        query_base += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(text(query_base), params)
                rows = result.fetchall()

                campaigns = []
                for row in rows:
                    campaigns.append(Campaign(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        slug=row[3],
                        description=row[4],
                        campaign_type=CampaignType(row[5]) if row[5] else CampaignType.PROMOTIONAL,
                        tone=CampaignTone(row[6]) if row[6] else CampaignTone.PROFESSIONAL,
                        briefing=row[7],
                        template_text=row[8],
                        template_variable_count=row[9],
                        promotional_context=row[10] or {},
                        start_date=row[11],
                        end_date=row[12],
                        status=CampaignStatus(row[13]),
                        leads_total=row[14] or 0,
                        leads_processed=row[15] or 0,
                        leads_exported=row[16] or 0,
                        total_cost_brl=float(row[17] or 0),
                        last_export_at=row[18],
                        last_export_count=row[19] or 0,
                        created_at=row[20],
                        updated_at=row[21],
                        created_by=row[22]
                    ))

                return campaigns

        except Exception as e:
            logger.error(f"Erro ao listar campanhas: {e}")
            raise

    def update_campaign(
        self,
        campaign_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        campaign_type: Optional[CampaignType] = None,
        tone: Optional[CampaignTone] = None,
        briefing: Optional[str] = None,
        template_text: Optional[str] = None,
        promotional_context: Optional[Dict[str, Any]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[CampaignStatus] = None
    ) -> Optional[Campaign]:
        """
        Atualiza uma campanha.

        Args:
            campaign_id: ID da campanha
            name: Novo nome (opcional)
            description: Nova descrição (opcional)
            campaign_type: Novo tipo de campanha (opcional)
            tone: Novo tom (opcional)
            briefing: Novo briefing (opcional)
            template_text: Novo template (opcional)
            promotional_context: Novo contexto (opcional)
            start_date: Nova data início (opcional)
            end_date: Nova data fim (opcional)
            status: Novo status (opcional)

        Returns:
            Campaign atualizada ou None se não encontrada
        """
        # Verificar se campanha existe
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None

        # Montar SET dinamicamente
        updates = []
        params = {"campaign_id": campaign_id, "tenant_id": self.tenant_id}

        if name is not None:
            updates.append("name = :name")
            updates.append("slug = :slug")
            params["name"] = name.strip()
            params["slug"] = self._generate_slug(name)

        if description is not None:
            updates.append("description = :description")
            params["description"] = description

        if campaign_type is not None:
            updates.append("campaign_type = :campaign_type")
            params["campaign_type"] = str(campaign_type)

        if tone is not None:
            updates.append("tone = :tone")
            params["tone"] = str(tone)

        if briefing is not None:
            updates.append("briefing = :briefing")
            params["briefing"] = briefing

        if template_text is not None:
            updates.append("template_text = :template_text")
            updates.append("template_variable_count = :variable_count")
            params["template_text"] = template_text
            params["variable_count"] = len(re.findall(r'\{\{\d+\}\}', template_text))

        if promotional_context is not None:
            updates.append("promotional_context = CAST(:promotional_context AS jsonb)")
            params["promotional_context"] = json.dumps(promotional_context, ensure_ascii=False)

        if start_date is not None:
            updates.append("start_date = :start_date")
            params["start_date"] = start_date

        if end_date is not None:
            updates.append("end_date = :end_date")
            params["end_date"] = end_date

        if status is not None:
            updates.append("status = :status")
            params["status"] = str(status)

        if not updates:
            return campaign  # Nada para atualizar

        query = text(f"""
            UPDATE campaigns
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = :campaign_id AND tenant_id = :tenant_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                conn.execute(query, params)
                conn.commit()

            logger.info(f"Campanha {campaign_id} atualizada")
            return self.get_campaign(campaign_id)

        except Exception as e:
            logger.error(f"Erro ao atualizar campanha {campaign_id}: {e}")
            raise

    def delete_campaign(self, campaign_id: int) -> bool:
        """
        Deleta uma campanha e seus leads.

        Args:
            campaign_id: ID da campanha

        Returns:
            True se deletada, False se não encontrada
        """
        query = text("""
            DELETE FROM campaigns
            WHERE id = :campaign_id AND tenant_id = :tenant_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {
                    "campaign_id": campaign_id,
                    "tenant_id": self.tenant_id
                })
                conn.commit()

                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Campanha {campaign_id} deletada")
                return deleted

        except Exception as e:
            logger.error(f"Erro ao deletar campanha {campaign_id}: {e}")
            raise

    # =========================================================================
    # GERENCIAMENTO DE LEADS
    # =========================================================================

    def import_eligible_leads(
        self,
        campaign_id: int,
        min_inactivity_hours: int = 24,
        limit: Optional[int] = None
    ) -> int:
        """
        Importa leads elegíveis do conversations_analytics para a campanha.

        Critérios de elegibilidade:
        - is_lead = true
        - tipo_conversa IS NOT NULL (já foi analisado)
        - mc_last_message_at < NOW() - INTERVAL 'X hours'
        - contact_phone IS NOT NULL
        - Não está já na campanha

        Args:
            campaign_id: ID da campanha
            min_inactivity_hours: Mínimo de horas de inatividade (default: 24)
            limit: Máximo de leads a importar (opcional)

        Returns:
            Quantidade de leads importados
        """
        # Verificar se campanha existe
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campanha {campaign_id} não encontrada")

        query = text("""
            INSERT INTO campaign_leads (
                campaign_id, conversation_id, contact_phone, contact_name, status
            )
            SELECT
                :campaign_id,
                ca.conversation_id,
                ca.contact_phone,
                COALESCE(ca.nome_mapeado_bot, ca.contact_name),
                'pending'
            FROM conversations_analytics ca
            WHERE ca.tenant_id = :tenant_id
              AND ca.is_lead = true
              AND ca.tipo_conversa IS NOT NULL
              AND ca.contact_phone IS NOT NULL
              AND ca.contact_phone != ''
              AND ca.mc_last_message_at < NOW() - INTERVAL ':hours hours'
              AND NOT EXISTS (
                  SELECT 1 FROM campaign_leads cl
                  WHERE cl.campaign_id = :campaign_id
                  AND cl.conversation_id = ca.conversation_id
              )
            ORDER BY ca.mc_last_message_at DESC
            {limit_clause}
        """.replace(":hours", str(min_inactivity_hours))
           .replace("{limit_clause}", f"LIMIT {limit}" if limit else ""))

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "campaign_id": campaign_id,
                    "tenant_id": self.tenant_id
                })

                imported_count = result.rowcount
                conn.commit()

                # Atualizar leads_total na campanha
                if imported_count > 0:
                    self._update_campaign_metrics(conn, campaign_id)
                    conn.commit()

                logger.info(f"Importados {imported_count} leads para campanha {campaign_id}")
                return imported_count

        except Exception as e:
            logger.error(f"Erro ao importar leads para campanha {campaign_id}: {e}")
            raise

    def get_campaign_leads(
        self,
        campaign_id: int,
        status: Optional[LeadStatus] = None,
        not_exported: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[CampaignLead]:
        """
        Lista leads de uma campanha.

        Args:
            campaign_id: ID da campanha
            status: Filtrar por status (opcional)
            not_exported: Se True, apenas leads não exportados
            limit: Máximo de registros
            offset: Pular registros

        Returns:
            Lista de CampaignLead
        """
        query_base = """
            SELECT
                id, campaign_id, conversation_id,
                contact_phone, contact_name,
                var1, var2, var3, message_preview,
                status, error_message, generation_metadata,
                export_count, last_exported_at,
                created_at, processed_at, updated_at
            FROM campaign_leads
            WHERE campaign_id = :campaign_id
        """

        params = {"campaign_id": campaign_id, "limit": limit, "offset": offset}

        if status:
            query_base += " AND status = :status"
            params["status"] = str(status)

        if not_exported:
            query_base += " AND export_count = 0"

        query_base += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(text(query_base), params)
                rows = result.fetchall()

                leads = []
                for row in rows:
                    leads.append(CampaignLead(
                        id=row[0],
                        campaign_id=row[1],
                        conversation_id=row[2],
                        contact_phone=row[3],
                        contact_name=row[4],
                        var1=row[5],
                        var2=row[6],
                        var3=row[7],
                        message_preview=row[8],
                        status=LeadStatus(row[9]),
                        error_message=row[10],
                        generation_metadata=row[11] or {},
                        export_count=row[12] or 0,
                        last_exported_at=row[13],
                        created_at=row[14],
                        processed_at=row[15],
                        updated_at=row[16]
                    ))

                return leads

        except Exception as e:
            logger.error(f"Erro ao listar leads da campanha {campaign_id}: {e}")
            raise

    def get_pending_leads(
        self,
        campaign_id: int,
        limit: int = 50
    ) -> List[CampaignLead]:
        """
        Busca leads pendentes de processamento.

        Args:
            campaign_id: ID da campanha
            limit: Máximo de leads

        Returns:
            Lista de leads com status 'pending'
        """
        return self.get_campaign_leads(
            campaign_id=campaign_id,
            status=LeadStatus.PENDING,
            limit=limit
        )

    def get_exportable_leads(
        self,
        campaign_id: int,
        only_not_exported: bool = True
    ) -> List[CampaignLead]:
        """
        Busca leads que podem ser exportados (processed ou exported).

        Args:
            campaign_id: ID da campanha
            only_not_exported: Se True, apenas leads nunca exportados

        Returns:
            Lista de leads exportáveis
        """
        query = """
            SELECT
                id, campaign_id, conversation_id,
                contact_phone, contact_name,
                var1, var2, var3, message_preview,
                status, error_message, generation_metadata,
                export_count, last_exported_at,
                created_at, processed_at, updated_at
            FROM campaign_leads
            WHERE campaign_id = :campaign_id
              AND status IN ('processed', 'exported')
        """

        if only_not_exported:
            query += " AND export_count = 0"

        query += " ORDER BY created_at"

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(text(query), {"campaign_id": campaign_id})
                rows = result.fetchall()

                leads = []
                for row in rows:
                    leads.append(CampaignLead(
                        id=row[0],
                        campaign_id=row[1],
                        conversation_id=row[2],
                        contact_phone=row[3],
                        contact_name=row[4],
                        var1=row[5],
                        var2=row[6],
                        var3=row[7],
                        message_preview=row[8],
                        status=LeadStatus(row[9]),
                        error_message=row[10],
                        generation_metadata=row[11] or {},
                        export_count=row[12] or 0,
                        last_exported_at=row[13],
                        created_at=row[14],
                        processed_at=row[15],
                        updated_at=row[16]
                    ))

                return leads

        except Exception as e:
            logger.error(f"Erro ao buscar leads exportáveis: {e}")
            raise

    def update_lead(
        self,
        lead_id: int,
        var1: Optional[str] = None,
        var2: Optional[str] = None,
        var3: Optional[str] = None,
        message_preview: Optional[str] = None,
        status: Optional[LeadStatus] = None,
        error_message: Optional[str] = None,
        generation_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atualiza um lead da campanha.

        Args:
            lead_id: ID do lead
            var1: Variável {{1}}
            var2: Variável {{2}}
            var3: Variável {{3}}
            message_preview: Preview da mensagem
            status: Novo status
            error_message: Mensagem de erro
            generation_metadata: Metadados da geração

        Returns:
            True se atualizado
        """
        updates = []
        params = {"lead_id": lead_id}

        if var1 is not None:
            updates.append("var1 = :var1")
            params["var1"] = var1

        if var2 is not None:
            updates.append("var2 = :var2")
            params["var2"] = var2

        if var3 is not None:
            updates.append("var3 = :var3")
            params["var3"] = var3

        if message_preview is not None:
            updates.append("message_preview = :message_preview")
            params["message_preview"] = message_preview

        if status is not None:
            updates.append("status = :status")
            params["status"] = str(status)
            if status == LeadStatus.PROCESSED:
                updates.append("processed_at = NOW()")

        if error_message is not None:
            updates.append("error_message = :error_message")
            params["error_message"] = error_message

        if generation_metadata is not None:
            updates.append("generation_metadata = CAST(:generation_metadata AS jsonb)")
            params["generation_metadata"] = json.dumps(generation_metadata)

        if not updates:
            return False

        query = text(f"""
            UPDATE campaign_leads
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = :lead_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, params)
                conn.commit()
                return result.rowcount > 0

        except Exception as e:
            logger.error(f"Erro ao atualizar lead {lead_id}: {e}")
            raise

    def mark_leads_as_exported(
        self,
        lead_ids: List[int],
        campaign_id: int
    ) -> int:
        """
        Marca leads como exportados.

        Args:
            lead_ids: Lista de IDs dos leads
            campaign_id: ID da campanha

        Returns:
            Quantidade de leads marcados
        """
        if not lead_ids:
            return 0

        query = text("""
            UPDATE campaign_leads
            SET
                status = 'exported',
                export_count = export_count + 1,
                last_exported_at = NOW(),
                updated_at = NOW()
            WHERE id = ANY(:lead_ids)
              AND campaign_id = :campaign_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {
                    "lead_ids": lead_ids,
                    "campaign_id": campaign_id
                })

                count = result.rowcount

                # Atualizar métricas da campanha
                self._update_campaign_metrics(conn, campaign_id)
                conn.commit()

                logger.info(f"Marcados {count} leads como exportados")
                return count

        except Exception as e:
            logger.error(f"Erro ao marcar leads como exportados: {e}")
            raise

    # =========================================================================
    # EXPORTAÇÕES
    # =========================================================================

    def register_export(
        self,
        campaign_id: int,
        file_name: str,
        leads_count: int,
        lead_ids: List[int],
        exported_by: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        notes: Optional[str] = None
    ) -> CampaignExport:
        """
        Registra uma exportação CSV.

        Args:
            campaign_id: ID da campanha
            file_name: Nome do arquivo
            leads_count: Quantidade de leads
            lead_ids: IDs dos leads exportados
            exported_by: ID do usuário
            file_size_bytes: Tamanho do arquivo
            notes: Notas

        Returns:
            CampaignExport criado
        """
        metadata = {
            "leads_ids": lead_ids,
            "format": "csv",
            "encoding": "utf-8"
        }

        query = text("""
            INSERT INTO campaign_exports (
                campaign_id, file_name, leads_count,
                file_size_bytes, exported_by, metadata, notes
            ) VALUES (
                :campaign_id, :file_name, :leads_count,
                :file_size_bytes, :exported_by, CAST(:metadata AS jsonb), :notes
            )
            RETURNING id, exported_at
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "campaign_id": campaign_id,
                    "file_name": file_name,
                    "leads_count": leads_count,
                    "file_size_bytes": file_size_bytes,
                    "exported_by": exported_by,
                    "metadata": json.dumps(metadata),
                    "notes": notes
                })

                row = result.fetchone()

                # Atualizar última exportação na campanha
                conn.execute(text("""
                    UPDATE campaigns
                    SET last_export_at = NOW(),
                        last_export_count = :leads_count,
                        updated_at = NOW()
                    WHERE id = :campaign_id
                """), {"campaign_id": campaign_id, "leads_count": leads_count})

                conn.commit()

                export = CampaignExport(
                    id=row[0],
                    campaign_id=campaign_id,
                    file_name=file_name,
                    leads_count=leads_count,
                    file_size_bytes=file_size_bytes,
                    exported_by=exported_by,
                    exported_at=row[1],
                    metadata=metadata,
                    notes=notes
                )

                logger.info(f"Exportação registrada: ID={export.id}, Arquivo='{file_name}'")
                return export

        except Exception as e:
            logger.error(f"Erro ao registrar exportação: {e}")
            raise

    def list_exports(self, campaign_id: int) -> List[CampaignExport]:
        """
        Lista exportações de uma campanha.

        Args:
            campaign_id: ID da campanha

        Returns:
            Lista de exportações ordenadas por data (mais recente primeiro)
        """
        query = text("""
            SELECT
                id, campaign_id, file_name, leads_count,
                file_size_bytes, exported_by, exported_at,
                metadata, notes
            FROM campaign_exports
            WHERE campaign_id = :campaign_id
            ORDER BY exported_at DESC
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {"campaign_id": campaign_id})
                rows = result.fetchall()

                exports = []
                for row in rows:
                    exports.append(CampaignExport(
                        id=row[0],
                        campaign_id=row[1],
                        file_name=row[2],
                        leads_count=row[3],
                        file_size_bytes=row[4],
                        exported_by=row[5],
                        exported_at=row[6],
                        metadata=row[7] or {},
                        notes=row[8]
                    ))

                return exports

        except Exception as e:
            logger.error(f"Erro ao listar exportações: {e}")
            raise

    # =========================================================================
    # MÉTRICAS E ESTATÍSTICAS
    # =========================================================================

    def _update_campaign_metrics(self, conn, campaign_id: int) -> None:
        """Atualiza métricas agregadas da campanha"""
        query = text("""
            UPDATE campaigns c
            SET
                leads_total = (
                    SELECT COUNT(*) FROM campaign_leads
                    WHERE campaign_id = :campaign_id
                ),
                leads_processed = (
                    SELECT COUNT(*) FROM campaign_leads
                    WHERE campaign_id = :campaign_id
                    AND status IN ('processed', 'exported')
                ),
                leads_exported = (
                    SELECT COUNT(*) FROM campaign_leads
                    WHERE campaign_id = :campaign_id
                    AND status = 'exported'
                ),
                total_cost_brl = (
                    SELECT COALESCE(SUM((generation_metadata->>'cost_brl')::numeric), 0)
                    FROM campaign_leads
                    WHERE campaign_id = :campaign_id
                    AND generation_metadata IS NOT NULL
                ),
                updated_at = NOW()
            WHERE id = :campaign_id
        """)

        conn.execute(query, {"campaign_id": campaign_id})

    def get_campaign_stats(self, campaign_id: int) -> Dict[str, Any]:
        """
        Retorna estatísticas detalhadas de uma campanha.

        Args:
            campaign_id: ID da campanha

        Returns:
            Dicionário com estatísticas
        """
        query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'processed') as processed,
                COUNT(*) FILTER (WHERE status = 'exported') as exported,
                COUNT(*) FILTER (WHERE status = 'error') as errors,
                COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
                COUNT(*) FILTER (WHERE export_count = 0 AND status IN ('processed', 'exported')) as not_exported,
                COALESCE(SUM((generation_metadata->>'cost_brl')::numeric), 0) as total_cost,
                COALESCE(SUM((generation_metadata->>'tokens_total')::integer), 0) as total_tokens
            FROM campaign_leads
            WHERE campaign_id = :campaign_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {"campaign_id": campaign_id})
                row = result.fetchone()

                return {
                    "total": row[0] or 0,
                    "pending": row[1] or 0,
                    "processing": row[2] or 0,
                    "processed": row[3] or 0,
                    "exported": row[4] or 0,
                    "errors": row[5] or 0,
                    "skipped": row[6] or 0,
                    "not_exported": row[7] or 0,
                    "total_cost_brl": float(row[8] or 0),
                    "total_tokens": row[9] or 0,
                    "exportable": (row[3] or 0) + (row[4] or 0),
                }

        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            raise

    def count_campaigns(self, status: Optional[CampaignStatus] = None) -> int:
        """
        Conta campanhas do tenant.

        Args:
            status: Filtrar por status (opcional)

        Returns:
            Quantidade de campanhas
        """
        query = "SELECT COUNT(*) FROM campaigns WHERE tenant_id = :tenant_id"
        params = {"tenant_id": self.tenant_id}

        if status:
            query += " AND status = :status"
            params["status"] = str(status)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(text(query), params)
                return result.scalar() or 0

        except Exception as e:
            logger.error(f"Erro ao contar campanhas: {e}")
            raise

    # =========================================================================
    # LEADS ELEGÍVEIS (conversations_analytics)
    # =========================================================================

    def get_eligible_leads(
        self,
        campaign_id: Optional[int] = None,
        min_score: int = 0,
        only_with_analysis: bool = True,
        only_remarketing: bool = False,
        exclude_already_in_campaign: bool = True,
        search_term: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Busca leads elegíveis da tabela conversations_analytics.

        Esta função busca leads que podem ser adicionados a campanhas,
        com filtros inteligentes baseados nos dados de análise de IA.

        Args:
            campaign_id: Se fornecido, exclui leads já na campanha
            min_score: Score mínimo de probabilidade (0-100)
            only_with_analysis: Se True, apenas leads com análise de IA
            only_remarketing: Se True, apenas leads marcados para remarketing
            exclude_already_in_campaign: Se True, exclui leads já em qualquer campanha ativa
            search_term: Termo de busca (nome ou telefone)
            limit: Máximo de registros
            offset: Pular registros

        Returns:
            Tupla (lista de leads, total count)
        """
        # Query base com dados relevantes para campanhas
        query_base = """
            SELECT
                ca.conversation_id,
                ca.contact_name,
                COALESCE(ca.nome_mapeado_bot, ca.contact_name) as nome_display,
                ca.contact_phone,
                ca.ai_probability_score,
                ca.ai_probability_label,
                ca.analise_ia,
                ca.sugestao_disparo,
                ca.dados_extraidos_ia,
                ca.precisa_remarketing,
                ca.nivel_interesse,
                ca.is_lead,
                ca.mc_last_message_at,
                ca.inbox_name
            FROM conversations_analytics ca
            WHERE ca.tenant_id = :tenant_id
              AND ca.is_lead = true
              AND ca.contact_phone IS NOT NULL
              AND ca.contact_phone != ''
        """

        count_query_base = """
            SELECT COUNT(*)
            FROM conversations_analytics ca
            WHERE ca.tenant_id = :tenant_id
              AND ca.is_lead = true
              AND ca.contact_phone IS NOT NULL
              AND ca.contact_phone != ''
        """

        params = {"tenant_id": self.tenant_id}

        # Filtro: apenas com análise de IA
        if only_with_analysis:
            filter_clause = " AND ca.analise_ia IS NOT NULL AND ca.analise_ia != ''"
            query_base += filter_clause
            count_query_base += filter_clause

        # Filtro: score mínimo
        if min_score > 0:
            filter_clause = " AND COALESCE(ca.ai_probability_score, 0) >= :min_score"
            query_base += filter_clause
            count_query_base += filter_clause
            params["min_score"] = min_score

        # Filtro: apenas remarketing
        if only_remarketing:
            filter_clause = " AND ca.precisa_remarketing = true"
            query_base += filter_clause
            count_query_base += filter_clause

        # Filtro: excluir leads já em campanha específica
        if campaign_id and exclude_already_in_campaign:
            filter_clause = """
                AND NOT EXISTS (
                    SELECT 1 FROM campaign_leads cl
                    WHERE cl.conversation_id = ca.conversation_id
                    AND cl.campaign_id = :campaign_id
                )
            """
            query_base += filter_clause
            count_query_base += filter_clause
            params["campaign_id"] = campaign_id

        # Filtro: busca por termo (nome ou telefone)
        if search_term and search_term.strip():
            filter_clause = """
                AND (
                    LOWER(ca.contact_name) LIKE LOWER(:search_term)
                    OR LOWER(ca.nome_mapeado_bot) LIKE LOWER(:search_term)
                    OR ca.contact_phone LIKE :search_term
                )
            """
            query_base += filter_clause
            count_query_base += filter_clause
            params["search_term"] = f"%{search_term.strip()}%"

        # Ordenação e paginação
        query_base += """
            ORDER BY ca.ai_probability_score DESC NULLS LAST, ca.mc_last_message_at DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                # Buscar total
                count_result = conn.execute(text(count_query_base), params)
                total_count = count_result.scalar() or 0

                # Buscar leads
                result = conn.execute(text(query_base), params)
                rows = result.fetchall()

                leads = []
                for row in rows:
                    # Extrair dados do JSON se disponível
                    dados_ia = row[8] or {}
                    if isinstance(dados_ia, str):
                        try:
                            dados_ia = json.loads(dados_ia)
                        except:
                            dados_ia = {}

                    leads.append({
                        "conversation_id": row[0],
                        "contact_name": row[1],
                        "nome_display": row[2] or row[1] or "Sem nome",
                        "contact_phone": row[3],
                        "ai_probability_score": float(row[4] or 0),
                        "ai_probability_label": row[5] or "N/A",
                        "analise_ia": row[6],
                        "sugestao_disparo": row[7],
                        "dados_extraidos_ia": dados_ia,
                        "precisa_remarketing": row[9],
                        "nivel_interesse": row[10],
                        "is_lead": row[11],
                        "last_message_at": row[12],
                        "inbox_name": row[13],
                        # Extrair campos úteis do JSON
                        "interesse": dados_ia.get("interesse_mencionado", ""),
                        "objecoes": dados_ia.get("objecoes", []),
                        "urgencia": dados_ia.get("urgencia", ""),
                    })

                logger.info(f"Encontrados {len(leads)} leads elegíveis (total: {total_count})")
                return leads, total_count

        except Exception as e:
            logger.error(f"Erro ao buscar leads elegíveis: {e}")
            raise

    def add_leads_to_campaign(
        self,
        campaign_id: int,
        conversation_ids: List[int]
    ) -> int:
        """
        Adiciona múltiplos leads a uma campanha.

        Args:
            campaign_id: ID da campanha
            conversation_ids: Lista de IDs de conversas

        Returns:
            Quantidade de leads adicionados
        """
        if not conversation_ids:
            return 0

        # Verificar se campanha existe
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campanha {campaign_id} não encontrada")

        query = text("""
            INSERT INTO campaign_leads (
                campaign_id, conversation_id, contact_phone, contact_name, status
            )
            SELECT
                :campaign_id,
                ca.conversation_id,
                ca.contact_phone,
                COALESCE(ca.nome_mapeado_bot, ca.contact_name),
                'pending'
            FROM conversations_analytics ca
            WHERE ca.tenant_id = :tenant_id
              AND ca.conversation_id = ANY(:conversation_ids)
              AND NOT EXISTS (
                  SELECT 1 FROM campaign_leads cl
                  WHERE cl.campaign_id = :campaign_id
                  AND cl.conversation_id = ca.conversation_id
              )
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "campaign_id": campaign_id,
                    "tenant_id": self.tenant_id,
                    "conversation_ids": conversation_ids
                })

                added_count = result.rowcount

                # Atualizar métricas
                if added_count > 0:
                    self._update_campaign_metrics(conn, campaign_id)

                conn.commit()

                logger.info(f"Adicionados {added_count} leads à campanha {campaign_id}")
                return added_count

        except Exception as e:
            logger.error(f"Erro ao adicionar leads à campanha: {e}")
            raise

    def remove_lead_from_campaign(
        self,
        campaign_id: int,
        lead_id: int
    ) -> bool:
        """
        Remove um lead de uma campanha.

        Args:
            campaign_id: ID da campanha
            lead_id: ID do lead na campaign_leads

        Returns:
            True se removido
        """
        query = text("""
            DELETE FROM campaign_leads
            WHERE id = :lead_id AND campaign_id = :campaign_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "lead_id": lead_id,
                    "campaign_id": campaign_id
                })

                removed = result.rowcount > 0

                if removed:
                    self._update_campaign_metrics(conn, campaign_id)

                conn.commit()

                if removed:
                    logger.info(f"Lead {lead_id} removido da campanha {campaign_id}")

                return removed

        except Exception as e:
            logger.error(f"Erro ao remover lead: {e}")
            raise

    def get_lead_details(
        self,
        conversation_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Busca detalhes completos de um lead para preview.

        Args:
            conversation_id: ID da conversa

        Returns:
            Dicionário com todos os dados do lead
        """
        query = text("""
            SELECT
                ca.conversation_id,
                ca.display_id,
                ca.contact_name,
                COALESCE(ca.nome_mapeado_bot, ca.contact_name) as nome_display,
                ca.contact_phone,
                ca.contact_email,
                ca.ai_probability_score,
                ca.ai_probability_label,
                ca.analise_ia,
                ca.sugestao_disparo,
                ca.dados_extraidos_ia,
                ca.metadados_analise_ia,
                ca.precisa_remarketing,
                ca.nivel_interesse,
                ca.mc_last_message_at,
                ca.mc_first_message_at,
                ca.inbox_name,
                ca.status,
                ca.tipo_conversa,
                ca.total_messages
            FROM conversations_analytics ca
            WHERE ca.tenant_id = :tenant_id
              AND ca.conversation_id = :conversation_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {
                    "tenant_id": self.tenant_id,
                    "conversation_id": conversation_id
                })

                row = result.fetchone()
                if not row:
                    return None

                # Processar JSON
                dados_ia = row[10] or {}
                if isinstance(dados_ia, str):
                    try:
                        dados_ia = json.loads(dados_ia)
                    except:
                        dados_ia = {}

                metadados = row[11] or {}
                if isinstance(metadados, str):
                    try:
                        metadados = json.loads(metadados)
                    except:
                        metadados = {}

                return {
                    "conversation_id": row[0],
                    "display_id": row[1],
                    "contact_name": row[2],
                    "nome_display": row[3] or row[2] or "Sem nome",
                    "contact_phone": row[4],
                    "contact_email": row[5],
                    "ai_probability_score": float(row[6] or 0),
                    "ai_probability_label": row[7] or "N/A",
                    "analise_ia": row[8],
                    "sugestao_disparo": row[9],
                    "dados_extraidos_ia": dados_ia,
                    "metadados_analise_ia": metadados,
                    "precisa_remarketing": row[12],
                    "nivel_interesse": row[13],
                    "last_message_at": row[14],
                    "first_message_at": row[15],
                    "inbox_name": row[16],
                    "status": row[17],
                    "tipo_conversa": row[18],
                    "total_messages": row[19],
                    # Campos extraídos do JSON
                    "interesse": dados_ia.get("interesse_mencionado", ""),
                    "objecoes": dados_ia.get("objecoes", []),
                    "urgencia": dados_ia.get("urgencia", ""),
                    "contexto_relevante": dados_ia.get("contexto_relevante", ""),
                }

        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do lead: {e}")
            raise

    def reset_error_leads(self, campaign_id: int) -> int:
        """
        Reseta leads com erro para status pending, permitindo reprocessamento.

        Args:
            campaign_id: ID da campanha

        Returns:
            Quantidade de leads resetados
        """
        query = text("""
            UPDATE campaign_leads
            SET
                status = 'pending',
                error_message = NULL,
                processed_at = NULL
            WHERE campaign_id = :campaign_id
              AND status = 'error'
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)

                result = conn.execute(query, {"campaign_id": campaign_id})
                reset_count = result.rowcount

                conn.commit()

                if reset_count > 0:
                    logger.info(f"Resetados {reset_count} leads com erro da campanha {campaign_id}")

                return reset_count

        except Exception as e:
            logger.error(f"Erro ao resetar leads com erro: {e}")
            raise

    def _update_campaign_cost(self, campaign_id: int, additional_cost: float) -> None:
        """
        Atualiza o custo total da campanha somando um valor adicional.

        Args:
            campaign_id: ID da campanha
            additional_cost: Custo adicional a ser somado (em BRL)
        """
        query = text("""
            UPDATE campaigns
            SET
                total_cost_brl = COALESCE(total_cost_brl, 0) + :additional_cost,
                updated_at = NOW()
            WHERE id = :campaign_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                conn.execute(query, {
                    "campaign_id": campaign_id,
                    "additional_cost": additional_cost
                })
                conn.commit()

                logger.debug(f"Atualizado custo da campanha {campaign_id}: +R$ {additional_cost:.3f}")

        except Exception as e:
            logger.error(f"Erro ao atualizar custo da campanha: {e}")

    # =========================================================================
    # CICLO DE VIDA DOS LEADS - RESET E REGENERAÇÃO
    # =========================================================================

    def reset_lead_status(
        self,
        lead_id: int,
        new_status: LeadStatus = LeadStatus.PROCESSED,
        clear_variables: bool = False,
        reason: Optional[str] = None
    ) -> bool:
        """
        Reseta o status de um lead, permitindo re-exportação ou reprocessamento.

        Casos de uso:
        - Lead exportado precisa ser re-exportado (exported → processed)
        - Lead exportado precisa novas variáveis (exported → pending, clear_variables=True)
        - Lead processado precisa novas variáveis (processed → pending, clear_variables=True)

        Args:
            lead_id: ID do lead
            new_status: Novo status (PENDING, PROCESSED ou EXPORTED)
            clear_variables: Se True, limpa var1, var2, var3 e message_preview
            reason: Motivo do reset (salvo em generation_metadata.reset_history)

        Returns:
            True se atualizado com sucesso
        """
        # Validar status permitidos para reset
        allowed_statuses = [LeadStatus.PENDING, LeadStatus.PROCESSED, LeadStatus.EXPORTED]
        if new_status not in allowed_statuses:
            raise ValueError(f"Status {new_status} não é permitido para reset. Use: {allowed_statuses}")

        # Buscar lead atual para salvar histórico
        current_lead = self._get_lead_by_id(lead_id)
        if not current_lead:
            return False

        # Montar update
        updates = ["status = :new_status", "updated_at = NOW()"]
        params = {"lead_id": lead_id, "new_status": str(new_status)}

        # Se voltando para PENDING, resetar processed_at
        if new_status == LeadStatus.PENDING:
            updates.append("processed_at = NULL")

        # Se clear_variables, limpar as variáveis mas salvar histórico
        if clear_variables:
            updates.extend([
                "var1 = NULL",
                "var2 = NULL",
                "var3 = NULL",
                "message_preview = NULL"
            ])

        # Salvar histórico no metadata
        current_metadata = current_lead.get('generation_metadata') or {}
        reset_history = current_metadata.get('reset_history', [])
        reset_history.append({
            "from_status": current_lead.get('status'),
            "to_status": str(new_status),
            "cleared_variables": clear_variables,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "previous_vars": {
                "var1": current_lead.get('var1'),
                "var2": current_lead.get('var2'),
                "var3": current_lead.get('var3')
            } if clear_variables else None
        })
        current_metadata['reset_history'] = reset_history

        updates.append("generation_metadata = CAST(:metadata AS jsonb)")
        params["metadata"] = json.dumps(current_metadata)

        query = text(f"""
            UPDATE campaign_leads
            SET {', '.join(updates)}
            WHERE id = :lead_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, params)
                conn.commit()

                if result.rowcount > 0:
                    logger.info(f"Lead {lead_id} resetado: {current_lead.get('status')} → {new_status}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Erro ao resetar lead {lead_id}: {e}")
            raise

    def _get_lead_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Busca lead por ID para operações internas"""
        query = text("""
            SELECT id, status, var1, var2, var3, generation_metadata
            FROM campaign_leads
            WHERE id = :lead_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {"lead_id": lead_id})
                row = result.fetchone()

                if not row:
                    return None

                return {
                    "id": row[0],
                    "status": row[1],
                    "var1": row[2],
                    "var2": row[3],
                    "var3": row[4],
                    "generation_metadata": row[5]
                }

        except Exception as e:
            logger.error(f"Erro ao buscar lead {lead_id}: {e}")
            return None

    def reset_leads_batch(
        self,
        lead_ids: List[int],
        campaign_id: int,
        new_status: LeadStatus = LeadStatus.PROCESSED,
        clear_variables: bool = False,
        reason: Optional[str] = None
    ) -> int:
        """
        Reseta múltiplos leads em lote.

        Args:
            lead_ids: Lista de IDs dos leads
            campaign_id: ID da campanha (para validação)
            new_status: Novo status
            clear_variables: Se True, limpa variáveis
            reason: Motivo do reset

        Returns:
            Quantidade de leads resetados
        """
        if not lead_ids:
            return 0

        # Validar status
        allowed_statuses = [LeadStatus.PENDING, LeadStatus.PROCESSED, LeadStatus.EXPORTED]
        if new_status not in allowed_statuses:
            raise ValueError(f"Status {new_status} não é permitido para reset")

        updates = ["status = :new_status", "updated_at = NOW()"]
        params = {
            "lead_ids": lead_ids,
            "campaign_id": campaign_id,
            "new_status": str(new_status)
        }

        if new_status == LeadStatus.PENDING:
            updates.append("processed_at = NULL")

        if clear_variables:
            updates.extend([
                "var1 = NULL",
                "var2 = NULL",
                "var3 = NULL",
                "message_preview = NULL"
            ])

        query = text(f"""
            UPDATE campaign_leads
            SET {', '.join(updates)}
            WHERE id = ANY(:lead_ids)
              AND campaign_id = :campaign_id
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, params)

                reset_count = result.rowcount

                # Atualizar métricas da campanha
                if reset_count > 0:
                    self._update_campaign_metrics(conn, campaign_id)

                conn.commit()

                logger.info(f"Resetados {reset_count} leads para status {new_status}")
                return reset_count

        except Exception as e:
            logger.error(f"Erro ao resetar leads em lote: {e}")
            raise

    def mark_leads_for_regeneration(
        self,
        lead_ids: List[int],
        campaign_id: int,
        keep_history: bool = True
    ) -> int:
        """
        Marca leads para regeneração de variáveis (volta para PENDING).

        Diferente de reset_leads_batch, este método:
        - Sempre volta para PENDING
        - Sempre limpa variáveis
        - Opcionalmente mantém histórico das variáveis anteriores

        Args:
            lead_ids: Lista de IDs dos leads
            campaign_id: ID da campanha
            keep_history: Se True, salva variáveis anteriores no metadata

        Returns:
            Quantidade de leads marcados para regeneração
        """
        if not lead_ids:
            return 0

        if keep_history:
            # Precisamos buscar as variáveis atuais antes de limpar
            # Fazer um por um para manter o histórico
            count = 0
            for lead_id in lead_ids:
                success = self.reset_lead_status(
                    lead_id=lead_id,
                    new_status=LeadStatus.PENDING,
                    clear_variables=True,
                    reason="Marcado para regeneração de variáveis"
                )
                if success:
                    count += 1
            return count
        else:
            # Pode fazer em batch sem histórico
            return self.reset_leads_batch(
                lead_ids=lead_ids,
                campaign_id=campaign_id,
                new_status=LeadStatus.PENDING,
                clear_variables=True,
                reason="Regeneração em lote"
            )

    def get_lead_history(self, lead_id: int) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de resets de um lead.

        Args:
            lead_id: ID do lead

        Returns:
            Lista de eventos de reset (do mais recente ao mais antigo)
        """
        lead = self._get_lead_by_id(lead_id)
        if not lead:
            return []

        metadata = lead.get('generation_metadata') or {}
        history = metadata.get('reset_history', [])

        # Retornar do mais recente ao mais antigo
        return list(reversed(history))

    def get_exported_leads_summary(self, campaign_id: int) -> Dict[str, Any]:
        """
        Retorna resumo dos leads exportados de uma campanha.

        Args:
            campaign_id: ID da campanha

        Returns:
            Dicionário com estatísticas de exportação
        """
        query = text("""
            SELECT
                COUNT(*) as total_exported,
                COUNT(*) FILTER (WHERE export_count = 1) as exported_once,
                COUNT(*) FILTER (WHERE export_count > 1) as exported_multiple,
                MAX(export_count) as max_exports,
                MIN(last_exported_at) as first_export,
                MAX(last_exported_at) as last_export
            FROM campaign_leads
            WHERE campaign_id = :campaign_id
              AND status = 'exported'
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {"campaign_id": campaign_id})
                row = result.fetchone()

                return {
                    "total_exported": row[0] or 0,
                    "exported_once": row[1] or 0,
                    "exported_multiple": row[2] or 0,
                    "max_exports": row[3] or 0,
                    "first_export": row[4],
                    "last_export": row[5]
                }

        except Exception as e:
            logger.error(f"Erro ao buscar resumo de exportados: {e}")
            return {}

    def get_export_history(self, campaign_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retorna histórico de exportações de uma campanha.

        Args:
            campaign_id: ID da campanha
            limit: Número máximo de exportações a retornar

        Returns:
            Lista de exportações com detalhes
        """
        query = text("""
            SELECT
                id,
                exported_at,
                exported_by,
                leads_count,
                file_name,
                metadata
            FROM campaign_exports
            WHERE campaign_id = :campaign_id
            ORDER BY exported_at DESC
            LIMIT :limit
        """)

        try:
            with self.engine.connect() as conn:
                self._set_tenant_context(conn)
                result = conn.execute(query, {"campaign_id": campaign_id, "limit": limit})

                exports = []
                for row in result.fetchall():
                    exports.append({
                        "id": row[0],
                        "exported_at": row[1],
                        "exported_by": row[2],
                        "total_leads": row[3],
                        "filename": row[4],
                        "metadata": row[5] if row[5] else {}
                    })

                return exports

        except Exception as e:
            logger.error(f"Erro ao buscar histórico de exportações: {e}")
            return []