"""
Script: Análise de Categorias de Conversas (Multi-Tenant)
=========================================================

Analisa todas as conversas de todos os tenants para identificar
os tipos de conversas mais frequentes e propor categorias.

Autor: Isaac (via Claude Code)
Data: 2025-11-19
"""

import os
import sys
import json
import re
from collections import Counter, defaultdict
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Carregar variáveis de ambiente
load_dotenv()

def get_db_connection():
    """Conecta ao banco de dados"""
    return psycopg2.connect(
        host='localhost',
        database='geniai_analytics',
        user='johan_geniai',
        password='vlVMVM6UNz2yYSBlzodPjQvZh'
    )

# ===================================================================
# PADRÕES DE CATEGORIZAÇÃO (baseados em palavras-chave)
# ===================================================================
CATEGORY_PATTERNS = {
    'AGENDAMENTO': {
        'keywords': [
            r'\bagendar\b', r'\bagendamento\b', r'\bmarcar\b', r'\bhorário\b',
            r'\bvisita\b', r'\bdata\b', r'\bhora\b', r'\bquando\b',
            r'\bexperimental\b', r'\btreino experimental\b', r'\baula experimental\b',
            r'\bpode ser\b', r'\bagendado\b', r'\bconfirmado\b'
        ],
        'weight': 2  # Prioridade alta
    },

    'PREÇO/PLANOS': {
        'keywords': [
            r'\bpreço\b', r'\bvalor\b', r'\bcusto\b', r'\bquanto\b',
            r'\bplano\b', r'\bmensalidade\b', r'\bmatrícula\b',
            r'\bpagamento\b', r'\bforma de pagamento\b', r'\bpagar\b',
            r'\bpix\b', r'\bcartão\b', r'\bparcela\b'
        ],
        'weight': 2
    },

    'INFORMAÇÕES GERAIS': {
        'keywords': [
            r'\binformação\b', r'\bsobre\b', r'\bcomo funciona\b',
            r'\bfunciona\b', r'\bdetalhes\b', r'\bme fala\b',
            r'\bme explica\b', r'\bquero saber\b', r'\bgostaria de saber\b'
        ],
        'weight': 1
    },

    'LOCALIZAÇÃO/ENDEREÇO': {
        'keywords': [
            r'\bonde fica\b', r'\bendereço\b', r'\blocalização\b',
            r'\bcomo chegar\b', r'\bmapa\b', r'\blocaliza\b',
            r'\bfica onde\b', r'\bpertinho\b', r'\bperto\b'
        ],
        'weight': 1
    },

    'HORÁRIOS DE FUNCIONAMENTO': {
        'keywords': [
            r'\bhorário de funcionamento\b', r'\bhorários\b', r'\bfunciona\b',
            r'\babre\b', r'\bfecha\b', r'\batende\b', r'\babre quando\b',
            r'\bfecha quando\b', r'\bfim de semana\b', r'\bsábado\b', r'\bdomingo\b'
        ],
        'weight': 1
    },

    'CANCELAMENTO/RECLAMAÇÃO': {
        'keywords': [
            r'\bcancelar\b', r'\bcancelamento\b', r'\bdesistir\b',
            r'\breclamação\b', r'\bproblema\b', r'\bnão funcionou\b',
            r'\binsatisfeito\b', r'\bruim\b', r'\bpéssimo\b'
        ],
        'weight': 2
    },

    'SUPORTE/DÚVIDAS': {
        'keywords': [
            r'\bajuda\b', r'\bdúvida\b', r'\bnão entendi\b',
            r'\bcomo faz\b', r'\bcomo faço\b', r'\bpreciso de ajuda\b',
            r'\bsuporte\b', r'\batendimento\b'
        ],
        'weight': 1
    },

    'RENOVAÇÃO/CONTRATO': {
        'keywords': [
            r'\brenovar\b', r'\brenovação\b', r'\bcontrato\b',
            r'\bvencimento\b', r'\bprazo\b', r'\bperiodo\b',
            r'\bextender\b', r'\bestender\b'
        ],
        'weight': 1
    },

    'WHATSAPP/CONTATO': {
        'keywords': [
            r'\bwhatsapp\b', r'\bwpp\b', r'\btelefone\b',
            r'\bcontato\b', r'\bfalar\b', r'\bligar\b',
            r'\bmensagem\b', r'\bnúmero\b'
        ],
        'weight': 0.5  # Baixa prioridade (muito genérico)
    }
}

