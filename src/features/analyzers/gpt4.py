"""
GPT-4 Analyzer - Análise de Conversas com OpenAI GPT-4
Analisa conversas usando GPT-4 para gerar insights precisos e personalizados
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text

load_dotenv()

# Configuração OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

# Configuração do banco local
LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST')
LOCAL_DB_PORT = os.getenv('LOCAL_DB_PORT')
LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME')
LOCAL_DB_USER = os.getenv('LOCAL_DB_USER')
LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD')


def get_local_engine():
    """Cria engine para banco local"""
    from urllib.parse import quote_plus
    password_encoded = quote_plus(LOCAL_DB_PASSWORD)
    connection_string = f"postgresql://{LOCAL_DB_USER}:{password_encoded}@{LOCAL_DB_HOST}:{LOCAL_DB_PORT}/{LOCAL_DB_NAME}"
    return create_engine(connection_string)


def get_analysis_prompt() -> str:
    """
    Retorna o prompt otimizado para análise de conversas da AllpFit
    """
    return """Você é um analista especializado em conversas de leads de academias de crossfit (AllpFit).

Sua tarefa é analisar a conversa completa entre o lead e a academia e extrair as seguintes informações em formato JSON:

{
  "nome_mapeado_bot": "string - nome completo do lead que o bot descobriu durante a conversa (se mencionado)",
  "condicao_fisica": "string - opções: Sedentário | Iniciante | Intermediário | Avançado | Não mencionado",
  "objetivo": "string - opções: Perda de peso | Ganho de massa muscular | Condicionamento físico | Saúde geral | Estética/Definição | Não mencionado",
  "probabilidade_conversao": "number - de 0 a 5, onde:",
  "visita_agendada": "boolean - true se houve confirmação de agendamento de visita, false caso contrário",
  "analise_ia": "string - análise detalhada com 3-5 parágrafos explicando:",
  "sugestao_disparo": "string - sugestão específica de mensagem para enviar ao lead"
}

CRITÉRIOS DE PROBABILIDADE DE CONVERSÃO (0-5):

5 - ALTÍSSIMA: Lead agendou visita OU pediu para matricular OU perguntou sobre pagamento/contrato OU confirmou que vai começar
4 - ALTA: Lead perguntou valores E horários E demonstrou interesse claro ("quero", "vou pensar", "preciso ver minha agenda")
3 - MÉDIA: Lead fez múltiplas perguntas (valor, horário, planos) mas não demonstrou urgência ou comprometimento
2 - BAIXA: Lead fez poucas perguntas genéricas ou respondeu apenas com "ok", "entendi" sem aprofundar
1 - MUITO BAIXA: Lead demonstrou objeções (caro, longe, sem tempo) ou respostas muito curtas e secas
0 - NULA: Lead não respondeu adequadamente, mandou apenas "oi" ou mensagens sem sentido, ou claramente não está interessado

ESTRUTURA DA ANÁLISE IA (analise_ia):
Parágrafo 1: Resumo do perfil do lead (condição física, objetivo, contexto pessoal mencionado)
Parágrafo 2: Nível de engajamento e sinais de interesse (perguntas feitas, tom da conversa, urgência)
Parágrafo 3: Objeções ou barreiras identificadas (se houver)
Parágrafo 4: Oportunidades e pontos fortes para abordagem
Parágrafo 5: Recomendação de estratégia de conversão

SUGESTÃO DE DISPARO (sugestao_disparo):
- Deve ser uma mensagem PERSONALIZADA baseada no perfil e interesse do lead
- Mencionar especificamente o objetivo do lead e condição física
- Incluir call-to-action claro (agendar visita, tirar dúvidas, etc)
- Usar tom humanizado e empático
- Máximo 3-4 frases

NOME MAPEADO BOT (nome_mapeado_bot):
- Extrair o NOME COMPLETO que o bot perguntou e o lead respondeu durante a conversa
- Procurar por perguntas do tipo: "Qual é o seu nome?", "Como você se chama?", "Me diz seu nome"
- O nome deve ser EXATAMENTE como o lead forneceu (primeiro e último nome se possível)
- Se o lead NÃO forneceu seu nome durante a conversa, retornar string vazia ""
- Não usar o nome do contato do sistema, apenas o que foi dito na conversa

DETECÇÃO DE VISITA AGENDADA (visita_agendada):
- Marcar TRUE se houver CONFIRMAÇÃO EXPLÍCITA de agendamento na conversa
- Palavras-chave para TRUE: "visita agendada", "agendamento confirmado", "já agendei", "te espero", "vejo você", "nos vemos"
- Marcar FALSE se o lead apenas perguntou sobre visita, mas NÃO confirmou
- Marcar FALSE se ainda está em negociação ou pensando
- A confirmação pode vir tanto do atendente quanto do próprio lead aceitando

