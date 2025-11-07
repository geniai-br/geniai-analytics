#!/usr/bin/env python3
"""
Script para executar ETL de todos os tenants ativos
Usado pelo Systemd Timer para automação
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
import subprocess

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)


def get_active_tenants():
    """
    Retorna lista de tenants ativos

    Returns:
        list[dict]: Lista de tenants (id, name, slug)
    """
    # Usar owner para bypass RLS
    owner_url = "postgresql://johan_geniai:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics"
    engine = create_engine(owner_url)

    query = text("""
        SELECT id, name, slug
        FROM tenants
        WHERE deleted_at IS NULL
          AND status = 'active'
          AND id != 0  -- Excluir GeniAI Admin
        ORDER BY id
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        tenants = []

        for row in result:
            tenants.append({
                'id': row.id,
                'name': row.name,
                'slug': row.slug
            })

        return tenants


def run_etl_for_tenant(tenant_id: int, tenant_name: str) -> bool:
    """
    Executa ETL para um tenant específico

    Args:
        tenant_id: ID do tenant
        tenant_name: Nome do tenant (para logs)

    Returns:
        bool: True se sucesso, False se erro
    """
    print(f"\n{'='*60}")
    print(f"🚀 Executando ETL para: {tenant_name} (ID: {tenant_id})")
    print(f"{'='*60}")

    try:
        # Caminho do script ETL
        etl_script = Path(__file__).parent / "pipeline.py"

        # Executar ETL como subprocesso
        result = subprocess.run(
            [sys.executable, str(etl_script), "--tenant-id", str(tenant_id)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos timeout
        )

        if result.returncode == 0:
            print(f"✅ ETL concluído com sucesso para {tenant_name}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return True
        else:
            print(f"❌ ETL falhou para {tenant_name}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️ ETL excedeu timeout de 10 minutos para {tenant_name}")
        return False
    except Exception as e:
        print(f"❌ Erro ao executar ETL para {tenant_name}: {str(e)}")
        return False


def main():
    """
    Função principal - executa ETL para todos os tenants ativos
    """
    start_time = datetime.now()

    print(f"\n{'#'*60}")
    print(f"# ETL AllpFit Analytics - Execução Automática")
    print(f"# Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

    # Buscar tenants ativos
    print("🔍 Buscando tenants ativos...")
    tenants = get_active_tenants()

    if not tenants:
        print("ℹ️ Nenhum tenant ativo encontrado")
        return 0

    print(f"✅ {len(tenants)} tenant(s) ativo(s) encontrado(s):\n")
    for t in tenants:
        print(f"  - {t['name']} (ID: {t['id']}, slug: {t['slug']})")

    # Executar ETL para cada tenant
    success_count = 0
    failed_count = 0

    for tenant in tenants:
        success = run_etl_for_tenant(tenant['id'], tenant['name'])

        if success:
            success_count += 1
        else:
            failed_count += 1

    # Resumo final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'#'*60}")
    print(f"# Resumo da Execução")
    print(f"{'#'*60}")
    print(f"Total de tenants: {len(tenants)}")
    print(f"✅ Sucesso: {success_count}")
    print(f"❌ Falhas: {failed_count}")
    print(f"⏱️ Duração total: {duration:.1f}s")
    print(f"🏁 Término: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

    # Exit code: 0 se todos sucederam, 1 se algum falhou
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())