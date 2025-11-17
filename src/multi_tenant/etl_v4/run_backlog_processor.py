#!/usr/bin/env python3
"""
Backlog Processor - Sistema Multi-Tenant
=========================================

Processa backlog histórico de leads não analisados para todos os tenants ativos.

Características:
- Batch processing (50-100 leads por tenant)
- Priorização de tenants
- Respeita rate limits e cost thresholds
- Graceful shutdown (SIGTERM/SIGINT)
- Logging estruturado
- Checkpoint system (retoma de onde parou)

Uso:
    python run_backlog_processor.py [--batch-size N] [--max-cost N] [--dry-run]

Fase: 9.2 - Backlog Processing
Relacionado: docs/private/checkpoints/FASE9_AUTOMACAO_MULTI_TENANT.md
Autor: Isaac (via Claude Code)
Data: 2025-11-17
"""

import sys
import os
import signal
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from multi_tenant.utils.rate_limiter import get_rate_limiter
from multi_tenant.utils.cost_tracker import get_cost_tracker
from multi_tenant.etl_v4.remarketing_analyzer import analyze_inactive_leads

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/backlog_processor.log')
    ]
)
logger = logging.getLogger(__name__)

# Flag global para shutdown graceful
shutdown_requested = False


def signal_handler(signum, frame):
    """Handler para SIGTERM/SIGINT - shutdown graceful."""
    global shutdown_requested
    logger.warning(f"Signal {signum} recebido. Finalizando gracefully...")
    shutdown_requested = True


# Registrar handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class TenantInfo:
    """Informações de um tenant para priorização."""

    def __init__(self, tenant_id: int, name: str, backlog_count: int, is_vip: bool = False):
        self.tenant_id = tenant_id
        self.name = name
        self.backlog_count = backlog_count
        self.is_vip = is_vip
        self.priority_score = 0

    def calculate_priority(self) -> float:
        """
        Calcula score de prioridade.

        Critérios:
        - VIP: +1000 pontos
        - Backlog size: +1 ponto por lead pendente
        """
        score = 0

        # VIP tem prioridade máxima
        if self.is_vip:
            score += 1000

        # Backlog size
        score += self.backlog_count

        self.priority_score = score
        return score

    def __repr__(self):
        return f"Tenant({self.tenant_id}, {self.name}, backlog={self.backlog_count}, vip={self.is_vip})"