IMPORTANTE:
- Analise TODO o histórico de mensagens, não apenas as últimas
- Considere o contexto completo da conversa
- Se não houver informação suficiente, use "Não mencionado"
- Seja preciso e objetivo na probabilidade
- A análise deve ser útil para a equipe de vendas tomar decisões

Retorne APENAS o JSON, sem texto adicional antes ou depois."""


def analyze_with_gpt4(conversation_text: str, contact_name: str, message_count: int, retry_count: int = 3) -> Optional[Dict]:
    """
    Analisa uma conversa usando GPT-4

    Args:
        conversation_text: Texto completo da conversa
        contact_name: Nome do contato
        message_count: Número de mensagens do contato
        retry_count: Número de tentativas em caso de erro

    Returns:
        Dict com análise ou None em caso de erro
    """
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY não configurada")
        return None

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Preparar mensagem do usuário
    user_message = f"""NOME DO LEAD: {contact_name}
TOTAL DE MENSAGENS DO LEAD: {message_count}

CONVERSA COMPLETA:
{conversation_text}

Analise esta conversa e retorne o JSON com as informações solicitadas."""

    for attempt in range(retry_count):
        try:
            # Chamar GPT-4
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": get_analysis_prompt()},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Baixa temperatura para análises mais consistentes
                max_tokens=1500,
                response_format={"type": "json_object"}  # Força resposta em JSON
            )

            # Extrair resposta
            content = response.choices[0].message.content
            analysis = json.loads(content)

            # Validar campos obrigatórios
            required_fields = ['nome_mapeado_bot', 'condicao_fisica', 'objetivo', 'probabilidade_conversao', 'visita_agendada', 'analise_ia', 'sugestao_disparo']
            for field in required_fields:
                if field not in analysis:
                    print(f"⚠️  Campo obrigatório ausente: {field}")
                    return None

            # Validar probabilidade (0-5)
            prob = analysis.get('probabilidade_conversao')
            if not isinstance(prob, (int, float)) or prob < 0 or prob > 5:
                print(f"⚠️  Probabilidade inválida: {prob}")
                analysis['probabilidade_conversao'] = 0
            else:
                analysis['probabilidade_conversao'] = int(prob)

            print(f"✅ Análise GPT-4 concluída para {contact_name} (prob: {analysis['probabilidade_conversao']})")
            return analysis

        except json.JSONDecodeError as e:
            print(f"⚠️  Erro ao decodificar JSON (tentativa {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2)  # Aguardar antes de tentar novamente
            continue

        except Exception as e:
            print(f"❌ Erro na análise GPT-4 (tentativa {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2)
            continue

    print(f"❌ Falha ao analisar conversa de {contact_name} após {retry_count} tentativas")
    return None


def save_analysis_to_db(engine, conversation_id: int, analysis: Dict, model_name: str = 'gpt-4o'):
    """
    Salva análise no banco de dados (UPSERT)

    Args:
        engine: SQLAlchemy engine
        conversation_id: ID da conversa
        analysis: Dict com análise
        model_name: Nome do modelo usado
    """
    query = text("""
        INSERT INTO conversas_analytics_ai (
            conversation_id,
            nome_mapeado_bot,
            condicao_fisica,
            objetivo,
            analise_ia,
            sugestao_disparo,
            probabilidade_conversao,
            visita_agendada,
            analisado_em,
            modelo_ia
        ) VALUES (
            :conversation_id,
            :nome_mapeado_bot,
            :condicao_fisica,
            :objetivo,
            :analise_ia,
            :sugestao_disparo,
            :probabilidade_conversao,
            :visita_agendada,
            :analisado_em,
            :modelo_ia
        )
        ON CONFLICT (conversation_id)
        DO UPDATE SET
            nome_mapeado_bot = EXCLUDED.nome_mapeado_bot,
            condicao_fisica = EXCLUDED.condicao_fisica,
            objetivo = EXCLUDED.objetivo,
            analise_ia = EXCLUDED.analise_ia,
            sugestao_disparo = EXCLUDED.sugestao_disparo,
            probabilidade_conversao = EXCLUDED.probabilidade_conversao,
            visita_agendada = EXCLUDED.visita_agendada,
            analisado_em = EXCLUDED.analisado_em,
            modelo_ia = EXCLUDED.modelo_ia
    """)

    params = {
        'conversation_id': conversation_id,
        'nome_mapeado_bot': analysis.get('nome_mapeado_bot', ''),
        'condicao_fisica': analysis.get('condicao_fisica', 'Não mencionado'),
        'objetivo': analysis.get('objetivo', 'Não mencionado'),
        'analise_ia': analysis.get('analise_ia', ''),
        'sugestao_disparo': analysis.get('sugestao_disparo', ''),
        'probabilidade_conversao': analysis.get('probabilidade_conversao', 0),
        'visita_agendada': analysis.get('visita_agendada', False),
        'analisado_em': datetime.now(),
        'modelo_ia': model_name
    }

    with engine.connect() as conn:
        conn.execute(query, params)
        conn.commit()


def analyze_and_save(conversation_id: int, conversation_text: str, contact_name: str, message_count: int) -> bool:
    """
    Analisa conversa com GPT-4 e salva no banco

    Args:
        conversation_id: ID da conversa
        conversation_text: Texto completo da conversa
        contact_name: Nome do contato
        message_count: Número de mensagens do contato

    Returns:
        bool: True se sucesso, False se erro
    """
    # Analisar com GPT-4
    analysis = analyze_with_gpt4(conversation_text, contact_name, message_count)

    if not analysis:
        return False

    # Salvar no banco
    engine = get_local_engine()
    save_analysis_to_db(engine, conversation_id, analysis, OPENAI_MODEL)

    return True


def get_conversations_to_analyze(engine, limit: Optional[int] = None) -> List[Dict]:
    """
    Busca conversas que precisam ser analisadas (novas ou atualizadas)

    Args:
        engine: SQLAlchemy engine
        limit: Limite de conversas (None = todas)

    Returns:
        Lista de conversas para analisar
    """
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = text(f"""
        SELECT
            ca.conversation_id,
            ca.message_compiled::text as message_compiled,
            ca.contact_name,
            ca.contact_messages_count,
            ca.last_activity_at,
            ai.analisado_em
        FROM conversas_analytics ca
        LEFT JOIN conversas_analytics_ai ai ON ca.conversation_id = ai.conversation_id
        WHERE
            ca.contact_messages_count > 0
            AND LENGTH(ca.message_compiled::text) > 10
            AND (
                ai.id IS NULL  -- Nunca foi analisada
                OR ca.last_activity_at > ai.analisado_em  -- Foi atualizada após análise
            )
        ORDER BY ca.last_activity_at DESC
        {limit_clause}
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

        conversations = []
        for row in rows:
            conversations.append({
                'conversation_id': row[0],
                'message_compiled': row[1],
                'contact_name': row[2],
                'contact_messages_count': row[3],
                'last_activity_at': row[4],
                'analisado_em': row[5]
            })

        return conversations


