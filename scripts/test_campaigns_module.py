#!/usr/bin/env python3
"""
Script de Teste - Módulo de Campanhas (Fase 10)
===============================================

Valida que todos os componentes do módulo de campanhas funcionam corretamente:
1. CampaignService (CRUD)
2. CampaignVariableGenerator (IA)
3. CampaignCSVExporter

Uso:
    python scripts/test_campaigns_module.py

Autor: Isaac (via Claude Code)
Data: 2025-11-26
"""

import os
import sys
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

# Adicionar diretório raiz ao path
sys.path.insert(0, '/home/tester/projetos/geniai-analytics')

from sqlalchemy import create_engine, text

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def create_engine_from_env():
    """Cria engine do banco local"""
    host = os.getenv('LOCAL_DB_HOST', 'localhost')
    port = os.getenv('LOCAL_DB_PORT', '5432')
    database = os.getenv('LOCAL_DB_NAME', 'geniai_analytics')
    user = os.getenv('LOCAL_DB_USER', 'johan_geniai')
    password = os.getenv('LOCAL_DB_PASSWORD', 'vlVMVM6UNz2yYSBlzodPjQvZh')

    password_encoded = quote_plus(password)
    connection_string = f"postgresql://{user}:{password_encoded}@{host}:{port}/{database}"

    return create_engine(connection_string, echo=False)


def test_imports():
    """Testa se todos os imports funcionam"""
    print_header("TESTE 1: Imports do Módulo")

    try:
        from src.multi_tenant.campaigns import (
            Campaign,
            CampaignLead,
            CampaignExport,
            CampaignStatus,
            LeadStatus,
            CampaignService,
            CampaignVariableGenerator,
            CampaignCSVExporter,
        )
        print_success("Todos os imports funcionaram")
        return True
    except ImportError as e:
        print_error(f"Erro de import: {e}")
        return False


def test_models():
    """Testa as dataclasses/models"""
    print_header("TESTE 2: Models (Dataclasses)")

    from src.multi_tenant.campaigns.models import (
        Campaign, CampaignLead, CampaignStatus, LeadStatus
    )

    # Teste Campaign
    campaign = Campaign(
        id=1,
        tenant_id=1,
        name="Black Friday 2025",
        slug="black-friday-2025",
        template_text="Olá, {{1}}. Vi que {{2}}. Hoje {{3}}!",
        promotional_context={"promocao": "40% off"},
        start_date=date(2025, 11, 25),
        end_date=date(2025, 11, 30),
        status=CampaignStatus.ACTIVE,
    )

    assert campaign.is_active == True
    assert campaign.can_process_leads == True
    assert "{{1}}" in campaign.template_text
    print_success("Campaign model OK")

    # Teste render_preview
    preview = campaign.render_preview("João", "você perguntou sobre...", "temos 40% off")
    assert "João" in preview
    assert "40% off" in preview
    print_success("Campaign.render_preview() OK")

    # Teste CampaignLead
    lead = CampaignLead(
        id=1,
        campaign_id=1,
        conversation_id=12345,
        contact_phone="+55 11 99999-8888",
        contact_name="João Silva",
        var1="João",
        var2="você perguntou sobre...",
        var3="temos 40% off",
        status=LeadStatus.PROCESSED,
    )

    assert lead.is_processed == True
    assert lead.csv_phone == "5511999998888"
    assert lead.first_name == "João"
    print_success("CampaignLead model OK")

    # Teste to_csv_row
    csv_row = lead.to_csv_row()
    assert csv_row["telefone"] == "5511999998888"
    assert csv_row["nome"] == "João"
    print_success("CampaignLead.to_csv_row() OK")

    return True


