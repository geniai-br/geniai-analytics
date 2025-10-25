"""
Rule-Based Analyzer - Análise de Conversas com Regras
Analisa conversas usando regras heurísticas (sem IA)
"""

import os
import re
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

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


def extract_condicao_fisica(text: str) -> str:
    """Extrai condição física da conversa usando palavras-chave"""
    text_lower = text.lower()

    if any(word in text_lower for word in ['sedentário', 'parado', 'não faço exercício', 'não treino']):
        return 'Sedentário'
    elif any(word in text_lower for word in ['iniciante', 'começando', 'nunca treinei']):
        return 'Iniciante'
    elif any(word in text_lower for word in ['intermediário', 'treino há alguns meses', 'já treino']):
        return 'Intermediário'
    elif any(word in text_lower for word in ['avançado', 'treino há anos', 'atleta']):
        return 'Avançado'
    else:
        return 'Não mencionado'


def extract_objetivo(text: str) -> str:
    """Extrai objetivo da conversa usando palavras-chave"""
    text_lower = text.lower()

    # Peso/emagrecimento
    if any(word in text_lower for word in ['emagrecer', 'perder peso', 'perda de peso', 'queimar gordura', 'secar']):
        return 'Perda de peso'
    # Ganho de massa
    elif any(word in text_lower for word in ['ganhar massa', 'hipertrofia', 'músculo', 'crescer', 'bulking']):
        return 'Ganho de massa muscular'
    # Condicionamento
    elif any(word in text_lower for word in ['condicionamento', 'resistência', 'cardio', 'fôlego']):
        return 'Condicionamento físico'
    # Saúde
    elif any(word in text_lower for word in ['saúde', 'médico recomendou', 'colesterol', 'diabetes', 'pressão']):
        return 'Saúde geral'
    # Estética
    elif any(word in text_lower for word in ['definição', 'shape', 'corpo', 'estética', 'verão']):
        return 'Estética/Definição'
    else:
        return 'Não mencionado'


