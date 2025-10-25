#!/usr/bin/env python3
"""
Script para rodar análise GPT-4 manualmente

Uso:
    python scripts/analysis/run_gpt4.py              # Analisar todas as conversas pendentes
    python scripts/analysis/run_gpt4.py --limit 10   # Analisar apenas 10 conversas
    python scripts/analysis/run_gpt4.py --help       # Mostrar ajuda
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from features.analyzers.gpt4 import run_gpt4_analysis


def main():
    parser = argparse.ArgumentParser(
        description='Analisa conversas com GPT-4 (apenas novas/atualizadas)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limite de conversas para analisar (padrão: todas)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Modo silencioso (sem logs detalhados)'
    )

    args = parser.parse_args()

    # Rodar análise
    stats = run_gpt4_analysis(
        limit=args.limit,
        verbose=not args.quiet
    )

    # Exit code baseado no resultado
    if stats['failed'] > 0:
        sys.exit(1)  # Erro se houve falhas
    else:
        sys.exit(0)  # Sucesso


if __name__ == '__main__':
    main()
