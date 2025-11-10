"""
Test OpenAI Analyzer
=====================

Testa OpenAI analyzer com poucas conversas para validar funcionalidade e custos.

Execução:
    cd /home/tester/projetos/allpfit-analytics
    source venv/bin/activate
    python tests/test_openai_analyzer.py
"""

import sys
import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Adicionar path do projeto
sys.path.insert(0, '/home/tester/projetos/allpfit-analytics')

from src.multi_tenant.etl_v4.analyzers import OpenAIAnalyzer


def print_section(title):
    """Imprime seção formatada"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def get_local_engine():
    """Cria engine para banco local usando johan_geniai"""
    password = quote_plus('vlVMVM6UNz2yYSBlzodPjQvZh')
    connection_string = f"postgresql://johan_geniai:{password}@localhost:5432/geniai_analytics"

    engine = create_engine(
        connection_string,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        echo=False
    )

    return engine


def test_openai_analyzer_single_conversation():
    """Testa OpenAI analyzer com uma conversa de exemplo"""
    print_section("TEST 1: OpenAI Analyzer - Conversa Única")

    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não encontrada no ambiente")
        print("   Configure: export OPENAI_API_KEY='sk-...'")
        return False

    print(f"✅ API Key encontrada: {api_key[:20]}...")

    # Criar analyzer
    print("\n🔧 Criando OpenAI Analyzer...")
    try:
        analyzer = OpenAIAnalyzer(
            tenant_id=1,
            api_key=api_key,
            model='gpt-4o-mini'
        )
        print("✅ Analyzer criado com sucesso")
    except Exception as e:
        print(f"❌ ERRO ao criar analyzer: {e}")
        return False

    # Conversa de teste
    test_conversation = """