def generate_analysis(text: str, contact_name: str, message_count: int) -> str:
    """
    Gera análise DETALHADA da conversa com 3 tópicos aprofundados
    Esta análise serve como BASE/CONTEXTO para a IA OpenAI refinar depois
    """
    text_lower = text.lower()

    # Detectar sinais específicos de interesse (análise completa)
    perguntou_valor = 'valor' in text_lower or 'preço' in text_lower or 'quanto custa' in text_lower or 'mensalidade' in text_lower or 'custo' in text_lower
    perguntou_horario = 'horário' in text_lower or 'que horas' in text_lower or 'funciona' in text_lower or 'abre' in text_lower or 'fecha' in text_lower
    agendou = 'agendar' in text_lower or 'visita' in text_lower or 'ir aí' in text_lower or 'conhecer' in text_lower or 'aparecer' in text_lower
    perguntou_planos = 'plano' in text_lower or 'modalidade' in text_lower or 'aula' in text_lower or 'treino' in text_lower
    urgente = any(word in text_lower for word in ['urgente', 'hoje', 'agora', 'rápido', 'amanhã', 'já', 'logo'])
    positivo = any(word in text_lower for word in ['quero', 'queria', 'gostaria', 'interesse', 'garantir', 'matricular', 'adorei', 'legal', 'perfeito'])
    respondeu_bot = 'ok' in text_lower or 'obrigad' in text_lower or 'entendi' in text_lower or 'certo' in text_lower or 'sim' in text_lower
    duvidas = 'dúvida' in text_lower or 'duvida' in text_lower or 'como funciona' in text_lower or 'pode' in text_lower or 'preciso saber' in text_lower
    negativo = any(word in text_lower for word in ['não consigo', 'não posso', 'caro', 'longe', 'difícil', 'não tenho'])

    # Calcular engajamento detalhado
    if message_count >= 15:
        engajamento = "muito alto"
        eng_score = 5
    elif message_count >= 10:
        engajamento = "alto"
        eng_score = 4
    elif message_count >= 5:
        engajamento = "moderado"
        eng_score = 3
    elif message_count >= 3:
        engajamento = "baixo"
        eng_score = 2
    else:
        engajamento = "muito baixo"
        eng_score = 1

    # RESUMO CONTEXTUAL DETALHADO
    if agendou and message_count >= 5:
        resumo = f"{contact_name} demonstrou FORTE interesse em agendar visita/conhecer. Engajamento {engajamento} ({message_count} mensagens)."
    elif perguntou_valor and perguntou_horario:
        resumo = f"{contact_name} perguntou sobre valores E horários (duplo interesse). Engajamento {engajamento} ({message_count} msgs)."
    elif perguntou_valor or perguntou_planos:
        resumo = f"{contact_name} questionou sobre valores/planos (interesse inicial). Engajamento {engajamento} ({message_count} msgs)."
    elif message_count >= 10:
        resumo = f"{contact_name} teve conversa LONGA sem perguntas diretas. Engajamento {engajamento} ({message_count} msgs)."
    elif message_count >= 3:
        resumo = f"{contact_name} teve interação moderada. Engajamento {engajamento} ({message_count} msgs)."
    else:
        resumo = f"{contact_name} teve interação BREVE/SUPERFICIAL. Engajamento {engajamento} ({message_count} msgs)."

    # TÓPICO 1: Por que demonstrou ou NÃO demonstrou interesse (análise profunda)
    sinais_positivos = []
    if agendou:
        sinais_positivos.append("tentou agendar visita/conhecer estrutura")
    if perguntou_valor:
        sinais_positivos.append("perguntou preços/valores/mensalidade")
    if perguntou_horario:
        sinais_positivos.append("questionou horários de funcionamento")
    if perguntou_planos:
        sinais_positivos.append("perguntou planos/modalidades/aulas")
    if positivo:
        sinais_positivos.append("usou linguagem positiva (quero/gostaria/interesse)")
    if urgente:
        sinais_positivos.append("demonstrou urgência temporal (hoje/agora)")
    if duvidas:
        sinais_positivos.append("buscou esclarecer dúvidas sobre funcionamento")

    if sinais_positivos:
        topico1 = f"✓ SINAIS DE INTERESSE IDENTIFICADOS:\n   {chr(10).join(['• ' + s for s in sinais_positivos])}"
    else:
        if message_count <= 2:
            topico1 = "✗ SEM SINAIS DE INTERESSE:\n   • Apenas saudação inicial ou mensagem única\n   • Não fez perguntas sobre a academia\n   • Não respondeu ao bot"
        else:
            topico1 = "~ INTERESSE INCERTO/BAIXO:\n   • Conversa sem perguntas diretas sobre valores/horários/agendamento\n   • Engajamento sem objetividade"

    # TÓPICO 2: Análise de Pontos Positivos vs Negativos (balanceamento)
    pontos_positivos = []
    pontos_negativos = []

    # Analisar positivos
    if message_count >= 15:
        pontos_positivos.append("engajamento ALTÍSSIMO (15+ mensagens)")
    elif message_count >= 10:
        pontos_positivos.append("alta quantidade de mensagens (10+)")
    elif message_count >= 5:
        pontos_positivos.append("engajamento moderado (5+ msgs)")

    if agendou:
        pontos_positivos.append("TENTOU agendar/conhecer (alto interesse)")
    if perguntou_valor or perguntou_horario:
        pontos_positivos.append("fez perguntas PRÁTICAS e objetivas")
    if positivo:
        pontos_positivos.append("linguagem receptiva e interessada")
    if respondeu_bot:
        pontos_positivos.append("respondeu às mensagens do bot (engajado)")
    if urgente:
        pontos_positivos.append("demonstrou urgência (quer resolver logo)")
    if duvidas and message_count >= 3:
        pontos_positivos.append("buscou esclarecer dúvidas (interesse genuíno)")

    # Analisar negativos
    if message_count <= 2:
        pontos_negativos.append("muito poucas mensagens (baixo engajamento)")
    if message_count == 1:
        pontos_negativos.append("NÃO respondeu ao bot (mensagem única)")
    if not perguntou_valor and not perguntou_horario and not agendou and not perguntou_planos:
        pontos_negativos.append("NÃO fez perguntas específicas sobre a academia")
    if negativo:
        pontos_negativos.append("mencionou OBJEÇÕES (caro/longe/difícil)")
    if message_count >= 10 and not perguntou_valor and not agendou:
        pontos_negativos.append("conversa longa MAS sem perguntas práticas (só papo)")

    if pontos_positivos and pontos_negativos:
        topico2 = f"⚖️ BALANÇO DA CONVERSA:\n   Positivos: {', '.join(pontos_positivos)}\n   Negativos: {', '.join(pontos_negativos)}"
    elif pontos_positivos:
        topico2 = f"✓ PONTOS POSITIVOS DOMINANTES:\n   {', '.join(pontos_positivos)}\n   (Nenhum ponto negativo significativo)"
    else:
        topico2 = f"✗ PONTOS NEGATIVOS DOMINANTES:\n   {', '.join(pontos_negativos)}\n   (Poucos ou nenhum ponto positivo)"

    # TÓPICO 3: Vale a pena trabalhar? (recomendação com score)
    score = 0
    if agendou:
        score += 3
    if perguntou_valor and message_count >= 5:
        score += 2
    elif perguntou_valor:
        score += 1
    if perguntou_horario:
        score += 1
    if perguntou_planos:
        score += 1
    if positivo:
        score += 1
    if urgente:
        score += 2
    if eng_score >= 4:
        score += 2
    elif eng_score >= 3:
        score += 1
    if negativo:
        score -= 2
    if message_count == 1:
        score -= 1

    # Recomendação baseada no score total
    if score >= 6:
        topico3 = f"🎯 RECOMENDAÇÃO: LEAD QUENTE (Score: {score}/10+)\n   • Prioridade: MÁXIMA\n   • Vale MUITO a pena trabalhar\n   • Ação: Follow-up IMEDIATO (ligação ou mensagem personalizada)\n   • Potencial de conversão: ALTO"
    elif score >= 4:
        topico3 = f"⭐ RECOMENDAÇÃO: LEAD MORNO (Score: {score}/10)\n   • Prioridade: ALTA\n   • Vale bastante a pena trabalhar\n   • Ação: Mensagem personalizada nas próximas horas\n   • Potencial de conversão: MÉDIO-ALTO"
    elif score >= 2:
        topico3 = f"💡 RECOMENDAÇÃO: LEAD ENGAJADO (Score: {score}/10)\n   • Prioridade: MÉDIA\n   • Pode valer a pena tentar\n   • Ação: Reativar com promoção/oferta especial\n   • Potencial de conversão: MÉDIO"
    elif score >= 0:
        topico3 = f"📊 RECOMENDAÇÃO: LEAD FRIO (Score: {score}/10)\n   • Prioridade: BAIXA\n   • Pouco interesse demonstrado\n   • Ação: Campanha de reativação em massa\n   • Potencial de conversão: BAIXO"
    else:
        topico3 = f"❄️ RECOMENDAÇÃO: LEAD MUITO FRIO (Score: {score}/10)\n   • Prioridade: NÃO PRIORIZAR\n   • Interesse mínimo ou inexistente\n   • Ação: Não investir tempo agora\n   • Potencial de conversão: MUITO BAIXO"

    # Montar análise completa formatada
    return f"{resumo}\n\n{topico1}\n\n{topico2}\n\n{topico3}"


