#!/usr/bin/env python3
"""
Busca membros ativos no EVO e cruza com leads do bot
Simples: membro ativo = conversão
"""

import psycopg2
from src.integrations.evo_crm import get_evo_client
from datetime import datetime
import time

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'allpfit',
    'user': 'isaac',
    'password': 'AllpFit2024@Analytics'
}

def main():
    print("="*80)
    print("🔗 CRUZANDO MEMBROS DO EVO COM LEADS DO BOT")
    print("="*80)

    client = get_evo_client()

    # 1. Buscar TODOS os membros ativos do EVO (paginação)
    print("\n👥 Buscando membros ativos do EVO...")

    all_members = []
    skip = 0
    take = 50  # Máximo por página

    while True:
        print(f"   Página {skip//take + 1}...")

        members = client.get_all_active_members(take=take, skip=skip)

        if not members or len(members) == 0:
            break

        all_members.extend(members)
        print(f"      + {len(members)} membros")

        if len(members) < take:
            break

        skip += take
        time.sleep(0.5)  # Respeitar rate limit

    print(f"\n✅ Total de membros ativos: {len(all_members)}")

    # 2. Extrair telefones dos membros
    print(f"\n📞 Extraindo telefones...")

    members_phones = {}
    for member in all_members:
        contacts = member.get('contacts', [])

        # Procurar telefone nos contatos
        phone = None
        email = None

        for contact in contacts:
            contact_type = contact.get('contactType', '')

            if contact_type == 'Cellphone' and not phone:
                # Telefone = DDI + description
                ddi = contact.get('ddi') or ''
                description = contact.get('description') or ''
                phone = str(ddi) + str(description)

            elif contact_type == 'E-mail' and not email:
                email = contact.get('description')

        if phone:
            phone_clean = ''.join(filter(str.isdigit, phone))
            # Também guardar últimos 11 dígitos (DDD + número) para match mais flexível
            phone_last11 = phone_clean[-11:] if len(phone_clean) >= 11 else phone_clean
            members_phones[phone_clean] = {
                'id_member': member.get('idMember'),
                'name': f"{member.get('firstName', '')} {member.get('lastName', '')}",
                'phone': phone,
                'email': email or member.get('email'),
                'conversion_date': member.get('conversionDate'),
                'status': member.get('status')
            }

    print(f"✅ Membros com telefone: {len(members_phones)}/{len(all_members)}")

    # 3. Buscar leads do bot
    print(f"\n📊 Buscando leads do bot...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            conversation_id,
            contact_phone,
            contact_name,
            conversation_date
        FROM conversas_analytics
        WHERE contact_messages_count > 0
          AND contact_phone IS NOT NULL
          AND contact_name <> 'Isaac'
    """)

    bot_leads = []
    for conv_id, phone, name, conv_date in cur.fetchall():
        phone_clean = ''.join(filter(str.isdigit, phone))
        bot_leads.append({
            'conversation_id': conv_id,
            'phone': phone,
            'phone_clean': phone_clean,
            'name': name,
            'conv_date': conv_date
        })

    print(f"✅ Leads do bot: {len(bot_leads)}")

    # 4. CRUZAR!
    print(f"\n🔗 Cruzando dados...")

    matches = []
    not_converted = []

    for lead in bot_leads:
        phone_clean = lead['phone_clean']
        # Tentar match exato primeiro
        member = members_phones.get(phone_clean)

        # Se não encontrou, tentar pelos últimos 11 dígitos (mais flexível)
        if not member:
            phone_last11 = phone_clean[-11:] if len(phone_clean) >= 11 else phone_clean
            for evo_phone, evo_data in members_phones.items():
                evo_last11 = evo_phone[-11:] if len(evo_phone) >= 11 else evo_phone
                if phone_last11 == evo_last11:
                    member = evo_data
                    break

        if member:
            # CONVERSÃO! ✅
            matches.append({
                'conversation_id': lead['conversation_id'],
                'bot_name': lead['name'],
                'bot_phone': lead['phone'],
                'conv_date': lead['conv_date'],
                'evo_id': member['id_member'],
                'evo_name': member['name'],
                'evo_email': member['email'],
                'conversion_date': member['conversion_date']
            })
        else:
            # Não converteu
            not_converted.append(lead)

    # RESULTADOS
    print("\n" + "="*80)
    print("📊 RESULTADOS")
    print("="*80)
    print(f"Total de membros ativos no EVO:    {len(all_members)}")
    print(f"Membros com telefone cadastrado:   {len(members_phones)}")
    print(f"Total de leads do bot:             {len(bot_leads)}")
    print(f"")
    print(f"✅ CONVERSÕES (Bot → Membro):      {len(matches)} 🎯")
    print(f"❌ NÃO CONVERTERAM:                {len(not_converted)}")

    if len(bot_leads) > 0:
        conversion_rate = (len(matches) / len(bot_leads)) * 100
        print(f"\n💰 TAXA DE CONVERSÃO: {conversion_rate:.1f}%")

    # Mostrar conversões
    if matches:
        print(f"\n✅ PRIMEIROS 20 LEADS QUE VIRARAM MEMBROS:")
        print("-"*80)
        for i, m in enumerate(matches[:20], 1):
            days_to_convert = None
            if m['conv_date'] and m['conversion_date']:
                try:
                    conv_datetime = datetime.fromisoformat(str(m['conversion_date']))
                    days = (conv_datetime.date() - m['conv_date']).days
                    days_to_convert = f"({days} dias)"
                except:
                    days_to_convert = ""

            print(f"{i}. {m['evo_name']}")
            print(f"   Conversa: {m['conv_date']} → Membro: {m['conversion_date']} {days_to_convert or ''}")
            print(f"   EVO ID: {m['evo_id']} | {m['bot_phone']}")
            print()

        if len(matches) > 20:
            print(f"... e mais {len(matches) - 20} conversões")

    # Salvar relatório
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"relatorio_conversoes_{timestamp}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE CONVERSÕES BOT → EVO\n")
        f.write("="*80 + "\n\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(f"Membros ativos EVO: {len(all_members)}\n")
        f.write(f"Leads do bot: {len(bot_leads)}\n")
        f.write(f"Conversões: {len(matches)}\n")
        f.write(f"Taxa: {conversion_rate:.1f}%\n\n")

        f.write("CONVERSÕES:\n")
        f.write("-"*80 + "\n")
        for m in matches:
            f.write(f"{m['evo_name']} (ID: {m['evo_id']})\n")
            f.write(f"  Bot: {m['bot_name']} | {m['bot_phone']}\n")
            f.write(f"  Conversa: {m['conv_date']} → Conversão: {m['conversion_date']}\n\n")

    print(f"\n💾 Relatório: {report_file}")

    # Salvar no banco
    print(f"\n💾 Salvando no banco de dados...")

    # Criar tabela se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversas_crm_match (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER,
            bot_name VARCHAR(255),
            bot_phone VARCHAR(50),
            conv_date DATE,
            evo_id_member INTEGER,
            evo_name VARCHAR(255),
            evo_email VARCHAR(255),
            evo_conversion_date DATE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Limpar dados antigos
    cur.execute("DELETE FROM conversas_crm_match")

    # Inserir conversões
    for m in matches:
        cur.execute("""
            INSERT INTO conversas_crm_match
            (conversation_id, bot_name, bot_phone, conv_date,
             evo_id_member, evo_name, evo_email, evo_conversion_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            m['conversation_id'],
            m['bot_name'],
            m['bot_phone'],
            m['conv_date'],
            m['evo_id'],
            m['evo_name'],
            m['evo_email'],
            m['conversion_date']
        ))

    conn.commit()
    print(f"✅ {len(matches)} conversões salvas no banco!")

    cur.close()
    conn.close()

    print("\n✅ Processo concluído!")
    print(f"\n🎯 VENDAS/TRÁFEGO: {len(matches)} leads viraram membros")
    print(f"📈 TAXA: {conversion_rate:.1f}%")

if __name__ == '__main__':
    main()
