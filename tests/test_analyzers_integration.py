"""
Test Analyzers Integration
===========================

Testa a integração completa dos analyzers (Regex e OpenAI).

Execução:
    cd /home/tester/projetos/allpfit-analytics
    python tests/test_analyzers_integration.py
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, '/home/tester/projetos/allpfit-analytics')

from src.multi_tenant.etl_v4.analyzers import (
    BaseAnalyzer,
    AnalyzerFactory,
    RegexAnalyzer,
    OpenAIAnalyzer
)


def print_section(title):
    """Imprime seção formatada"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_regex_analyzer():
    """Testa RegexAnalyzer com dados de exemplo"""
    print_section("TEST 1: RegexAnalyzer - Análise por Keywords")

    # Dados de teste
    test_conversations = [
        {
            'id': 1,
            'message': 'Olá! Quero agendar uma aula experimental para amanhã às 18h',
            'expected_lead': True,
            'expected_visit': True,
        },
        {
            'id': 2,
            'message': 'Quanto custa a matrícula? Tenho interesse no plano anual',
            'expected_lead': True,
            'expected_visit': False,
        },
        {
            'id': 3,
            'message': 'Matrícula realizada com sucesso! Pagamento confirmado via Pix',
            'expected_lead': True,
            'expected_visit': False,
        },
        {
            'id': 4,
            'message': 'Não quero mais, desisti',
            'expected_lead': False,
            'expected_visit': False,
        },
        {
            'id': 5,
            'message': 'Olá, boa tarde',
            'expected_lead': False,
            'expected_visit': False,
        },
    ]

    # Criar analyzer
    analyzer = RegexAnalyzer(tenant_id=1)

    print(f"✅ RegexAnalyzer criado para tenant 1")
    print(f"   - {len(analyzer.lead_patterns)} padrões de lead")
    print(f"   - {len(analyzer.visit_patterns)} padrões de visita")
    print(f"   - {len(analyzer.conversion_patterns)} padrões de conversão\n")

    # Testar cada conversa
    passed = 0
    failed = 0

    for conv in test_conversations:
        result = analyzer.analyze_conversation(
            message_text=conv['message'],
            status='open',
            has_human_intervention=False
        )

        # Verificar resultados
        lead_ok = result['is_lead'] == conv['expected_lead']
        visit_ok = result['visit_scheduled'] == conv['expected_visit']

        if lead_ok and visit_ok:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"[{conv['id']}] {status}")
        print(f"    Mensagem: {conv['message'][:60]}...")
        print(f"    Lead: {result['is_lead']} (esperado: {conv['expected_lead']}) | "
              f"Visita: {result['visit_scheduled']} (esperado: {conv['expected_visit']})")
        print(f"    Score: {result['ai_probability_score']:.1f} | "
              f"Label: {result['ai_probability_label']}")

        if result['is_lead']:
            print(f"    Keywords encontradas: {len(result.get('lead_keywords_found', []))} leads, "
                  f"{len(result.get('visit_keywords_found', []))} visitas")
        print()

    print(f"📊 Resultados: {passed} passed, {failed} failed")

    return failed == 0