def generate_sugestao_disparo(text: str, objetivo: str, contact_name: str) -> str:
    """Gera mensagem personalizada para follow-up"""
    text_lower = text.lower()

    # Se perguntou sobre valor
    if 'valor' in text_lower or 'preço' in text_lower:
        return f"Oi {contact_name}! Vi que você perguntou sobre nossos planos. Temos uma promoção especial essa semana! Posso te passar os detalhes?"

    # Se perguntou sobre horário
    if 'horário' in text_lower:
        return f"E aí {contact_name}! Nossos horários são super flexíveis. Que tal agendar uma visita e conhecer a estrutura? Quando seria melhor pra você?"

    # Se mencionou objetivo
    if objetivo and objetivo != 'Não mencionado':
        if 'Perda de peso' in objetivo:
            return f"Oi {contact_name}! Nossos treinos para emagrecimento são focados e com acompanhamento. Vamos conversar?"
        elif 'Ganho de massa' in objetivo:
            return f"Fala {contact_name}! Temos equipamentos top para hipertrofia. Quando pode conhecer?"

    # Genérico
    return f"E aí {contact_name}! Notei seu interesse na academia. Que tal marcar uma visita sem compromisso? Temos promoção rolando!"


def calculate_probabilidade(text: str, message_count: int) -> int:
    """Calcula probabilidade de conversão (0-5) baseado em regras"""
    text_lower = text.lower()
    score = 0

    # Quantidade de mensagens (max 2 pontos)
    if message_count >= 15:
        score += 2
    elif message_count >= 10:
        score += 1.5
    elif message_count >= 5:
        score += 1
    elif message_count >= 3:
        score += 0.5

    # Perguntas específicas (+1 ponto cada, max 2)
    if 'valor' in text_lower or 'preço' in text_lower:
        score += 1
    if 'horário' in text_lower or 'funciona' in text_lower:
        score += 0.5
    if 'modalidade' in text_lower or 'aula' in text_lower:
        score += 0.5

    # Agendamento ou visita (+2 pontos)
    if 'agendar' in text_lower or 'visita' in text_lower or 'ir aí' in text_lower:
        score += 2

    # Urgência (+1 ponto)
    if any(word in text_lower for word in ['urgente', 'hoje', 'agora', 'rápido']):
        score += 1

    # Normalizar para 0-5
    score = min(5, max(0, int(round(score))))

    return score