Bot: Olá! Seja bem-vindo à AllpFit CrossFit! Como posso te ajudar?
Lead: Oi! Tenho interesse em conhecer a academia. Quais são os horários disponíveis?
Bot: Temos aulas de segunda a sexta das 6h às 22h e sábados das 8h às 12h. Qual horário funciona melhor para você?
Lead: Prefiro de manhã, por volta das 7h. Qual o valor da mensalidade?
Bot: Perfeito! Temos turmas às 7h. O plano mensal custa R$ 199,00. Gostaria de agendar uma aula experimental gratuita?
Lead: Sim! Quero agendar para amanhã às 7h. Meu nome é João Silva.
Bot: Ótimo, João! Aula experimental agendada para amanhã às 7h. Te esperamos! Você já praticou CrossFit antes?
Lead: Não, sou sedentário. Quero melhorar meu condicionamento físico e perder uns 10kg.
Bot: Excelente objetivo! Nossos treinos são adaptados para todos os níveis. Vejo você amanhã!
Lead: Até amanhã! Obrigado!
"""

    print("\n📝 Conversa de teste:")
    print("-" * 80)
    print(test_conversation[:200] + "...")
    print("-" * 80)

    # Analisar
    print("\n🤖 Analisando com OpenAI GPT-4o-mini...")
    print("   (Isso pode levar alguns segundos...)\n")

    start_time = datetime.now()

    try:
        result = analyzer.analyze_conversation(
            message_text=test_conversation,
            contact_name="João Silva",
            message_count=10
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"✅ Análise concluída em {elapsed:.2f}s")

        # Mostrar resultados
        print("\n📊 Resultados da análise:")
        print(f"\n🎯 Classificação:")
        print(f"   Lead: {'✅ SIM' if result['is_lead'] else '❌ NÃO'}")
        print(f"   Visita agendada: {'✅ SIM' if result['visit_scheduled'] else '❌ NÃO'}")
        print(f"   CRM convertido: {'✅ SIM' if result['crm_converted'] else '❌ NÃO'}")
        print(f"   Probabilidade: {result['ai_probability_label']} ({result['ai_probability_score']:.1f})")

        print(f"\n👤 Dados extraídos:")
        print(f"   Nome: {result.get('nome_mapeado_bot', 'N/A')}")
        print(f"   Condição física: {result.get('condicao_fisica', 'N/A')}")
        print(f"   Objetivo: {result.get('objetivo', 'N/A')}")
        print(f"   Prob. conversão (0-5): {result.get('probabilidade_conversao', 0)}")

        print(f"\n💡 Análise IA:")
        analise = result.get('analise_ia', '')
        if analise:
            # Mostrar primeiros 300 chars
            print(f"   {analise[:300]}...")
        else:
            print("   (Não disponível)")

        print(f"\n📨 Sugestão de mensagem:")
        sugestao = result.get('sugestao_disparo', '')
        if sugestao:
            print(f"   {sugestao}")
        else:
            print("   (Não disponível)")

        # Estatísticas de uso
        print(f"\n💰 Estatísticas OpenAI:")
        usage_stats = analyzer.get_usage_stats()
        print(f"   API calls: {usage_stats['successful_calls']}")
        print(f"   Total tokens: {usage_stats['total_tokens']}")
        print(f"   Success rate: {usage_stats['success_rate']:.1f}%")

        # Calcular custo
        cost_per_1k_tokens = 0.0004
        usd_to_brl = 5.50
        cost_brl = (usage_stats['total_tokens'] / 1000.0) * cost_per_1k_tokens * usd_to_brl

        print(f"   Custo estimado: R$ {cost_brl:.4f}")

        # Validações
        print(f"\n✅ Validações:")
        checks = [
            ("Lead detectado corretamente", result['is_lead'] == True),
            ("Visita agendada detectada", result['visit_scheduled'] == True),
            ("Nome extraído", result.get('nome_mapeado_bot') != ''),
            ("Condição física identificada", result.get('condicao_fisica') != 'Não mencionado'),
            ("Objetivo identificado", result.get('objetivo') != 'Não mencionado'),
            ("Probabilidade >= 3", result.get('probabilidade_conversao', 0) >= 3),
            ("Análise IA gerada", len(result.get('analise_ia', '')) > 100),
            ("Sugestão gerada", len(result.get('sugestao_disparo', '')) > 20),
        ]

        passed = 0
        total = len(checks)

        for check_name, check_result in checks:
            status = "✅" if check_result else "⚠️ "
            print(f"   {status} {check_name}")
            if check_result:
                passed += 1

        print(f"\n📊 Score: {passed}/{total} checks passaram ({passed/total*100:.0f}%)")

        if passed >= 6:  # Pelo menos 75% deve passar
            print("\n✅ PASS - OpenAI Analyzer funcionando corretamente!")
            return True
        else:
            print(f"\n⚠️  WARN - Apenas {passed}/{total} checks passaram (esperado >= 6)")
            return False

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ ERRO ao analisar ({elapsed:.2f}s): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_openai_cost_tracking():
    """Testa rastreamento de custos com múltiplas conversas"""
    print_section("TEST 2: OpenAI Cost Tracking - Múltiplas Conversas")

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não encontrada")
        return False

    # Criar analyzer
    analyzer = OpenAIAnalyzer(tenant_id=1, api_key=api_key)

    # Conversas de teste
    test_conversations = [
        "Lead: Oi, quero saber o preço\nBot: R$ 199/mês",
        "Lead: Não tenho interesse\nBot: Obrigado",
        "Lead: Quero agendar aula experimental para amanhã\nBot: Ok, agendado!",
    ]

    print(f"📝 Testando com {len(test_conversations)} conversas...\n")

    start_time = datetime.now()
    results = []

    for i, conv in enumerate(test_conversations, 1):
        print(f"   [{i}/{len(test_conversations)}] Analisando...")
        try:
            result = analyzer.analyze_conversation(message_text=conv)
            results.append(result)
        except Exception as e:
            print(f"      ❌ Erro: {e}")

    elapsed = (datetime.now() - start_time).total_seconds()

    # Estatísticas finais
    usage_stats = analyzer.get_usage_stats()

    print(f"\n✅ Análise concluída em {elapsed:.2f}s")
    print(f"\n📊 Estatísticas:")
    print(f"   Conversas processadas: {len(results)}/{len(test_conversations)}")
    print(f"   API calls: {usage_stats['total_calls']}")
    print(f"   Successful calls: {usage_stats['successful_calls']}")
    print(f"   Failed calls: {usage_stats['failed_calls']}")
    print(f"   Total tokens: {usage_stats['total_tokens']}")
    print(f"   Média tokens/conversa: {usage_stats['total_tokens']/len(results) if results else 0:.0f}")

    # Calcular custo
    cost_per_1k_tokens = 0.0004
    usd_to_brl = 5.50
    cost_brl = (usage_stats['total_tokens'] / 1000.0) * cost_per_1k_tokens * usd_to_brl

    print(f"\n💰 Custos:")
    print(f"   Custo total: R$ {cost_brl:.4f}")
    print(f"   Custo/conversa: R$ {cost_brl/len(results) if results else 0:.4f}")
    print(f"   Custo projetado para 1.000 conversas: R$ {cost_brl/len(results)*1000 if results else 0:.2f}")

    # Validações
    checks = [
        ("Todas conversas processadas", len(results) == len(test_conversations)),
        ("Success rate 100%", usage_stats['success_rate'] == 100.0),
        ("Custo < R$ 0.10", cost_brl < 0.10),
        ("Tokens rastreados", usage_stats['total_tokens'] > 0),
    ]

    print(f"\n✅ Validações:")
    passed = sum(1 for _, check in checks if check)

    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} {check_name}")

    if passed >= 3:
        print("\n✅ PASS - Cost tracking funcionando!")
        return True
    else:
        print(f"\n❌ FAIL - Apenas {passed}/{ len(checks)} checks passaram")
        return False


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "🧪" * 40)
    print("  OPENAI ANALYZER TEST SUITE")
    print("  Fase 5.6 - OpenAI Integration")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🧪" * 40)

    results = {
        'test_single_conversation': test_openai_analyzer_single_conversation(),
        'test_cost_tracking': test_openai_cost_tracking(),
    }

    # Resumo final
    print_section("RESUMO FINAL")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n📊 Total: {passed}/{total} testes passaram")

    if passed == total:
        print("\n🎉 SUCCESS - Todos os testes OpenAI passaram!")
        print("\n💡 Próximo passo: Executar ETL completo com OpenAI habilitado")
        return 0
    else:
        print(f"\n❌ FAILURE - {total - passed} teste(s) falharam")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)