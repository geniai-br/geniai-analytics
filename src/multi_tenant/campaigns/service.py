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
            updates.append("promotional_context = :promotional_context::jsonb")
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
            updates.append("generation_metadata = :generation_metadata::jsonb")
            params["generation_metadata"] = str(generation_metadata).replace("'", '"')

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
                :file_size_bytes, :exported_by, :metadata::jsonb, :notes
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
                    "metadata": str(metadata).replace("'", '"'),
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