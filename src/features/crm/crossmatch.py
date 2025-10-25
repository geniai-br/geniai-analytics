#!/usr/bin/env python3
"""
Cruza base Excel do EVO CRM com conversas do bot
Identifica conversões reais (leads que falaram com bot ANTES de entrar no CRM)
"""

import sys
import os
from pathlib import Path
import pandas as pd
import psycopg2
from datetime import datetime
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import Config


def normalizar_telefone(telefone_original):
    """
    Normaliza telefone removendo DDI e DDD, retorna múltiplas versões para match
    Exemplos:
        '55 83988439500' -> ['988439500', '88439500'] (com e sem 9)
        '55 (83) 99886-9874' -> ['998869874', '98869874']
        '+558388439500' -> ['88439500', '988439500']
    """
    if pd.isna(telefone_original):
        return []

    # Remove tudo que não é dígito
    apenas_digitos = re.sub(r'\D', '', str(telefone_original))

    # Remove DDI (55) e DDD (83 ou outros 2 dígitos) = remove 4 primeiros dígitos
    # Fica com o número puro (8 ou 9 dígitos)
    if len(apenas_digitos) >= 12:  # 55 + 83 + 9 dígitos
        numero_puro = apenas_digitos[4:]  # Remove DDI+DDD (5583)
    elif len(apenas_digitos) >= 11:  # 83 + 9 dígitos (sem DDI)
        numero_puro = apenas_digitos[2:]  # Remove apenas DDD
    elif len(apenas_digitos) >= 10:  # Pode ser 83 + 8 dígitos
        numero_puro = apenas_digitos[2:]  # Remove DDD
    else:
        numero_puro = apenas_digitos  # Usa como está

    # Retorna AMBAS as versões: com 9 e sem 9
    versoes = []

    # Se tem 9 dígitos e começa com 9, adiciona com e sem o 9
    if len(numero_puro) == 9 and numero_puro[0] == '9':
        versoes.append(numero_puro)        # Com 9: 988439500
        versoes.append(numero_puro[1:])    # Sem 9: 88439500
    # Se tem 8 dígitos, tenta adicionar o 9 também
    elif len(numero_puro) == 8:
        versoes.append(numero_puro)        # Sem 9: 88439500
        versoes.append('9' + numero_puro)  # Com 9: 988439500
    else:
        versoes.append(numero_puro)

    return versoes


def formatar_data(data):
    """Formata data para string dd/mm/yyyy"""
    if pd.isna(data):
        return None

    # Se já é datetime, formata
    if isinstance(data, (pd.Timestamp, datetime)):
        return data.strftime('%d/%m/%Y')

    # Se é string, retorna como está
    return str(data)


def get_db_connection():
    """Cria conexão com banco local usando config centralizado"""
    Config.validate_local_db()

    conn_params = {
        'host': Config.LOCAL_DB_HOST,
        'port': Config.LOCAL_DB_PORT,
        'database': Config.LOCAL_DB_NAME,
        'user': Config.LOCAL_DB_USER,
    }

    if Config.LOCAL_DB_PASSWORD:
        conn_params['password'] = Config.LOCAL_DB_PASSWORD

    return psycopg2.connect(**conn_params)


