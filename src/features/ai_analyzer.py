"""
AI Analyzer - Análise de Conversas com OpenAI
Analisa conversas de leads para extrair insights e classificar probabilidade de conversão
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
import sqlalchemy
from sqlalchemy import create_engine, text

# Carregar variáveis de ambiente
load_dotenv()

# Configuração OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
OPENAI_PROMPT_VERSION = int(os.getenv('OPENAI_PROMPT_VERSION', 1))

# Configuração do banco local
LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST')
LOCAL_DB_PORT = os.getenv('LOCAL_DB_PORT')
LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME')
LOCAL_DB_USER = os.getenv('LOCAL_DB_USER')
LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD')

# Cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


def get_local_engine():
    """Cria engine para banco local"""
    from urllib.parse import quote_plus
    password_encoded = quote_plus(LOCAL_DB_PASSWORD)
    connection_string = f"postgresql://{LOCAL_DB_USER}:{password_encoded}@{LOCAL_DB_HOST}:{LOCAL_DB_PORT}/{LOCAL_DB_NAME}"
    return create_engine(connection_string)


def build_analysis_prompt(conversa_compilada: str, contact_name: str) -> str:
    """
    Constrói o prompt para análise da conversa

    Args:
        conversa_compilada: Texto completo da conversa
        contact_name: Nome do contato

    Returns:
        Prompt formatado para a IA
    """
    prompt = f"""Você é um analista especializado em conversas de academia/fitness para identificar leads de alta qualidade.

Analise a seguinte conversa entre um lead ({contact_name}) e um chatbot de uma academia:

CONVERSA:
{conversa_compilada}

TAREFA:
Extraia as seguintes informações e forneça sua análise em formato JSON estruturado:

1. **condicao_fisica**: Condição física atual do lead (sedentário/iniciante/intermediário/avançado ou "não mencionado")
2. **objetivo**: Objetivo principal na academia (perda de peso/ganho de massa/condicionamento/saúde geral/outro ou "não mencionado")
3. **analise_ia**: Resumo breve da conversa em 2-3 frases (máximo 200 caracteres), destacando principais pontos e nível de interesse
4. **sugestao_disparo**: Mensagem personalizada e persuasiva para follow-up/remarketing (máximo 300 caracteres), com tom amigável e direto
5. **probabilidade_conversao**: Classifique de 0 a 5:
   - 0: Sem interesse real, não vale follow-up
   - 1: Interesse mínimo, apenas pesquisando
   - 2: Interesse moderado, precisa de mais informações
   - 3: Interesse real, considerando seriamente
   - 4: Alta probabilidade, quase decidido
   - 5: Muito alta probabilidade, pronto para converter

CRITÉRIOS PARA CLASSIFICAÇÃO:
- Lead fez perguntas específicas sobre valores, horários, modalidades? (+pontos)
- Lead demonstrou urgência ou necessidade clara? (+pontos)
- Lead agendou visita ou solicitou contato? (+pontos)
- Lead abandonou a conversa sem conclusão? (-pontos)
- Lead só perguntou informações básicas? (neutro)

