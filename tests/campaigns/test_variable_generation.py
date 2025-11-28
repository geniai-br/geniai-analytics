#!/usr/bin/env python3
"""
Teste Manual de Geração de Variáveis para Campanhas
====================================================

Este script permite testar a geração de variáveis de campanha
de forma interativa, validando cada etapa do processo.

Uso:
    python tests/campaigns/test_variable_generation.py

Autor: Isaac (via Claude Code)
Data: 2025-11-27
"""

import os
import sys
import json
from pathlib import Path
from datetime import date, datetime
from pprint import pprint

# Adicionar src ao path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from multi_tenant.campaigns import (
    CampaignService,
    CampaignVariableGenerator,
    Campaign,
    CampaignLead,
    CampaignStatus,
    CampaignType,
    CampaignTone,
    LeadStatus,
)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

def get_database_url():
    """Obtém URL do banco de dados"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:vlVMVM6UNz2yYSBlzodPjQvZh@localhost:5432/geniai_analytics'
    )


def get_engine():
    """Cria engine SQLAlchemy"""
    return create_engine(get_database_url())


def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Imprime seção formatada"""
    print(f"\n--- {title} ---")


# ============================================================================
# FUNÇÕES DE TESTE
# ============================================================================

def test_1_listar_campanhas(tenant_id: int = 1):
    """Lista campanhas disponíveis para teste"""
    print_header("TESTE 1: Listar Campanhas do Tenant")

    engine = get_engine()
    service = CampaignService(engine, tenant_id)

    campaigns = service.list_campaigns()

    if not campaigns:
        print("❌ Nenhuma campanha encontrada!")
        print("   Crie uma campanha primeiro no dashboard.")
        return None

    print(f"\n✅ Encontradas {len(campaigns)} campanha(s):\n")

    for c in campaigns:
        stats = service.get_campaign_stats(c.id)
        print(f"  [{c.id}] {c.name}")
        print(f"      Status: {c.status.value}")
        print(f"      Tipo: {c.campaign_type.value} | Tom: {c.tone.value}")
        print(f"      Leads: {stats['total']} total | {stats['pending']} pendentes | {stats['processed']} processados")
        print()

    return campaigns


def test_2_listar_leads_pendentes(campaign_id: int, tenant_id: int = 1):
    """Lista leads pendentes de uma campanha"""
    print_header(f"TESTE 2: Leads Pendentes da Campanha {campaign_id}")

    engine = get_engine()
    service = CampaignService(engine, tenant_id)

    leads = service.get_pending_leads(campaign_id, limit=10)

    if not leads:
        print("❌ Nenhum lead pendente!")
        print("   Adicione leads à campanha primeiro.")
        return None

    print(f"\n✅ Encontrados {len(leads)} lead(s) pendentes:\n")

    for lead in leads:
        print(f"  [{lead.id}] {lead.contact_name or 'Sem nome'}")
        print(f"      Telefone: {lead.contact_phone}")
        print(f"      Conversation ID: {lead.conversation_id}")
        print(f"      Status: {lead.status.value}")
        print()

    return leads


def test_3_buscar_analise_lead(conversation_id: int, tenant_id: int = 1):
    """Busca análise prévia de um lead (o que a IA vai usar)"""
    print_header(f"TESTE 3: Análise Prévia do Lead (conversation_id={conversation_id})")

    engine = get_engine()
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY não configurada!")
        return None

    generator = CampaignVariableGenerator(
        openai_api_key=api_key,
        engine=engine,
        tenant_id=tenant_id
    )

    # Buscar análise (método interno)
    analysis = generator._get_lead_analysis(conversation_id)

    if not analysis:
        print("❌ Nenhuma análise encontrada para este lead!")
        return None

    print("\n✅ Análise encontrada:\n")
    for key, value in analysis.items():
        print(f"  {key}: {value}")

    return analysis


