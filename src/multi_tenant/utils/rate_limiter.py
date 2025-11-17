"""
Rate Limiter Global - Sistema de Análise Multi-Tenant
=====================================================

Controla taxa de requisições à OpenAI API considerando todos os tenants.

Limites OpenAI (Tier 1 - gpt-4o-mini):
- 500 RPM (Requests Per Minute)
- 30,000 TPM (Tokens Per Minute)
- 200 RPD (Requests Per Day)

Estratégia de Rate Limiting:
- Sliding window (janela deslizante) para contagem precisa
- File-based storage (simples, sem dependência Redis)
- Thread-safe para execuções paralelas futuras
- Conservative limits (80% dos limites oficiais para margem de segurança)

Fase: 9.1 - Rate Limiting Foundation
Relacionado: docs/private/checkpoints/FASE9_AUTOMACAO_MULTI_TENANT.md
Autor: Isaac (via Claude Code)
Data: 2025-11-17
"""

import logging
import time
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from threading import Lock

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter global para OpenAI API usando sliding window.

    Limites configuráveis com defaults seguros (80% dos limites oficiais).
    Persiste estado em arquivo para sobreviver a reinicializações.
    """

    # Limites OpenAI Tier 1 (conservadores - 80% dos oficiais)
    DEFAULT_RPM_LIMIT = 400      # 80% de 500 RPM
    DEFAULT_TPM_LIMIT = 24000    # 80% de 30,000 TPM
    DEFAULT_RPD_LIMIT = 160      # 80% de 200 RPD

    # Janelas de tempo
    MINUTE_WINDOW = 60           # 60 segundos
    DAY_WINDOW = 86400          # 24 horas em segundos

    # Arquivo de persistência
    STATE_FILE = '/tmp/geniai_rate_limiter_state.json'

    def __init__(
        self,
        rpm_limit: int = DEFAULT_RPM_LIMIT,
        tpm_limit: int = DEFAULT_TPM_LIMIT,
        rpd_limit: int = DEFAULT_RPD_LIMIT,
        state_file: Optional[str] = None
    ):
        """
        Inicializa o rate limiter.

        Args:
            rpm_limit: Requests per minute limit
            tpm_limit: Tokens per minute limit
            rpd_limit: Requests per day limit
            state_file: Caminho para arquivo de estado (opcional)
        """
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit
        self.state_file = state_file or self.STATE_FILE

        # Thread-safe lock
        self._lock = Lock()

        # Estado interno (carregado do arquivo se existir)
        self._state = {
            'requests_minute': [],      # [(timestamp, tokens), ...]
            'requests_day': [],          # [(timestamp, tokens), ...]
            'total_requests': 0,
            'total_tokens': 0,
            'last_cleanup': time.time()
        }

        # Carregar estado persistido
        self._load_state()

        logger.info(
            f"RateLimiter inicializado - "
            f"RPM: {rpm_limit}, TPM: {tpm_limit}, RPD: {rpd_limit}"
        )

    def _load_state(self) -> None:
        """Carrega estado do arquivo se existir."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    saved_state = json.load(f)

                    # Limpar requisições antigas
                    now = time.time()
                    saved_state['requests_minute'] = [
                        (ts, tokens) for ts, tokens in saved_state.get('requests_minute', [])
                        if now - ts < self.MINUTE_WINDOW
                    ]
                    saved_state['requests_day'] = [
                        (ts, tokens) for ts, tokens in saved_state.get('requests_day', [])
                        if now - ts < self.DAY_WINDOW
                    ]

                    self._state.update(saved_state)
                    logger.info(f"Estado carregado: {self.get_current_usage()}")
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

    def _cleanup_old_requests(self) -> None:
        """Remove requisições antigas das janelas de tempo."""
        now = time.time()

        # Limpar janela de 1 minuto
        self._state['requests_minute'] = [
            (ts, tokens) for ts, tokens in self._state['requests_minute']
            if now - ts < self.MINUTE_WINDOW
        ]

        # Limpar janela de 1 dia
        self._state['requests_day'] = [
            (ts, tokens) for ts, tokens in self._state['requests_day']
            if now - ts < self.DAY_WINDOW
        ]

        self._state['last_cleanup'] = now

    def get_current_usage(self) -> Dict[str, Any]:
        """
        Retorna uso atual em todas as janelas de tempo.

        Returns:
            Dict com métricas atuais
        """
        with self._lock:
            self._cleanup_old_requests()

            # Contadores
            rpm_count = len(self._state['requests_minute'])
            rpd_count = len(self._state['requests_day'])

            # Tokens na última janela de 1 minuto
            tpm_count = sum(
                tokens for _, tokens in self._state['requests_minute']
            )

            return {
                'requests_per_minute': rpm_count,
                'tokens_per_minute': tpm_count,
                'requests_per_day': rpd_count,
                'rpm_limit': self.rpm_limit,
                'tpm_limit': self.tpm_limit,
                'rpd_limit': self.rpd_limit,
                'rpm_available': self.rpm_limit - rpm_count,
                'tpm_available': self.tpm_limit - tpm_count,
                'rpd_available': self.rpd_limit - rpd_count,
                'rpm_usage_percent': round((rpm_count / self.rpm_limit) * 100, 1),
                'tpm_usage_percent': round((tpm_count / self.tpm_limit) * 100, 1),
                'rpd_usage_percent': round((rpd_count / self.rpd_limit) * 100, 1),
                'total_requests': self._state['total_requests'],
                'total_tokens': self._state['total_tokens']
            }

    def can_make_request(self, estimated_tokens: int = 500) -> tuple[bool, Optional[str]]:
        """
        Verifica se pode fazer uma requisição considerando limites.

        Args:
            estimated_tokens: Tokens estimados para a requisição

        Returns:
            Tupla (pode_fazer, motivo_recusa)
        """
        with self._lock:
            self._cleanup_old_requests()

            usage = self.get_current_usage()

            # Verificar RPM
            if usage['rpm_available'] <= 0:
                return False, f"RPM limit reached ({usage['requests_per_minute']}/{self.rpm_limit})"

            # Verificar TPM
            if usage['tpm_available'] < estimated_tokens:
                return False, f"TPM limit reached ({usage['tokens_per_minute']}/{self.tpm_limit})"

            # Verificar RPD
            if usage['rpd_available'] <= 0:
                return False, f"RPD limit reached ({usage['requests_per_day']}/{self.rpd_limit})"

            return True, None

    def record_request(self, tokens_used: int) -> None:
        """
        Registra uma requisição feita.

        Args:
            tokens_used: Número de tokens consumidos
        """
        with self._lock:
            now = time.time()

            # Adicionar às janelas
            self._state['requests_minute'].append((now, tokens_used))
            self._state['requests_day'].append((now, tokens_used))

            # Atualizar contadores totais
            self._state['total_requests'] += 1
            self._state['total_tokens'] += tokens_used

            # Persistir estado
            self._save_state()

            # Log se próximo dos limites
            usage = self.get_current_usage()
            if usage['rpm_usage_percent'] > 80:
                logger.warning(
                    f"RPM usage high: {usage['rpm_usage_percent']}% "
                    f"({usage['requests_per_minute']}/{self.rpm_limit})"
                )
            if usage['tpm_usage_percent'] > 80:
                logger.warning(
                    f"TPM usage high: {usage['tpm_usage_percent']}% "
                    f"({usage['tokens_per_minute']}/{self.tpm_limit})"
                )

    def wait_if_needed(self, estimated_tokens: int = 500, max_wait: int = 60) -> bool:
        """
        Espera se necessário até que seja possível fazer a requisição.

        Args:
            estimated_tokens: Tokens estimados
            max_wait: Tempo máximo de espera em segundos

        Returns:
            True se pode prosseguir, False se timeout
        """
        start_time = time.time()

        while True:
            can_proceed, reason = self.can_make_request(estimated_tokens)

            if can_proceed:
                return True

            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                logger.error(
                    f"Rate limit timeout após {elapsed:.1f}s. Motivo: {reason}"
                )
                return False

            # Calcular tempo de espera baseado no motivo
            if "RPM" in reason:
                wait_time = min(10, max_wait - elapsed)  # Esperar até 10s
            elif "TPM" in reason:
                wait_time = min(15, max_wait - elapsed)  # Esperar até 15s
            else:  # RPD
                logger.error(f"Daily limit reached. Cannot proceed. {reason}")
                return False

            logger.info(f"Rate limit atingido. Aguardando {wait_time:.1f}s... ({reason})")
            time.sleep(wait_time)

    def reset_daily_stats(self) -> None:
        """Reseta estatísticas diárias (útil para testes ou reset manual)."""
        with self._lock:
            self._state['requests_day'] = []
            self._save_state()
            logger.info("Estatísticas diárias resetadas")

    def get_stats_summary(self) -> str:
        """
        Retorna resumo formatado das estatísticas.

        Returns:
            String formatada com estatísticas
        """
        with self._lock:
            usage = self.get_current_usage()

            return f"""Rate Limiter Status:
RPM: {usage['requests_per_minute']:3d}/{self.rpm_limit} ({usage['rpm_usage_percent']:5.1f}%)
TPM: {usage['tokens_per_minute']:5d}/{self.tpm_limit} ({usage['tpm_usage_percent']:5.1f}%)
RPD: {usage['requests_per_day']:3d}/{self.rpd_limit} ({usage['rpd_usage_percent']:5.1f}%)
Total Requests: {usage['total_requests']:,}
Total Tokens:   {usage['total_tokens']:,}"""


# Instância global (singleton)
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Retorna instância global do rate limiter (singleton).

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()

    return _global_rate_limiter


def reset_rate_limiter() -> None:
    """Reseta instância global (útil para testes)."""
    global _global_rate_limiter
    _global_rate_limiter = None