def test_database_tables(engine):
    """Testa se as tabelas existem no banco"""
    print_header("TESTE 3: Tabelas no Banco de Dados")

    tables = ["campaigns", "campaign_leads", "campaign_exports"]

    with engine.connect() as conn:
        for table in tables:
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                )
            """))
            exists = result.scalar()

            if exists:
                print_success(f"Tabela '{table}' existe")
            else:
                print_error(f"Tabela '{table}' não encontrada")
                return False

    return True


def test_campaign_service(engine, tenant_id=1):
    """Testa CampaignService"""
    print_header("TESTE 4: CampaignService (CRUD)")

    from src.multi_tenant.campaigns import CampaignService, CampaignStatus

    service = CampaignService(engine, tenant_id)

    # CREATE
    print_info("Criando campanha de teste...")
    campaign = service.create_campaign(
        name="Teste Automatizado",
        template_text="Olá, {{1}}. {{2}}. {{3}}!",
        promotional_context={
            "promocao": "Teste",
            "validade": "2025-12-31"
        },
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        description="Campanha criada por teste automatizado"
    )

    assert campaign.id is not None
    assert campaign.slug == "teste-automatizado"
    print_success(f"CREATE OK - ID={campaign.id}")

    # READ
    campaign_read = service.get_campaign(campaign.id)
    assert campaign_read is not None
    assert campaign_read.name == "Teste Automatizado"
    print_success("READ OK")

    # LIST
    campaigns = service.list_campaigns()
    assert len(campaigns) >= 1
    print_success(f"LIST OK - {len(campaigns)} campanhas encontradas")

    # UPDATE
    updated = service.update_campaign(
        campaign.id,
        description="Descrição atualizada",
        status=CampaignStatus.ACTIVE
    )
    assert updated.description == "Descrição atualizada"
    assert updated.status == CampaignStatus.ACTIVE
    print_success("UPDATE OK")

    # STATS
    stats = service.get_campaign_stats(campaign.id)
    assert "total" in stats
    assert "pending" in stats
    print_success(f"STATS OK - {stats}")

    # DELETE
    deleted = service.delete_campaign(campaign.id)
    assert deleted == True
    print_success("DELETE OK")

    # Verificar se foi deletado
    campaign_check = service.get_campaign(campaign.id)
    assert campaign_check is None
    print_success("Campanha removida do banco")

    return True


def test_csv_exporter():
    """Testa CampaignCSVExporter"""
    print_header("TESTE 5: CampaignCSVExporter")

    from src.multi_tenant.campaigns import (
        CampaignCSVExporter, CampaignLead, Campaign, LeadStatus
    )

    # Criar leads de teste
    leads = [
        CampaignLead(
            id=1,
            campaign_id=1,
            conversation_id=1001,
            contact_phone="11999998888",
            contact_name="João Silva",
            var1="João",
            var2="você perguntou sobre CrossFit",
            var3="temos 40% off no plano anual",
            status=LeadStatus.PROCESSED,
        ),
        CampaignLead(
            id=2,
            campaign_id=1,
            conversation_id=1002,
            contact_phone="+55 11 88887777",
            contact_name="Maria Santos",
            var1="Maria",
            var2="você demonstrou interesse em Pilates",
            var3="aproveite nossa aula experimental gratuita",
            status=LeadStatus.PROCESSED,
        ),
        CampaignLead(
            id=3,
            campaign_id=1,
            conversation_id=1003,
            contact_phone="",  # Sem telefone - deve ser pulado
            contact_name="Pedro",
            var1="Pedro",
            var2="teste",
            var3="teste",
            status=LeadStatus.PROCESSED,
        ),
    ]

    campaign = Campaign(
        id=1,
        tenant_id=1,
        name="Black Friday",
        slug="black-friday",
        template_text="Olá, {{1}}. {{2}}. {{3}}!",
        promotional_context={},
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
    )

    exporter = CampaignCSVExporter()

    # Exportar
    csv_content, stats = exporter.export(leads, campaign)

    # Validações
    assert stats["exported"] == 2
    assert stats["skipped_no_phone"] == 1
    print_success(f"Exportação OK - {stats['exported']} leads exportados")

    # Verificar conteúdo
    assert "telefone,nome,variavel_1,variavel_2" in csv_content
    assert "5511999998888" in csv_content
    assert "5511888877" in csv_content  # Phone formatado
    assert "João" in csv_content
    assert "Maria" in csv_content
    print_success("Conteúdo CSV válido")

    # Testar geração de nome de arquivo
    filename = exporter.generate_filename(campaign)
    assert "campanha_black-friday_" in filename
    assert filename.endswith(".csv")
    print_success(f"Filename OK: {filename}")

    # Testar preview
    preview = exporter.preview_rows(leads, limit=2)
    assert len(preview) == 2
    print_success(f"Preview OK - {len(preview)} linhas")

    # Mostrar conteúdo do CSV
    print_info("Conteúdo do CSV gerado:")
    print("-" * 60)
    for line in csv_content.strip().split("\n")[:5]:
        print(f"  {line[:80]}...")
    print("-" * 60)

    return True


def test_variable_generator_structure():
    """Testa estrutura do CampaignVariableGenerator (sem chamar OpenAI)"""
    print_header("TESTE 6: CampaignVariableGenerator (Estrutura)")

    from src.multi_tenant.campaigns import CampaignVariableGenerator

    # Verificar se a classe tem os métodos esperados
    assert hasattr(CampaignVariableGenerator, 'generate_for_lead')
    assert hasattr(CampaignVariableGenerator, 'generate_batch')
    assert hasattr(CampaignVariableGenerator, 'estimate_batch_cost')
    assert hasattr(CampaignVariableGenerator, 'get_session_stats')
    print_success("Métodos esperados existem")

    # Verificar prompt template
    assert "{{1}}" in CampaignVariableGenerator.VARIABLE_PROMPT_TEMPLATE
    assert "{{2}}" in CampaignVariableGenerator.VARIABLE_PROMPT_TEMPLATE
    assert "{{3}}" in CampaignVariableGenerator.VARIABLE_PROMPT_TEMPLATE
    print_success("Prompt template OK")

    print_warning("Teste de chamada real à OpenAI pulado (requer API key)")
    return True


def main():
    """Função principal de testes"""
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}   TESTES DO MÓDULO DE CAMPANHAS - FASE 10{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")

    all_passed = True

    # 1. Imports
    if not test_imports():
        print_error("Falha nos imports - abortando")
        return 1

    # 2. Models
    try:
        if not test_models():
            all_passed = False
    except Exception as e:
        print_error(f"Erro em test_models: {e}")
        all_passed = False

    # 3. Database
    try:
        engine = create_engine_from_env()
        if not test_database_tables(engine):
            all_passed = False
    except Exception as e:
        print_error(f"Erro em test_database_tables: {e}")
        all_passed = False

    # 4. CampaignService
    try:
        if not test_campaign_service(engine, tenant_id=1):
            all_passed = False
    except Exception as e:
        print_error(f"Erro em test_campaign_service: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 5. CSV Exporter
    try:
        if not test_csv_exporter():
            all_passed = False
    except Exception as e:
        print_error(f"Erro em test_csv_exporter: {e}")
        all_passed = False

    # 6. Variable Generator
    try:
        if not test_variable_generator_structure():
            all_passed = False
    except Exception as e:
        print_error(f"Erro em test_variable_generator_structure: {e}")
        all_passed = False

    # Resultado final
    print_header("RESULTADO FINAL")

    if all_passed:
        print_success("TODOS OS TESTES PASSARAM!")
        print_info("O módulo de campanhas está pronto para uso.")
        return 0
    else:
        print_error("ALGUNS TESTES FALHARAM!")
        print_info("Verifique os erros acima e corrija.")
        return 1


if __name__ == "__main__":
    sys.exit(main())