RETORNE APENAS O JSON, SEM TEXTO ADICIONAL:
{{
  "condicao_fisica": "valor",
  "objetivo": "valor",
  "analise_ia": "valor",
  "sugestao_disparo": "valor",
  "probabilidade_conversao": numero
}}
"""
    return prompt


def analyze_conversation(conversation_id: int, conversa_compilada: str, contact_name: str) -> Optional[Dict]:
    """
    Analisa uma conversa usando OpenAI GPT-4

    Args:
        conversation_id: ID da conversa
        conversa_compilada: Texto completo da conversa
        contact_name: Nome do contato

    Returns:
        Dict com os campos analisados ou None em caso de erro
    """
    try:
        print(f"[AI] Analisando conversa {conversation_id} ({contact_name})...")

        # Construir prompt
        prompt = build_analysis_prompt(conversa_compilada, contact_name)

        # Chamar OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Você é um analista especializado em qualificação de leads para academias."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Baixa temperatura para respostas mais consistentes
            max_tokens=500,
            response_format={"type": "json_object"}  # Força resposta em JSON
        )

        # Extrair resposta
        content = response.choices[0].message.content
        analysis = json.loads(content)

        # Validar campos obrigatórios
        required_fields = ['condicao_fisica', 'objetivo', 'analise_ia', 'sugestao_disparo', 'probabilidade_conversao']
        for field in required_fields:
            if field not in analysis:
                print(f"[AI] ⚠️  Campo '{field}' ausente na resposta da IA")
                return None

        # Validar probabilidade (0-5)
        prob = analysis['probabilidade_conversao']
        if not isinstance(prob, int) or prob < 0 or prob > 5:
            print(f"[AI] ⚠️  Probabilidade inválida: {prob}")
            return None

        print(f"[AI] ✅ Conversa {conversation_id} analisada - Probabilidade: {prob}/5")

        return analysis

    except json.JSONDecodeError as e:
        print(f"[AI] ❌ Erro ao decodificar JSON da IA: {e}")
        print(f"[AI] Resposta recebida: {content[:200]}...")
        return None

    except Exception as e:
        print(f"[AI] ❌ Erro ao analisar conversa {conversation_id}: {e}")
        return None


def save_analysis_to_db(conversation_id: int, analysis: Dict, engine):
    """
    Salva análise da IA no banco de dados

    Args:
        conversation_id: ID da conversa
        analysis: Dict com campos analisados
        engine: SQLAlchemy engine
    """
    try:
        with engine.connect() as conn:
            # Verificar se já existe análise
            check_query = text("""
                SELECT id FROM conversas_analytics_ai
                WHERE conversation_id = :conv_id
            """)
            existing = conn.execute(check_query, {"conv_id": conversation_id}).fetchone()

            if existing:
                # UPDATE
                update_query = text("""
                    UPDATE conversas_analytics_ai
                    SET condicao_fisica = :condicao,
                        objetivo = :objetivo,
                        analise_ia = :analise,
                        sugestao_disparo = :sugestao,
                        probabilidade_conversao = :probabilidade,
                        analisado_em = NOW(),
                        modelo_ia = :modelo,
                        versao_prompt = :versao,
                        updated_at = NOW()
                    WHERE conversation_id = :conv_id
                """)
                conn.execute(update_query, {
                    "conv_id": conversation_id,
                    "condicao": analysis['condicao_fisica'],
                    "objetivo": analysis['objetivo'],
                    "analise": analysis['analise_ia'],
                    "sugestao": analysis['sugestao_disparo'],
                    "probabilidade": analysis['probabilidade_conversao'],
                    "modelo": OPENAI_MODEL,
                    "versao": OPENAI_PROMPT_VERSION
                })
                conn.commit()
                print(f"[DB] ✅ Análise atualizada: conversa {conversation_id}")

            else:
                # INSERT
                insert_query = text("""
                    INSERT INTO conversas_analytics_ai (
                        conversation_id, condicao_fisica, objetivo,
                        analise_ia, sugestao_disparo, probabilidade_conversao,
                        modelo_ia, versao_prompt
                    ) VALUES (
                        :conv_id, :condicao, :objetivo,
                        :analise, :sugestao, :probabilidade,
                        :modelo, :versao
                    )
                """)
                conn.execute(insert_query, {
                    "conv_id": conversation_id,
                    "condicao": analysis['condicao_fisica'],
                    "objetivo": analysis['objetivo'],
                    "analise": analysis['analise_ia'],
                    "sugestao": analysis['sugestao_disparo'],
                    "probabilidade": analysis['probabilidade_conversao'],
                    "modelo": OPENAI_MODEL,
                    "versao": OPENAI_PROMPT_VERSION
                })
                conn.commit()
                print(f"[DB] ✅ Análise salva: conversa {conversation_id}")

    except Exception as e:
        print(f"[DB] ❌ Erro ao salvar análise: {e}")


def analyze_and_save(conversation_id: int, conversa_compilada: str, contact_name: str) -> bool:
    """
    Analisa conversa e salva no banco (função principal)

    Args:
        conversation_id: ID da conversa
        conversa_compilada: Texto da conversa
        contact_name: Nome do contato

    Returns:
        True se sucesso, False se erro
    """
    # Validar entrada
    if not conversa_compilada or conversa_compilada.strip() == "":
        print(f"[AI] ⚠️  Conversa {conversation_id} vazia, pulando análise")
        return False

    # Analisar com IA
    analysis = analyze_conversation(conversation_id, conversa_compilada, contact_name)

    if not analysis:
        return False

    # Salvar no banco
    engine = get_local_engine()
    save_analysis_to_db(conversation_id, analysis, engine)

    return True


if __name__ == "__main__":
    print("Módulo AI Analyzer carregado com sucesso!")
    print(f"Modelo: {OPENAI_MODEL}")
    print(f"Versão do prompt: {OPENAI_PROMPT_VERSION}")
