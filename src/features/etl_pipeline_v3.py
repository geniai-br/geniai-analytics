#!/usr/bin/env python3
"""
ETL Pipeline V3: Incremental Load with Scheduling Support
==========================================

Funcionalidades:
- ✅ Extração incremental (apenas dados novos/atualizados)
- ✅ UPSERT inteligente (INSERT novos, UPDATE modificados)
- ✅ Watermark automático (controle de ponto de sincronização)
- ✅ Logging estruturado com histórico
- ✅ Auditoria completa (tabela etl_control)
- ✅ Suporte para agendamento (systemd/cron)

Execução:
    python src/features/etl_pipeline_v3.py [--full] [--triggered-by scheduler]

Flags:
    --full: Força carga completa (ignora watermark)
    --triggered-by: Identifica quem disparou (scheduler, manual, api)
"""

import os
import sys
import argparse
import traceback
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ETL modules
from etl.watermark_manager import (
    get_last_watermark,
    create_etl_execution,
    update_etl_execution
)
from etl.extractor import extract_incremental, extract_full, test_connection
from etl.transformer import transform_data, validate_data
from etl.loader import load_upsert, load_full
from etl.logger import setup_logger, log_execution_summary


def run_etl_incremental(triggered_by='manual', force_full=False):
    """
    Executa ETL incremental

    Args:
        triggered_by: Como foi disparado ('manual', 'scheduler', 'api')
        force_full: Se True, força carga completa

    Returns:
        bool: True se executou com sucesso
    """
    logger = setup_logger('etl')

    logger.info("█" * 80)
    logger.info("  ETL PIPELINE V3 - AllpFit Analytics")
    logger.info("  Modo: INCREMENTAL (UPSERT)")
    logger.info(f"  Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Disparado por: {triggered_by}")
    logger.info("█" * 80)

    start_total = datetime.now()
    execution_id = None
    watermark_end = None

    try:
        # 0. TESTAR CONEXÃO
        logger.info("\n🔌 Testando conexão com banco remoto...")
        if not test_connection():
            logger.error("❌ Falha na conexão com banco remoto")
            return False

        # 1. REGISTRAR INÍCIO DA EXECUÇÃO
        logger.info("\n📝 Registrando execução no etl_control...")

        load_type = 'full' if force_full else 'incremental'
        execution_id = create_etl_execution(
            triggered_by=triggered_by,
            load_type=load_type,
            is_full_load=force_full
        )

        logger.info(f"   Execution ID: {execution_id}")

        # 2. OBTER WATERMARK
        watermark_start = None if force_full else get_last_watermark()

        if watermark_start:
            logger.info(f"\n📅 Watermark encontrado: {watermark_start}")
            logger.info(f"   Modo: INCREMENTAL (buscar apenas dados novos)")
        else:
            logger.info(f"\n📅 Nenhum watermark encontrado")
            logger.info(f"   Modo: FULL LOAD (primeira execução ou forçado)")

        # 3. EXTRACT
        logger.info("\n" + "=" * 80)
        logger.info("FASE 1: EXTRACT")
        logger.info("=" * 80)

        df, watermark_end, extract_duration = extract_incremental(watermark_start)

        if df is None:
            logger.error("❌ Falha na extração")
            raise Exception("Extração retornou None")

        rows_extracted = len(df)
        logger.info(f"✅ Extração concluída: {rows_extracted:,} registros em {extract_duration:.2f}s")

        if rows_extracted == 0:
            logger.info("\n📭 Nenhum dado novo para processar")
            logger.info("   ETL concluído (sem mudanças)")

            # Atualizar execução como sucesso
            update_etl_execution(
                execution_id=execution_id,
                status='success',
                watermark_end=watermark_start,  # Manter watermark anterior
                rows_extracted=0,
                rows_inserted=0,
                rows_updated=0,
                rows_unchanged=0,
                duration_seconds=(datetime.now() - start_total).total_seconds(),
                extract_duration=extract_duration,
                transform_duration=0,
                load_duration=0
            )

            logger.info("\n✅ ETL CONCLUÍDO (sem dados novos)")
            return True

        # 4. TRANSFORM
        logger.info("\n" + "=" * 80)
        logger.info("FASE 2: TRANSFORM")
        logger.info("=" * 80)

        df_transformed, transform_duration = transform_data(df)

        if df_transformed is None:
            logger.error("❌ Falha na transformação")
            raise Exception("Transformação retornou None")

        logger.info(f"✅ Transformação concluída em {transform_duration:.2f}s")

        # 5. VALIDATE
        logger.info("\n🔍 Validando dados...")
        if not validate_data(df_transformed):
            logger.error("❌ Validação falhou")
            raise Exception("Dados inválidos")

        # 6. LOAD
        logger.info("\n" + "=" * 80)
        logger.info("FASE 3: LOAD")
        logger.info("=" * 80)

        if force_full:
            # Carga completa (TRUNCATE + INSERT)
            rows_inserted, load_duration = load_full(df_transformed, truncate=True)
            rows_updated = 0
            rows_unchanged = 0
        else:
            # Carga incremental (UPSERT)
            rows_inserted, rows_updated, rows_unchanged, load_duration = load_upsert(df_transformed)

        logger.info(f"✅ Carga concluída em {load_duration:.2f}s")

        # 7. ATUALIZAR EXECUÇÃO (SUCESSO)
        elapsed_total = (datetime.now() - start_total).total_seconds()

        update_etl_execution(
            execution_id=execution_id,
            status='success',
            watermark_end=watermark_end,
            rows_extracted=rows_extracted,
            rows_inserted=rows_inserted,
            rows_updated=rows_updated,
            rows_unchanged=rows_unchanged,
            duration_seconds=elapsed_total,
            extract_duration=extract_duration,
            transform_duration=transform_duration,
            load_duration=load_duration
        )

        # 8. SUMÁRIO
        logger.info("\n" + "█" * 80)
        logger.info("  ✅ ETL PIPELINE CONCLUÍDO COM SUCESSO!")
        logger.info("█" * 80)

        stats = {
            'Execution ID': execution_id,
            'Modo': load_type.upper(),
            'Registros extraídos': f"{rows_extracted:,}",
            'Registros inseridos': f"{rows_inserted:,}",
            'Registros atualizados': f"{rows_updated:,}",
            'Registros inalterados': f"{rows_unchanged:,}",
            'Watermark inicial': watermark_start or 'N/A',
            'Watermark final': watermark_end or 'N/A',
            'Tempo extração': f"{extract_duration:.2f}s",
            'Tempo transformação': f"{transform_duration:.2f}s",
            'Tempo carga': f"{load_duration:.2f}s",
            'Tempo TOTAL': f"{elapsed_total:.2f}s ({elapsed_total/60:.1f}min)"
        }

        log_execution_summary(logger, stats)

        return True

    except Exception as e:
        # Erro durante execução
        logger.error(f"\n❌ ERRO DURANTE EXECUÇÃO DO ETL")
        logger.error(f"   {str(e)}")

        error_traceback = traceback.format_exc()
        logger.error(f"\n{error_traceback}")

        # Atualizar execução como falha
        if execution_id:
            elapsed_total = (datetime.now() - start_total).total_seconds()

            update_etl_execution(
                execution_id=execution_id,
                status='failed',
                watermark_end=watermark_end,
                duration_seconds=elapsed_total,
                error_message=str(e),
                error_traceback=error_traceback
            )

        logger.error("\n❌ ETL PIPELINE FALHOU")
        return False


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description='ETL Pipeline V3 - Incremental Load')

    parser.add_argument(
        '--full',
        action='store_true',
        help='Força carga completa (ignora watermark)'
    )

    parser.add_argument(
        '--triggered-by',
        type=str,
        default='manual',
        choices=['manual', 'scheduler', 'api'],
        help='Identifica quem disparou a execução'
    )

    args = parser.parse_args()

    # Executar ETL
    success = run_etl_incremental(
        triggered_by=args.triggered_by,
        force_full=args.full
    )

    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