def test_4_gerar_variaveis(campaign_id: int, lead_id: int, tenant_id: int = 1):
    """Gera variáveis para um lead específico"""
    print_header(f"TESTE 4: Gerar Variáveis (campaign={campaign_id}, lead={lead_id})")

    engine = get_engine()
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY não configurada!")
        return None

    service = CampaignService(engine, tenant_id)

    # Buscar campanha
    campaign = service.get_campaign(campaign_id)
    if not campaign:
        print(f"❌ Campanha {campaign_id} não encontrada!")
        return None

    print_section("Dados da Campanha")
    print(f"  Nome: {campaign.name}")
    print(f"  Tipo: {campaign.campaign_type.value}")
    print(f"  Tom: {campaign.tone.value}")
    print(f"  Template: {campaign.template_text[:100]}...")
    if campaign.briefing:
        print(f"  Briefing: {campaign.briefing[:200]}...")

    # Buscar lead
    leads = service.get_campaign_leads(campaign_id)
    lead = next((l for l in leads if l.id == lead_id), None)

    if not lead:
        print(f"❌ Lead {lead_id} não encontrado na campanha!")
        return None

    print_section("Dados do Lead")
    print(f"  Nome: {lead.contact_name}")
    print(f"  Telefone: {lead.contact_phone}")
    print(f"  Conversation ID: {lead.conversation_id}")

    # Criar generator
    generator = CampaignVariableGenerator(
        openai_api_key=api_key,
        engine=engine,
        tenant_id=tenant_id
    )

    print_section("Gerando Variáveis com IA...")
    print("  (Aguarde, chamando OpenAI...)")

    # Gerar!
    result = generator.generate_for_lead(campaign, lead)

    print_section("Resultado")

    if result.get('status') == LeadStatus.PROCESSED:
        print("  ✅ SUCESSO!")
        print()
        print(f"  var1 (nome): {result.get('var1')}")
        print(f"  var2 (contexto): {result.get('var2')}")
        print(f"  var3 (oferta): {result.get('var3')}")
        print()

        print_section("Preview da Mensagem")
        print(f"  {result.get('message_preview')}")
        print()

        print_section("Metadados")
        metadata = result.get('metadata', {})
        print(f"  Modelo: {metadata.get('model')}")
        print(f"  Tokens: {metadata.get('tokens_total')}")
        print(f"  Custo: R$ {metadata.get('cost_brl', 0):.4f}")
        print(f"  Tempo: {metadata.get('duration_seconds')}s")
    else:
        print("  ❌ ERRO!")
        print(f"  Mensagem: {result.get('error_message')}")

    return result


def test_5_salvar_resultado(campaign_id: int, lead_id: int, result: dict, tenant_id: int = 1):
    """Salva o resultado no banco de dados"""
    print_header(f"TESTE 5: Salvar Resultado no Banco")

    if not result or result.get('status') != LeadStatus.PROCESSED:
        print("❌ Nenhum resultado válido para salvar!")
        return False

    engine = get_engine()
    service = CampaignService(engine, tenant_id)

    print_section("Salvando...")

    success = service.update_lead(
        lead_id=lead_id,
        var1=result.get('var1'),
        var2=result.get('var2'),
        var3=result.get('var3'),
        message_preview=result.get('message_preview'),
        status=LeadStatus.PROCESSED,
        generation_metadata=result.get('metadata', {})
    )

    if success:
        print("  ✅ Salvo com sucesso!")

        # Verificar no banco
        print_section("Verificando no Banco...")

        with engine.connect() as conn:
            query = text("""
                SELECT var1, var2, var3, message_preview, status, generation_metadata
                FROM campaign_leads
                WHERE id = :lead_id
            """)
            row = conn.execute(query, {"lead_id": lead_id}).fetchone()

            if row:
                print(f"  var1: {row[0]}")
                print(f"  var2: {row[1]}")
                print(f"  var3: {row[2]}")
                print(f"  status: {row[4]}")
                print(f"  metadata: {row[5]}")
    else:
        print("  ❌ Falha ao salvar!")

    return success