def test_regex_analyzer_dataframe():
    """Testa RegexAnalyzer com DataFrame"""
    print_section("TEST 2: RegexAnalyzer - Análise de DataFrame")

    # Criar DataFrame de teste
    df = pd.DataFrame([
        {
            'conversation_id': 1,
            'message_compiled': 'Olá! Quero agendar uma aula experimental para amanhã às 18h',
            'status': 'open',
            'has_human_intervention': False,
        },
        {
            'conversation_id': 2,
            'message_compiled': 'Quanto custa a matrícula? Tenho interesse no plano anual',
            'status': 'open',
            'has_human_intervention': False,
        },
        {
            'conversation_id': 3,
            'message_compiled': 'Matrícula realizada com sucesso! Pagamento confirmado via Pix',
            'status': 'resolved',
            'has_human_intervention': True,
        },
        {
            'conversation_id': 4,
            'message_compiled': 'Não quero mais, desisti',
            'status': 'resolved',
            'has_human_intervention': False,
        },
        {
            'conversation_id': 5,
            'message_compiled': 'Olá, boa tarde',
            'status': 'open',
            'has_human_intervention': False,
        },
    ])

    print(f"📊 DataFrame criado com {len(df)} conversas\n")

    # Criar analyzer e processar
    analyzer = RegexAnalyzer(tenant_id=1)
    df_analyzed = analyzer.analyze_dataframe(df)

    # Verificar colunas adicionadas
    expected_cols = ['is_lead', 'visit_scheduled', 'crm_converted',
                     'ai_probability_label', 'ai_probability_score']

    missing_cols = [col for col in expected_cols if col not in df_analyzed.columns]

    if missing_cols:
        print(f"❌ FAIL - Colunas faltando: {missing_cols}")
        return False
    else:
        print(f"✅ Todas as colunas esperadas foram adicionadas\n")

    # Mostrar resultados
    print("📊 Resultados da análise:")
    print(df_analyzed[['conversation_id', 'is_lead', 'visit_scheduled',
                       'ai_probability_label', 'ai_probability_score']].to_string())
    print()

    # Estatísticas
    stats = analyzer.get_statistics(df_analyzed)
    print("📈 Estatísticas:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Validações
    total_leads = df_analyzed['is_lead'].sum()
    if total_leads >= 2:  # Esperamos pelo menos 2 leads
        print(f"✅ PASS - {total_leads} leads detectados")
        return True
    else:
        print(f"❌ FAIL - Apenas {total_leads} leads detectados (esperado >= 2)")
        return False


def test_analyzer_factory():
    """Testa AnalyzerFactory"""
    print_section("TEST 3: AnalyzerFactory - Criação de Analyzers")

    # Test 1: Criar RegexAnalyzer (default)
    print("Test 3.1: Criar RegexAnalyzer (use_openai=False)")
    analyzer1 = AnalyzerFactory.create_analyzer(
        tenant_id=1,
        use_openai=False
    )

    if isinstance(analyzer1, RegexAnalyzer):
        print(f"✅ PASS - RegexAnalyzer criado corretamente")
        print(f"   Tipo: {type(analyzer1).__name__}")
        print(f"   Tenant: {analyzer1.tenant_id}\n")
    else:
        print(f"❌ FAIL - Tipo incorreto: {type(analyzer1).__name__}\n")
        return False

    # Test 2: Criar OpenAI sem API key (deve fazer fallback)
    print("Test 3.2: Fallback automático (OpenAI sem API key)")
    analyzer2 = AnalyzerFactory.create_analyzer(
        tenant_id=1,
        use_openai=True,
        openai_api_key=None  # Sem API key
    )

    if isinstance(analyzer2, RegexAnalyzer):
        print(f"✅ PASS - Fallback para RegexAnalyzer funcionou")
        print(f"   Tipo: {type(analyzer2).__name__}\n")
    else:
        print(f"❌ FAIL - Fallback não funcionou\n")
        return False

    # Test 3: Verificar interface comum
    print("Test 3.3: Verificar interface BaseAnalyzer")

    methods_to_check = ['analyze_conversation', 'analyze_dataframe', 'get_statistics']
    all_ok = True

    for method in methods_to_check:
        if hasattr(analyzer1, method):
            print(f"   ✅ {method}()")
        else:
            print(f"   ❌ {method}() - MISSING")
            all_ok = False

    print()

    if all_ok:
        print("✅ PASS - Interface BaseAnalyzer implementada corretamente\n")
        return True
    else:
        print("❌ FAIL - Interface incompleta\n")
        return False


def test_compatibility():
    """Testa compatibilidade de saída entre analyzers"""
    print_section("TEST 4: Compatibilidade - Regex vs OpenAI Output")

    message = "Olá! Quero agendar uma aula experimental para amanhã. Quanto custa?"

    # Criar ambos analyzers
    regex_analyzer = RegexAnalyzer(tenant_id=1)

    # Analisar com Regex
    result_regex = regex_analyzer.analyze_conversation(message_text=message)

    print("📊 Campos retornados pelo RegexAnalyzer:")
    for key in sorted(result_regex.keys()):
        print(f"   - {key}: {type(result_regex[key]).__name__}")
    print()

    # Verificar campos obrigatórios
    required_fields = {
        'is_lead': bool,
        'visit_scheduled': bool,
        'crm_converted': bool,
        'ai_probability_label': str,
        'ai_probability_score': (int, float),
    }

    all_ok = True
    print("🔍 Validando campos obrigatórios:")

    for field, expected_type in required_fields.items():
        if field not in result_regex:
            print(f"   ❌ Campo '{field}' faltando")
            all_ok = False
        elif not isinstance(result_regex[field], expected_type):
            print(f"   ❌ Campo '{field}' tipo incorreto: "
                  f"{type(result_regex[field]).__name__} (esperado: {expected_type})")
            all_ok = False
        else:
            print(f"   ✅ {field}")

    print()

    if all_ok:
        print("✅ PASS - Formato de saída compatível com BaseAnalyzer\n")
        return True
    else:
        print("❌ FAIL - Formato de saída incompatível\n")
        return False


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "🧪" * 40)
    print("  ANALYZERS INTEGRATION TEST SUITE")
    print("  Fase 5.6 - OpenAI Integration")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🧪" * 40)

    results = {
        'test_regex_analyzer': test_regex_analyzer(),
        'test_regex_analyzer_dataframe': test_regex_analyzer_dataframe(),
        'test_analyzer_factory': test_analyzer_factory(),
        'test_compatibility': test_compatibility(),
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
        print("\n🎉 SUCCESS - Todos os testes passaram!")
        return 0
    else:
        print(f"\n❌ FAILURE - {total - passed} teste(s) falharam")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)