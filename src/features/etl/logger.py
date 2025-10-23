"""
Logger - Sistema de logging estruturado para ETL

Este módulo configura logging com:
1. Logs em arquivo (rotacionados diariamente)
2. Logs no console (stdout)
3. Formatação estruturada
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name='etl', log_dir='logs/etl'):
    """
    Configura e retorna logger para ETL

    Args:
        name: Nome do logger
        log_dir: Diretório para salvar logs

    Returns:
        logging.Logger: Logger configurado
    """
    # Criar diretório de logs se não existir
    os.makedirs(log_dir, exist_ok=True)

    # Configurar logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Limpar handlers existentes (evitar duplicação)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formato dos logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler 1: Console (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler 2: Arquivo rotacionado (1 arquivo por dia, mantém 30 dias)
    log_file = os.path.join(log_dir, f"etl_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=30
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler 3: Arquivo "latest" (symlink/sempre o último)
    latest_log = os.path.join(log_dir, 'etl_latest.log')
    latest_handler = logging.FileHandler(latest_log, mode='w')
    latest_handler.setLevel(logging.DEBUG)
    latest_handler.setFormatter(formatter)
    logger.addHandler(latest_handler)

    return logger


def log_execution_summary(logger, stats):
    """
    Loga sumário da execução do ETL

    Args:
        logger: Logger instance
        stats: Dicionário com estatísticas
    """
    logger.info("=" * 80)
    logger.info("SUMÁRIO DA EXECUÇÃO ETL")
    logger.info("=" * 80)

    for key, value in stats.items():
        logger.info(f"   {key}: {value}")

    logger.info("=" * 80)