def extract_messages_text(message_compiled):
    """Extrai texto limpo das mensagens compiladas"""
    try:
        if isinstance(message_compiled, str):
            messages = json.loads(message_compiled)
        else:
            messages = message_compiled

        texts = []
        for msg in messages:
            # Pular mensagens do sistema
            if msg.get('message_type') in [2, 3]:
                continue

            text = msg.get('text', '')
            if text:
                texts.append(text.lower())

        return ' '.join(texts)
    except:
        return ''

def categorize_conversation(message_text, analise_ia=''):
    """
    Categoriza uma conversa baseada em palavras-chave.

    Returns:
        tuple: (categoria_primaria, score, categorias_detectadas)
    """
    # Combinar mensagens e análise IA para melhor contexto
    full_text = f"{message_text} {analise_ia}".lower()

    category_scores = {}

    for category, config in CATEGORY_PATTERNS.items():
        score = 0
        matches = []

        for pattern in config['keywords']:
            if re.search(pattern, full_text):
                score += config['weight']
                matches.append(pattern)

        if score > 0:
            category_scores[category] = {
                'score': score,
                'matches': matches
            }

    # Se não encontrou nenhuma categoria, retornar OUTROS
    if not category_scores:
        return 'OUTROS', 0, []

    # Ordenar por score
    sorted_categories = sorted(
        category_scores.items(),
        key=lambda x: x[1]['score'],
        reverse=True
    )

    # Categoria primária (maior score)
    primary_category = sorted_categories[0][0]
    primary_score = sorted_categories[0][1]['score']

    # Todas as categorias detectadas
    all_categories = [cat for cat, _ in sorted_categories]

    return primary_category, primary_score, all_categories