def main(excel_path=None):
    print("="*80)
    print("🔗 CRUZANDO BASE EXCEL EVO COM CONVERSAS DO BOT")
    print("="*80)

    # 1. Carregar Excel
    print("\n📊 Carregando base_evo.xlsx...")
    if not excel_path:
        # Busca na pasta data/input primeiro, depois na raiz
        excel_path = os.path.join(Config.DATA_DIR, 'input', 'base_evo.xlsx')
        if not os.path.exists(excel_path):
            excel_path = 'base_evo.xlsx'

    if not os.path.exists(excel_path):
        print(f"❌ Arquivo não encontrado: {excel_path}")
        print(f"   Por favor, coloque o arquivo base_evo.xlsx em data/input/")
        return

    df_evo = pd.read_excel(excel_path)

    print(f"✅ {len(df_evo)} clientes carregados do Excel")
    print(f"   Colunas: {', '.join(df_evo.columns.tolist())}")

    # 2. Normalizar telefones
    print("\n📞 Normalizando telefones (removendo DDI/DDD, gerando versões com/sem 9)...")
    df_evo['telefone_versoes'] = df_evo['Telefone/celular'].apply(normalizar_telefone)

    # Remover linhas sem telefone
    df_evo = df_evo[df_evo['telefone_versoes'].apply(lambda x: len(x) > 0)]
    print(f"✅ {len(df_evo)} clientes com telefone válido")

    # Mostrar amostra
    print("\n   Exemplos de normalização:")
    for i, row in df_evo.head(5).iterrows():
        print(f"   {row['Telefone/celular']} -> {row['telefone_versoes']}")

    # 3. Buscar conversas do bot
    print("\n🤖 Buscando conversas do bot...")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.conversation_id,
            c.contact_phone,
            c.contact_name,
            c.conversation_created_at,
            c.mc_last_message_at,
            c.contact_messages_count
        FROM conversas_analytics c
        WHERE c.contact_messages_count > 0
          AND c.contact_phone IS NOT NULL
          AND c.contact_name <> 'Isaac'
    """)

    conversas_bot = {}
    for conv_id, phone, name, created_at, last_msg, msg_count in cur.fetchall():
        # Normalizar telefone - gera versões com e sem 9
        versoes = normalizar_telefone(phone)

        # Adiciona TODAS as versões no dicionário (para facilitar lookup)
        for versao in versoes:
            conversas_bot[versao] = {
                'conversation_id': conv_id,
                'nome_bot': name,
                'telefone': phone,
                'conversa_criada_em': created_at,
                'ultima_mensagem': last_msg,
                'total_mensagens': msg_count
            }

    print(f"✅ {len(conversas_bot)} conversas únicas do bot (por telefone)")

    # 4. CRUZAR!
    print("\n🔗 Cruzando dados...")
    conversoes = []
    conversoes_encontradas = set()  # Para evitar duplicatas

    for idx, cliente in df_evo.iterrows():
        versoes_tel = cliente['telefone_versoes']

        # Tenta match com QUALQUER uma das versões do telefone
        conversa = None
        tel_matched = None

        for versao in versoes_tel:
            if versao in conversas_bot:
                conversa = conversas_bot[versao]
                tel_matched = versao
                break

        if conversa and conversa['conversation_id'] not in conversoes_encontradas:
            # Evita duplicatas (mesmo conversation_id)
            conversoes_encontradas.add(conversa['conversation_id'])

            # Verificar se conversou ANTES de entrar no CRM
            data_cadastro_crm = pd.to_datetime(cliente.get('Data do cadastro'), errors='coerce', dayfirst=True)
            conversa_criada = conversa['conversa_criada_em']

            conversou_antes = True  # Default
            dias_para_conversao = None

            if data_cadastro_crm and conversa_criada:
                # Calcula diferença em dias
                dias_para_conversao = (data_cadastro_crm.date() - conversa_criada.date()).days

                # Considera conversão se foi no mesmo dia ou antes
                # (mesmo que tenha conversado algumas horas depois do cadastro)
                conversou_antes = dias_para_conversao >= 0

            # CONVERSÃO!
            conversoes.append({
                'conversation_id': conversa['conversation_id'],
                'nome_bot': conversa['nome_bot'],
                'nome_crm': cliente.get('Nome', ''),
                'telefone': conversa['telefone'],
                'telefone_normalizado': tel_matched,
                'conversa_criada_em': conversa['conversa_criada_em'],
                'cadastro_crm_em': data_cadastro_crm,
                'dias_para_conversao': dias_para_conversao,
                'total_mensagens': conversa['total_mensagens'],
                'conversou_antes_crm': conversou_antes,
                'id_cliente_crm': cliente.get('IdCliente'),
                'email_crm': cliente.get('Email')
            })

    # RESULTADOS
    print("\n" + "="*80)
    print("📊 RESULTADOS")
    print("="*80)
    print(f"Total de clientes no Excel (EVO):  {len(df_evo)}")
    print(f"Total de conversas do bot:         {len(conversas_bot)}")
    print(f"")
    print(f"✅ CONVERSÕES ENCONTRADAS:         {len(conversoes)} 🎯")

    conversoes_reais = [c for c in conversoes if c['conversou_antes_crm']]
    print(f"   └─ Conversaram ANTES do CRM:    {len(conversoes_reais)} (conversões reais)")

    if len(df_evo) > 0:
        taxa = (len(conversoes) / len(df_evo)) * 100
        taxa_real = (len(conversoes_reais) / len(df_evo)) * 100
        print(f"\n💰 TAXA DE CONVERSÃO:")
        print(f"   Total: {taxa:.1f}%")
        print(f"   Real (bot → CRM): {taxa_real:.1f}%")

    # Mostrar conversões
    if conversoes_reais:
        print(f"\n✅ CONVERSÕES REAIS (Bot → CRM):")
        print("-"*80)
        for i, c in enumerate(conversoes_reais, 1):
            dias = f"({c['dias_para_conversao']} dias)" if c['dias_para_conversao'] else ""
            print(f"{i}. {c['nome_crm']} (Bot: {c['nome_bot']})")
            print(f"   {c['telefone']} (normalizado: {c['telefone_normalizado']})")
            print(f"   Conversa: {c['conversa_criada_em'].strftime('%d/%m/%Y') if c['conversa_criada_em'] else 'N/A'} → " +
                  f"CRM: {c['cadastro_crm_em'].strftime('%d/%m/%Y') if pd.notna(c['cadastro_crm_em']) else 'N/A'} {dias}")
            print(f"   Mensagens: {c['total_mensagens']}")
            print()

    # 5. Salvar no banco
    print(f"\n💾 Salvando no banco de dados...")

    # Criar tabela se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversas_crm_match_real (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER,
            nome_bot VARCHAR(255),
            nome_crm VARCHAR(255),
            telefone VARCHAR(50),
            telefone_8dig VARCHAR(20),
            origem VARCHAR(50) DEFAULT 'Agente IA',
            conversa_criada_em TIMESTAMP,
            cadastro_crm_em DATE,
            dias_para_conversao INTEGER,
            total_mensagens INTEGER,
            conversou_antes_crm BOOLEAN,
            id_cliente_crm INTEGER,
            email_crm VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Limpar dados antigos
    cur.execute("DELETE FROM conversas_crm_match_real")

    # Inserir conversões REAIS
    for c in conversoes_reais:
        cur.execute("""
            INSERT INTO conversas_crm_match_real
            (conversation_id, nome_bot, nome_crm, telefone, telefone_8dig, origem,
             conversa_criada_em, cadastro_crm_em, dias_para_conversao,
             total_mensagens, conversou_antes_crm, id_cliente_crm, email_crm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            c['conversation_id'],
            c['nome_bot'],
            c['nome_crm'],
            c['telefone'],
            c['telefone_normalizado'],
            'Agente IA',  # Origem padrão
            c['conversa_criada_em'],
            c['cadastro_crm_em'],
            c['dias_para_conversao'],
            c['total_mensagens'],
            c['conversou_antes_crm'],
            c['id_cliente_crm'],
            c['email_crm']
        ))

    conn.commit()
    print(f"✅ {len(conversoes_reais)} conversões reais salvas na tabela conversas_crm_match_real!")

    # 6. Salvar relatório
    reports_dir = os.path.join(Config.DATA_DIR, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(reports_dir, f"conversoes_excel_{timestamp}.txt")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE CONVERSÕES: EXCEL EVO → BOT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(f"Clientes EVO (Excel): {len(df_evo)}\n")
        f.write(f"Conversas do bot: {len(conversas_bot)}\n")
        f.write(f"Conversões reais: {len(conversoes_reais)}\n")
        f.write(f"Taxa: {taxa_real:.1f}%\n\n")

        f.write("CONVERSÕES REAIS (Bot → CRM):\n")
        f.write("-"*80 + "\n")
        for c in conversoes_reais:
            f.write(f"{c['nome_crm']} (Bot: {c['nome_bot']})\n")
            f.write(f"  Tel: {c['telefone']} (normalizado: {c['telefone_normalizado']})\n")
            f.write(f"  Conversa: {c['conversa_criada_em'].strftime('%d/%m/%Y') if c['conversa_criada_em'] else 'N/A'}\n")
            f.write(f"  CRM: {c['cadastro_crm_em'].strftime('%d/%m/%Y') if pd.notna(c['cadastro_crm_em']) else 'N/A'}\n")
            f.write(f"  Dias: {c['dias_para_conversao']}\n")
            f.write(f"  Mensagens: {c['total_mensagens']}\n\n")

    print(f"\n💾 Relatório salvo: {report_file}")

    cur.close()
    conn.close()

    print("\n✅ Processo concluído!")
    print(f"\n🎯 CONVERSÕES REAIS: {len(conversoes_reais)} leads do bot viraram clientes do CRM")
    print(f"📈 TAXA: {taxa_real:.1f}%")


if __name__ == '__main__':
    main()