def test_6_exportar_csv(campaign_id: int, tenant_id: int = 1):
    """Testa exportação CSV"""
    print_header(f"TESTE 6: Exportar CSV da Campanha {campaign_id}")

    from multi_tenant.campaigns import CampaignCSVExporter

    engine = get_engine()
    service = CampaignService(engine, tenant_id)

    # Buscar leads exportáveis
    leads = service.get_exportable_leads(campaign_id, only_not_exported=False)

    if not leads:
        print("❌ Nenhum lead processado para exportar!")
        return None

    print(f"\n✅ {len(leads)} lead(s) exportáveis\n")

    # Criar exporter
    exporter = CampaignCSVExporter()

    # Gerar CSV
    csv_content = exporter.export(leads)

    print_section("Preview do CSV")
    print(csv_content[:1000])

    # Salvar arquivo de teste
    output_path = Path(__file__).parent / f"test_export_campaign_{campaign_id}.csv"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)

    print(f"\n✅ CSV salvo em: {output_path}")

    return csv_content


# ============================================================================
# MENU INTERATIVO
# ============================================================================

def menu_interativo():
    """Menu interativo para testes"""
    print("\n" + "=" * 70)
    print("  TESTE MANUAL - Geração de Variáveis para Campanhas")
    print("=" * 70)

    tenant_id = int(input("\nDigite o tenant_id (default=1): ") or "1")

    while True:
        print("\n--- MENU ---")
        print("1. Listar campanhas")
        print("2. Listar leads pendentes de uma campanha")
        print("3. Ver análise prévia de um lead")
        print("4. Gerar variáveis para um lead")
        print("5. Salvar resultado no banco")
        print("6. Exportar CSV")
        print("7. Teste completo (3 + 4 + 5)")
        print("0. Sair")

        opcao = input("\nEscolha: ")

        if opcao == "0":
            print("\nAté logo!")
            break

        elif opcao == "1":
            test_1_listar_campanhas(tenant_id)

        elif opcao == "2":
            campaign_id = int(input("Campaign ID: "))
            test_2_listar_leads_pendentes(campaign_id, tenant_id)

        elif opcao == "3":
            conversation_id = int(input("Conversation ID: "))
            test_3_buscar_analise_lead(conversation_id, tenant_id)

        elif opcao == "4":
            campaign_id = int(input("Campaign ID: "))
            lead_id = int(input("Lead ID: "))
            result = test_4_gerar_variaveis(campaign_id, lead_id, tenant_id)

        elif opcao == "5":
            campaign_id = int(input("Campaign ID: "))
            lead_id = int(input("Lead ID: "))
            if 'result' in dir():
                test_5_salvar_resultado(campaign_id, lead_id, result, tenant_id)
            else:
                print("❌ Execute o teste 4 primeiro!")

        elif opcao == "6":
            campaign_id = int(input("Campaign ID: "))
            test_6_exportar_csv(campaign_id, tenant_id)

        elif opcao == "7":
            campaign_id = int(input("Campaign ID: "))
            lead_id = int(input("Lead ID: "))

            # Buscar conversation_id
            engine = get_engine()
            service = CampaignService(engine, tenant_id)
            leads = service.get_campaign_leads(campaign_id)
            lead = next((l for l in leads if l.id == lead_id), None)

            if lead:
                test_3_buscar_analise_lead(lead.conversation_id, tenant_id)
                result = test_4_gerar_variaveis(campaign_id, lead_id, tenant_id)
                if result:
                    salvar = input("\nSalvar no banco? (s/n): ")
                    if salvar.lower() == 's':
                        test_5_salvar_resultado(campaign_id, lead_id, result, tenant_id)
            else:
                print(f"❌ Lead {lead_id} não encontrado!")

        else:
            print("Opção inválida!")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Verificar OPENAI_API_KEY
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERRO: OPENAI_API_KEY não está configurada!")
        print("   Configure no arquivo .env ou exporte a variável de ambiente.")
        sys.exit(1)

    menu_interativo()