def analyze_conversation_with_rules(conversation_id: int, conversa_compilada: str,
                                   contact_name: str, message_count: int) -> Dict:
    """
    Analisa uma conversa usando regras heurísticas

    Returns:
        Dict com os campos analisados
    """
    print(f"[RULE] Analisando conversa {conversation_id} ({contact_name})...")

    # Extrair informações
    condicao_fisica = extract_condicao_fisica(conversa_compilada)
    objetivo = extract_objetivo(conversa_compilada)
    analise = generate_analysis(conversa_compilada, contact_name, message_count)
    sugestao = generate_sugestao_disparo(conversa_compilada, objetivo, contact_name)
    probabilidade = calculate_probabilidade(conversa_compilada, message_count)

    print(f"[RULE] ✅ Conversa {conversation_id} analisada - Probabilidade: {probabilidade}/5")

    return {
        'condicao_fisica': condicao_fisica,
        'objetivo': objetivo,
        'analise_ia': analise,
        'sugestao_disparo': sugestao,
        'probabilidade_conversao': probabilidade
    }


def save_analysis_to_db(conversation_id: int, analysis: Dict, engine):
    """Salva análise no banco de dados"""
    try:
        with engine.connect() as conn:
            # Verificar se já existe
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
                    "modelo": "rule-based",
                    "versao": 1
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
                    "modelo": "rule-based",
                    "versao": 1
                })
                conn.commit()
                print(f"[DB] ✅ Análise salva: conversa {conversation_id}")

    except Exception as e:
        print(f"[DB] ❌ Erro ao salvar análise: {e}")


def analyze_and_save(conversation_id: int, conversa_compilada: str,
                    contact_name: str, message_count: int) -> bool:
    """Analisa conversa com regras e salva no banco"""

    if not conversa_compilada or len(conversa_compilada.strip()) < 10:
        print(f"[RULE] ⚠️  Conversa {conversation_id} muito curta, pulando")
        return False

    # Analisar
    analysis = analyze_conversation_with_rules(
        conversation_id, conversa_compilada, contact_name, message_count
    )

    # Salvar
    engine = get_local_engine()
    save_analysis_to_db(conversation_id, analysis, engine)

    return True