def run_gpt4_analysis(limit: Optional[int] = None, verbose: bool = True):
    """
    Executa análise GPT-4 em conversas novas/atualizadas

    Args:
        limit: Limite de conversas para analisar (None = todas)
        verbose: Se True, mostra logs detalhados

    Returns:
        Dict com estatísticas da execução
    """
    start_time = time.time()

    if verbose:
        print("=" * 80)
        print("  GPT-4 ANALYZER - AllpFit Analytics")
        print(f"  Modelo: {OPENAI_MODEL}")
        print(f"  Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    # Conectar ao banco
    engine = get_local_engine()

    # Buscar conversas para analisar
    if verbose:
        print("\n🔍 Buscando conversas para analisar...")

    conversations = get_conversations_to_analyze(engine, limit)
    total = len(conversations)

    if total == 0:
        if verbose:
            print("✅ Nenhuma conversa nova ou atualizada para analisar")
        return {
            'total_found': 0,
            'analyzed': 0,
            'failed': 0,
            'execution_time': time.time() - start_time
        }

    if verbose:
        print(f"📊 Encontradas {total} conversas para analisar")
        print()

    # Analisar conversas
    analyzed = 0
    failed = 0

    for i, conv in enumerate(conversations, 1):
        if verbose:
            status = "NOVA" if conv['analisado_em'] is None else "ATUALIZADA"
            print(f"[{i}/{total}] Analisando {conv['contact_name']} ({status})...")

        success = analyze_and_save(
            conversation_id=conv['conversation_id'],
            conversation_text=conv['message_compiled'],
            contact_name=conv['contact_name'],
            message_count=conv['contact_messages_count']
        )

        if success:
            analyzed += 1
        else:
            failed += 1

        # Pequeno delay para não sobrecarregar a API
        if i < total:
            time.sleep(0.5)

    execution_time = time.time() - start_time

    if verbose:
        print()
        print("=" * 80)
        print("  RESUMO DA EXECUÇÃO")
        print("=" * 80)
        print(f"✅ Analisadas com sucesso: {analyzed}")
        print(f"❌ Falhas: {failed}")
        print(f"⏱️  Tempo total: {execution_time:.2f}s")
        print(f"📊 Média por conversa: {execution_time/total:.2f}s")
        print("=" * 80)

    return {
        'total_found': total,
        'analyzed': analyzed,
        'failed': failed,
        'execution_time': execution_time
    }


if __name__ == '__main__':
    # Executar análise de todas as conversas novas/atualizadas
    run_gpt4_analysis(verbose=True)