def analyze_all_conversations():
    """Analisa todas as conversas e gera estatísticas de categorias"""
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    conversation_id,
                    tenant_id,
                    contact_name,
                    message_compiled,
                    analise_ia,
                    status_resolucao,
                    nivel_interesse,
                    precisa_remarketing
                FROM conversations_analytics
                WHERE is_lead = TRUE
                  AND message_compiled IS NOT NULL
                ORDER BY conversation_id
            """)

            conversations = cur.fetchall()

            print(f"📊 Analisando {len(conversations)} conversas de todos os tenants...")
            print()

            # Estatísticas globais
            category_counter = Counter()
            tenant_categories = defaultdict(Counter)
            category_examples = defaultdict(list)

            # Processar cada conversa
            for i, conv in enumerate(conversations, 1):
                message_text = extract_messages_text(conv['message_compiled'])
                analise_ia = conv.get('analise_ia', '')

                category, score, all_categories = categorize_conversation(
                    message_text,
                    analise_ia
                )

                # Contabilizar categoria primária
                category_counter[category] += 1
                tenant_categories[conv['tenant_id']][category] += 1

                # Guardar exemplos (primeiros 3 de cada categoria)
                if len(category_examples[category]) < 3:
                    category_examples[category].append({
                        'conversation_id': conv['conversation_id'],
                        'tenant_id': conv['tenant_id'],
                        'contact_name': conv['contact_name'],
                        'message_preview': message_text[:200] if message_text else '',
                        'score': score,
                        'all_categories': all_categories
                    })

                # Progresso
                if i % 100 == 0:
                    print(f"   Processadas {i}/{len(conversations)} conversas...")

            return {
                'total_conversations': len(conversations),
                'category_counter': category_counter,
                'tenant_categories': tenant_categories,
                'category_examples': category_examples
            }

    finally:
        conn.close()

def print_results(results):
    """Imprime resultados formatados"""
    print("=" * 80)
    print("📊 ANÁLISE DE CATEGORIAS DE CONVERSAS - TODOS OS TENANTS")
    print("=" * 80)
    print()

    total = results['total_conversations']
    category_counter = results['category_counter']
    tenant_categories = results['tenant_categories']
    category_examples = results['category_examples']

    print(f"✅ Total de conversas analisadas: {total}")
    print()

    # ===================================================================
    # DISTRIBUIÇÃO GLOBAL DE CATEGORIAS
    # ===================================================================
    print("=" * 80)
    print("🏆 CATEGORIAS MAIS FREQUENTES (TODOS OS TENANTS)")
    print("=" * 80)
    print()

    sorted_categories = category_counter.most_common()

    print(f"{'CATEGORIA':<30} {'QUANTIDADE':<12} {'%':<8} {'GRÁFICO'}")
    print("-" * 80)

    for category, count in sorted_categories:
        percentage = (count / total * 100)
        bar_length = int(percentage / 2)  # Escala: 50% = 25 chars
        bar = '█' * bar_length

        print(f"{category:<30} {count:<12} {percentage:>6.1f}%  {bar}")

    print()

    # ===================================================================
    # CATEGORIAS POR TENANT
    # ===================================================================
    print("=" * 80)
    print("🏢 DISTRIBUIÇÃO POR TENANT")
    print("=" * 80)
    print()

    for tenant_id in sorted(tenant_categories.keys()):
        tenant_total = sum(tenant_categories[tenant_id].values())
        print(f"Tenant {tenant_id} ({tenant_total} conversas):")
        print("-" * 60)

        for category, count in tenant_categories[tenant_id].most_common(5):
            percentage = (count / tenant_total * 100)
            print(f"  {category:<30} {count:>4} ({percentage:>5.1f}%)")

        print()

    # ===================================================================
    # EXEMPLOS DE CADA CATEGORIA
    # ===================================================================
    print("=" * 80)
    print("💬 EXEMPLOS DE CONVERSAS POR CATEGORIA")
    print("=" * 80)
    print()

    for category in sorted(category_counter.keys()):
        print(f"📁 {category}")
        print("-" * 80)

        for i, example in enumerate(category_examples[category], 1):
            print(f"  Exemplo {i}:")
            print(f"    Conversa: {example['conversation_id']} (Tenant {example['tenant_id']})")
            print(f"    Contato: {example['contact_name']}")
            print(f"    Score: {example['score']}")

            if len(example['all_categories']) > 1:
                print(f"    Outras categorias: {', '.join(example['all_categories'][1:])}")

            preview = example['message_preview'].replace('\n', ' ')[:150]
            print(f"    Preview: {preview}...")
            print()

        print()

    # ===================================================================
    # RECOMENDAÇÕES
    # ===================================================================
    print("=" * 80)
    print("💡 RECOMENDAÇÕES PARA IMPLEMENTAÇÃO")
    print("=" * 80)
    print()

    # Top categorias (> 5% do total)
    significant_categories = [
        cat for cat, count in sorted_categories
        if (count / total * 100) >= 5.0
    ]

    print(f"✅ Categorias principais (≥5%): {len(significant_categories)}")
    for cat in significant_categories:
        count = category_counter[cat]
        pct = (count / total * 100)
        print(f"   • {cat}: {count} conversas ({pct:.1f}%)")

    print()
    print(f"📦 Categoria 'OUTROS' incluirá: {total - sum(category_counter[cat] for cat in significant_categories)} conversas")
    print()

    print("🎨 Sugestão de cores para gráfico:")
    color_map = {
        'AGENDAMENTO': '#28a745 (verde)',
        'PREÇO/PLANOS': '#ffc107 (amarelo)',
        'INFORMAÇÕES GERAIS': '#17a2b8 (azul claro)',
        'LOCALIZAÇÃO/ENDEREÇO': '#6f42c1 (roxo)',
        'HORÁRIOS DE FUNCIONAMENTO': '#fd7e14 (laranja)',
        'CANCELAMENTO/RECLAMAÇÃO': '#dc3545 (vermelho)',
        'SUPORTE/DÚVIDAS': '#20c997 (verde água)',
        'RENOVAÇÃO/CONTRATO': '#6610f2 (índigo)',
        'WHATSAPP/CONTATO': '#6c757d (cinza)',
        'OUTROS': '#adb5bd (cinza claro)'
    }

    for cat in significant_categories + ['OUTROS']:
        color = color_map.get(cat, '#6c757d')
        print(f"   • {cat:<30} {color}")

    print()

def main():
    print("🚀 Iniciando análise de categorias de conversas...")
    print()

    results = analyze_all_conversations()
    print_results(results)

    print("=" * 80)
    print("✅ Análise concluída!")
    print("=" * 80)

if __name__ == '__main__':
    main()