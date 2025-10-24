#!/usr/bin/env python3
"""
Script para rodar análise GPT-4 manualmente

Uso:
    python run_gpt4_analysis.py              # Analisar todas as conversas pendentes
    python run_gpt4_analysis.py --limit 10   # Analisar apenas 10 conversas
    python run_gpt4_analysis.py --help       # Mostrar ajuda
"""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from features.gpt4_analyzer import run_gpt4_analysis


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