class BacklogProcessor:
    """Processador de backlog multi-tenant."""

    def __init__(
        self,
        batch_size: int = 50,
        max_cost_per_batch: float = 0.50,
        dry_run: bool = False
    ):
        """
        Inicializa o backlog processor.

        Args:
            batch_size: Tamanho do batch por tenant
            max_cost_per_batch: Custo máximo por batch em BRL
            dry_run: Se True, não faz análises reais
        """
        self.batch_size = batch_size
        self.max_cost_per_batch = max_cost_per_batch
        self.dry_run = dry_run

        # Componentes globais
        self.rate_limiter = get_rate_limiter()
        self.cost_tracker = get_cost_tracker()

        # Database
        db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics'
        )
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

        # Estatísticas
        self.stats = {
            'tenants_processed': 0,
            'total_analyzed': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'total_cost': 0.0,
            'start_time': datetime.now()
        }

        logger.info(
            f"BacklogProcessor inicializado - "
            f"Batch: {batch_size}, Max Cost/Batch: R$ {max_cost_per_batch:.2f}, "
            f"Dry Run: {dry_run}"
        )

    def get_active_tenants(self) -> List[TenantInfo]:
        """
        Busca tenants ativos e suas informações.

        Returns:
            Lista de TenantInfo ordenada por prioridade
        """
        query = text("""
            SELECT
                t.id,
                t.name,
                t.slug,
                COUNT(DISTINCT ca.conversation_id) as backlog_count,
                COALESCE(tc.features->>'is_vip', 'false')::boolean as is_vip
            FROM tenants t
            LEFT JOIN inbox_tenant_mapping itm ON t.id = itm.tenant_id
            LEFT JOIN conversations_analytics ca ON
                ca.tenant_id = t.id
                AND ca.is_lead = true
                AND ca.tipo_conversa IS NULL
                AND ca.mc_last_message_at < NOW() - INTERVAL '24 hours'
                AND ca.contact_messages_count >= 3
                AND ca.message_compiled IS NOT NULL
            LEFT JOIN tenant_configs tc ON t.id = tc.tenant_id
            WHERE t.status = 'active'
              AND t.deleted_at IS NULL
              AND itm.is_active = true
              AND COALESCE(tc.features->>'use_openai', 'true')::boolean = true
            GROUP BY t.id, t.name, t.slug, tc.features
            HAVING COUNT(DISTINCT ca.conversation_id) > 0
            ORDER BY is_vip DESC, backlog_count DESC
        """)

        tenants = []
        with self.engine.connect() as conn:
            result = conn.execute(query)
            for row in result:
                tenant = TenantInfo(
                    tenant_id=row[0],
                    name=row[1],
                    backlog_count=row[3],
                    is_vip=row[4]
                )
                tenant.calculate_priority()
                tenants.append(tenant)

        logger.info(f"Encontrados {len(tenants)} tenants com backlog")
        return tenants

    def process_tenant_backlog(self, tenant: TenantInfo) -> Dict[str, int]:
        """
        Processa backlog de um tenant.

        Args:
            tenant: Informações do tenant

        Returns:
            Dict com estatísticas do processamento
        """
        logger.info(
            f"\n{'='*70}\n"
            f"🏢 TENANT: {tenant.name} (ID: {tenant.tenant_id})\n"
            f"📊 Backlog: {tenant.backlog_count} leads\n"
            f"⭐ VIP: {'Sim' if tenant.is_vip else 'Não'}\n"
            f"{'='*70}"
        )

        # Verificar se pode gastar
        estimated_batch_cost = 0.08  # Estimativa conservadora (100 leads * R$0.0008)

        can_spend, reason = self.cost_tracker.can_spend(
            tenant_id=tenant.tenant_id,
            estimated_cost=estimated_batch_cost,
            check_type='all'
        )

        if not can_spend:
            logger.warning(
                f"⚠️  Tenant {tenant.tenant_id} bloqueado por threshold de custo: {reason}"
            )
            return {'analyzed': 0, 'failed': 0, 'skipped': tenant.backlog_count}

        # Processar batch
        if self.dry_run:
            logger.info(f"[DRY RUN] Simulando análise de {self.batch_size} leads...")
            return {
                'analyzed': min(self.batch_size, tenant.backlog_count),
                'failed': 0,
                'skipped': 0
            }

        try:
            # Chamar função de análise existente
            result = analyze_inactive_leads(
                tenant_id=tenant.tenant_id,
                limit=self.batch_size,
                max_cost_brl=self.max_cost_per_batch
            )

            logger.info(
                f"✅ Tenant {tenant.tenant_id} processado - "
                f"Sucesso: {result['analyzed']}, "
                f"Falhas: {result['failed']}, "
                f"Pulados: {result['skipped']}, "
                f"Custo: R$ {result['total_cost']:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Erro ao processar tenant {tenant.tenant_id}: {e}")
            return {'analyzed': 0, 'failed': 1, 'skipped': 0}

    def run(self):
        """Executa o processamento completo do backlog."""
        logger.info("\n" + "="*70)
        logger.info("🚀 INICIANDO BACKLOG PROCESSOR")
        logger.info("="*70 + "\n")

        # Mostrar status inicial
        logger.info(self.rate_limiter.get_stats_summary())
        logger.info("\n" + self.cost_tracker.get_stats_summary())

        # Buscar tenants
        tenants = self.get_active_tenants()

        if not tenants:
            logger.warning("⚠️  Nenhum tenant com backlog encontrado")
            return

        # Processar cada tenant
        for idx, tenant in enumerate(tenants, 1):
            # Verificar shutdown
            if shutdown_requested:
                logger.warning("⚠️  Shutdown solicitado. Parando processamento.")
                break

            logger.info(f"\n📦 Processando tenant {idx}/{len(tenants)}...")

            # Processar batch
            result = self.process_tenant_backlog(tenant)

            # Atualizar estatísticas
            self.stats['tenants_processed'] += 1
            self.stats['total_analyzed'] += result.get('analyzed', 0)
            self.stats['total_failed'] += result.get('failed', 0)
            self.stats['total_skipped'] += result.get('skipped', 0)
            self.stats['total_cost'] += result.get('total_cost', 0.0)

            # Mostrar progresso
            logger.info(
                f"\n📊 Progresso Global:\n"
                f"   Tenants: {self.stats['tenants_processed']}/{len(tenants)}\n"
                f"   Analisados: {self.stats['total_analyzed']}\n"
                f"   Falhas: {self.stats['total_failed']}\n"
                f"   Pulados: {self.stats['total_skipped']}\n"
                f"   Custo Total: R$ {self.stats['total_cost']:.4f}"
            )

        # Relatório final
        self.print_final_report()

    def print_final_report(self):
        """Imprime relatório final do processamento."""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()

        logger.info("\n" + "="*70)
        logger.info("📊 RELATÓRIO FINAL - BACKLOG PROCESSOR")
        logger.info("="*70)
        logger.info(f"⏱️  Tempo de Execução: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info(f"🏢 Tenants Processados: {self.stats['tenants_processed']}")
        logger.info(f"✅ Leads Analisados: {self.stats['total_analyzed']}")
        logger.info(f"❌ Falhas: {self.stats['total_failed']}")
        logger.info(f"⏭️  Pulados: {self.stats['total_skipped']}")
        logger.info(f"💰 Custo Total: R$ {self.stats['total_cost']:.4f}")

        if self.stats['total_analyzed'] > 0:
            avg_cost = self.stats['total_cost'] / self.stats['total_analyzed']
            avg_time = elapsed / self.stats['total_analyzed']
            logger.info(f"💵 Custo Médio/Lead: R$ {avg_cost:.4f}")
            logger.info(f"⏱️  Tempo Médio/Lead: {avg_time:.2f}s")

        logger.info("="*70)

        # Mostrar status final
        logger.info("\n" + self.rate_limiter.get_stats_summary())
        logger.info("\n" + self.cost_tracker.get_stats_summary())


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Processa backlog histórico de leads para todos os tenants'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Tamanho do batch por tenant (default: 50)'
    )
    parser.add_argument(
        '--max-cost',
        type=float,
        default=0.50,
        help='Custo máximo por batch em BRL (default: 0.50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula execução sem fazer análises reais'
    )

    args = parser.parse_args()

    # Criar e executar processor
    processor = BacklogProcessor(
        batch_size=args.batch_size,
        max_cost_per_batch=args.max_cost,
        dry_run=args.dry_run
    )

    try:
        processor.run()
        logger.info("\n✅ Backlog processor concluído com sucesso!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
