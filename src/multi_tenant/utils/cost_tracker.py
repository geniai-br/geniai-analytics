"""
Cost Tracker - Sistema de Análise Multi-Tenant
==============================================

Rastreia e agrega custos de análise OpenAI por tenant, dia e mês.

Funcionalidades:
- Agregação diária e mensal
- Alertas de threshold
- Projeção de custos
- Relatórios formatados
- Persistência em arquivo

Fase: 9.1 - Cost Management Foundation
Relacionado: docs/private/checkpoints/FASE9_AUTOMACAO_MULTI_TENANT.md
Autor: Isaac (via Claude Code)
Data: 2025-11-17
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from threading import RLock

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CostTracker:
    """
    Rastreador de custos OpenAI com agregação temporal e por tenant.

    Persiste dados em arquivo JSON para análise histórica.
    Thread-safe para uso em ambientes paralelos.
    """

    # Thresholds padrão (em BRL)
    DEFAULT_DAILY_THRESHOLD = 10.00      # R$ 10/dia
    DEFAULT_MONTHLY_THRESHOLD = 200.00   # R$ 200/mês
    DEFAULT_TENANT_MONTHLY_THRESHOLD = 50.00  # R$ 50/tenant/mês

    # Arquivo de persistência
    STATE_FILE = '/tmp/geniai_cost_tracker.json'

    def __init__(
        self,
        daily_threshold: float = DEFAULT_DAILY_THRESHOLD,
        monthly_threshold: float = DEFAULT_MONTHLY_THRESHOLD,
        tenant_monthly_threshold: float = DEFAULT_TENANT_MONTHLY_THRESHOLD,
        state_file: Optional[str] = None
    ):
        """
        Inicializa o cost tracker.

        Args:
            daily_threshold: Limite diário em BRL
            monthly_threshold: Limite mensal global em BRL
            tenant_monthly_threshold: Limite mensal por tenant em BRL
            state_file: Caminho para arquivo de estado (opcional)
        """
        self.daily_threshold = daily_threshold
        self.monthly_threshold = monthly_threshold
        self.tenant_monthly_threshold = tenant_monthly_threshold
        self.state_file = state_file or self.STATE_FILE

        # Thread-safe lock
        self._lock = RLock()  # Reentrant para evitar deadlock

        # Estado interno
        # Estrutura: {
        #   'costs': [
        #       {
        #           'timestamp': float,
        #           'date': 'YYYY-MM-DD',
        #           'tenant_id': int,
        #           'cost_brl': float,
        #           'tokens': int,
        #           'requests': int
        #       },
        #       ...
        #   ],
        #   'alerts_sent': []  # histórico de alertas
        # }
        self._state = {
            'costs': [],
            'alerts_sent': []
        }

        # Carregar estado persistido
        self._load_state()

        logger.info(
            f"CostTracker inicializado - "
            f"Daily: R$ {daily_threshold:.2f}, "
            f"Monthly: R$ {monthly_threshold:.2f}, "
            f"Tenant/Month: R$ {tenant_monthly_threshold:.2f}"
        )

    def _load_state(self) -> None:
        """Carrega estado do arquivo se existir."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    saved_state = json.load(f)

                    # Limpar registros muito antigos (> 90 dias)
                    cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                    saved_state['costs'] = [
                        cost for cost in saved_state.get('costs', [])
                        if cost.get('date', '9999-99-99') >= cutoff_date
                    ]

                    self._state.update(saved_state)
                    logger.info(f"Estado carregado: {len(self._state['costs'])} registros")
            except Exception as e:
                logger.warning(f"Erro ao carregar estado: {e}. Iniciando do zero.")

    def _save_state(self) -> None:
        """Persiste estado em arquivo."""
        try:
            # Criar diretório se não existir
            Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")

    def record_cost(
        self,
        tenant_id: int,
        cost_brl: float,
        tokens: int,
        requests: int = 1
    ) -> None:
        """
        Registra um custo de análise.

        Args:
            tenant_id: ID do tenant
            cost_brl: Custo em reais
            tokens: Tokens consumidos
            requests: Número de requisições (default: 1)
        """
        with self._lock:
            now = datetime.now()

            record = {
                'timestamp': now.timestamp(),
                'date': now.strftime('%Y-%m-%d'),
                'tenant_id': tenant_id,
                'cost_brl': round(cost_brl, 4),
                'tokens': tokens,
                'requests': requests
            }

            self._state['costs'].append(record)
            self._save_state()

            # Verificar thresholds e alertar se necessário
            self._check_thresholds(tenant_id)

            logger.debug(
                f"Custo registrado - Tenant {tenant_id}: "
                f"R$ {cost_brl:.4f}, {tokens} tokens"
            )

    def _check_thresholds(self, tenant_id: int) -> None:
        """
        Verifica se algum threshold foi ultrapassado e emite alertas.

        Args:
            tenant_id: ID do tenant que gerou o custo
        """
        # Calcular custos atuais
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')

        daily_cost = self.get_daily_cost(today)
        monthly_cost = self.get_monthly_cost(month)
        tenant_monthly_cost = self.get_tenant_monthly_cost(tenant_id, month)

        # Verificar threshold diário
        if daily_cost >= self.daily_threshold:
            alert_key = f"daily_{today}"
            if alert_key not in self._state['alerts_sent']:
                logger.warning(
                    f"⚠️  DAILY COST THRESHOLD EXCEEDED: "
                    f"R$ {daily_cost:.2f} / R$ {self.daily_threshold:.2f}"
                )
                self._state['alerts_sent'].append(alert_key)
                self._save_state()

        # Verificar threshold mensal global
        if monthly_cost >= self.monthly_threshold:
            alert_key = f"monthly_{month}"
            if alert_key not in self._state['alerts_sent']:
                logger.warning(
                    f"⚠️  MONTHLY COST THRESHOLD EXCEEDED: "
                    f"R$ {monthly_cost:.2f} / R$ {self.monthly_threshold:.2f}"
                )
                self._state['alerts_sent'].append(alert_key)
                self._save_state()

        # Verificar threshold mensal por tenant
        if tenant_monthly_cost >= self.tenant_monthly_threshold:
            alert_key = f"tenant_{tenant_id}_{month}"
            if alert_key not in self._state['alerts_sent']:
                logger.warning(
                    f"⚠️  TENANT MONTHLY COST THRESHOLD EXCEEDED (Tenant {tenant_id}): "
                    f"R$ {tenant_monthly_cost:.2f} / R$ {self.tenant_monthly_threshold:.2f}"
                )
                self._state['alerts_sent'].append(alert_key)
                self._save_state()

    def get_daily_cost(self, date: Optional[str] = None) -> float:
        """
        Retorna custo total de um dia.

        Args:
            date: Data no formato YYYY-MM-DD (default: hoje)

        Returns:
            Custo total em BRL
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        with self._lock:
            return sum(
                cost['cost_brl'] for cost in self._state['costs']
                if cost['date'] == date
            )

    def get_monthly_cost(self, month: Optional[str] = None) -> float:
        """
        Retorna custo total de um mês.

        Args:
            month: Mês no formato YYYY-MM (default: mês atual)

        Returns:
            Custo total em BRL
        """
        if month is None:
            month = datetime.now().strftime('%Y-%m')

        with self._lock:
            return sum(
                cost['cost_brl'] for cost in self._state['costs']
                if cost['date'].startswith(month)
            )

    def get_tenant_monthly_cost(
        self,
        tenant_id: int,
        month: Optional[str] = None
    ) -> float:
        """
        Retorna custo mensal de um tenant específico.

        Args:
            tenant_id: ID do tenant
            month: Mês no formato YYYY-MM (default: mês atual)

        Returns:
            Custo total em BRL
        """
        if month is None:
            month = datetime.now().strftime('%Y-%m')

        with self._lock:
            return sum(
                cost['cost_brl'] for cost in self._state['costs']
                if cost['date'].startswith(month) and cost['tenant_id'] == tenant_id
            )

    def get_tenant_costs_breakdown(self, month: Optional[str] = None) -> Dict[int, float]:
        """
        Retorna breakdown de custos por tenant para um mês.

        Args:
            month: Mês no formato YYYY-MM (default: mês atual)

        Returns:
            Dict {tenant_id: custo_brl}
        """
        if month is None:
            month = datetime.now().strftime('%Y-%m')

        with self._lock:
            costs_by_tenant = defaultdict(float)

            for cost in self._state['costs']:
                if cost['date'].startswith(month):
                    costs_by_tenant[cost['tenant_id']] += cost['cost_brl']

            return dict(costs_by_tenant)

    def get_daily_projection(self) -> float:
        """
        Projeta custo do dia baseado na taxa atual.

        Returns:
            Custo projetado para o dia completo
        """
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        hours_elapsed = now.hour + now.minute / 60

        if hours_elapsed < 1:
            return 0.0

        current_cost = self.get_daily_cost(today)
        hourly_rate = current_cost / hours_elapsed
        projected_cost = hourly_rate * 24

        return projected_cost

    def get_monthly_projection(self) -> float:
        """
        Projeta custo do mês baseado na taxa atual.

        Returns:
            Custo projetado para o mês completo
        """
        now = datetime.now()
        month = now.strftime('%Y-%m')
        day_of_month = now.day
        days_in_month = 30  # Aproximação

        if day_of_month < 1:
            return 0.0

        current_cost = self.get_monthly_cost(month)
        daily_rate = current_cost / day_of_month
        projected_cost = daily_rate * days_in_month

        return projected_cost

    def can_spend(
        self,
        tenant_id: int,
        estimated_cost: float,
        check_type: str = 'all'
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se pode gastar considerando thresholds.

        Args:
            tenant_id: ID do tenant
            estimated_cost: Custo estimado da operação
            check_type: 'daily', 'monthly', 'tenant', ou 'all'

        Returns:
            Tupla (pode_gastar, motivo_recusa)
        """
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')

        if check_type in ['daily', 'all']:
            daily_cost = self.get_daily_cost(today)
            if daily_cost + estimated_cost > self.daily_threshold:
                return False, (
                    f"Daily threshold would be exceeded: "
                    f"R$ {daily_cost + estimated_cost:.2f} > R$ {self.daily_threshold:.2f}"
                )

        if check_type in ['monthly', 'all']:
            monthly_cost = self.get_monthly_cost(month)
            if monthly_cost + estimated_cost > self.monthly_threshold:
                return False, (
                    f"Monthly threshold would be exceeded: "
                    f"R$ {monthly_cost + estimated_cost:.2f} > R$ {self.monthly_threshold:.2f}"
                )

        if check_type in ['tenant', 'all']:
            tenant_monthly_cost = self.get_tenant_monthly_cost(tenant_id, month)
            if tenant_monthly_cost + estimated_cost > self.tenant_monthly_threshold:
                return False, (
                    f"Tenant monthly threshold would be exceeded: "
                    f"R$ {tenant_monthly_cost + estimated_cost:.2f} > "
                    f"R$ {self.tenant_monthly_threshold:.2f}"
                )

        return True, None

    def get_stats_summary(self) -> str:
        """
        Retorna resumo formatado das estatísticas de custo.

        Returns:
            String formatada com estatísticas
        """
        with self._lock:
            today = datetime.now().strftime('%Y-%m-%d')
            month = datetime.now().strftime('%Y-%m')

            daily_cost = self.get_daily_cost(today)
            monthly_cost = self.get_monthly_cost(month)

            summary = f"""Cost Tracker Status ({month}):
Daily Cost: R$ {daily_cost:7.2f} / R$ {self.daily_threshold:.2f}
Monthly Cost: R$ {monthly_cost:7.2f} / R$ {self.monthly_threshold:.2f}"""

            return summary


# Instância global (singleton)
_global_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """
    Retorna instância global do cost tracker (singleton).

    Returns:
        CostTracker instance
    """
    global _global_cost_tracker

    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker()

    return _global_cost_tracker


def reset_cost_tracker() -> None:
    """Reseta instância global (útil para testes)."""
    global _global_cost_tracker
    _global_cost_tracker = None
