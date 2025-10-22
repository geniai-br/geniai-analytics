"""
Integração com EVO CRM API
Busca membros e vendas da academia
"""

import requests
from requests.auth import HTTPBasicAuth
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


class EvoCRM:
    """Cliente para API do EVO CRM"""

    def __init__(self, dns: str, api_token: str):
        """
        Inicializa cliente EVO CRM

        Args:
            dns: DNS da academia (username)
            api_token: Token da API (password)
        """
        self.dns = dns
        self.api_token = api_token
        self.base_url = "https://evo-integracao-api.w12app.com.br"
        self.auth = HTTPBasicAuth(dns, api_token)

        # Rate limiting
        self.requests_this_minute = 0
        self.last_request_time = datetime.now()

    def _check_rate_limit(self):
        """
        Verifica rate limit (40 req/min)
        Aguarda se necessário
        """
        now = datetime.now()

        # Reset contador a cada minuto
        if (now - self.last_request_time).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.last_request_time = now

        # Se atingiu limite, aguardar
        if self.requests_this_minute >= 40:
            wait_time = 60 - (now - self.last_request_time).total_seconds()
            if wait_time > 0:
                print(f"⚠️  Rate limit atingido. Aguardando {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.requests_this_minute = 0
                self.last_request_time = datetime.now()

        self.requests_this_minute += 1

    def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """
        Faz requisição à API com tratamento de erros

        Args:
            method: GET, POST, etc
            endpoint: Endpoint da API (ex: /api/v2/members)
            params: Query parameters

        Returns:
            dict: Resposta da API
        """
        self._check_rate_limit()

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                params=params,
                timeout=30
            )

            if response.status_code == 429:
                print("⚠️  Rate limit excedido (429). Aguardando 60s...")
                time.sleep(60)
                return self._make_request(method, endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            print(f"❌ Erro HTTP: {e}")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return None

    def get_member_by_phone(self, phone: str) -> Optional[Dict]:
        """
        Busca membro por telefone

        Args:
            phone: Telefone no formato 11987654321

        Returns:
            dict: Dados do membro ou None se não encontrado
        """
        # Limpar telefone (remover caracteres especiais)
        phone_clean = ''.join(filter(str.isdigit, phone))

        params = {
            'phone': phone_clean,
            'status': 1,  # Apenas ativos
            'showMemberships': True,  # Incluir dados de membership
            'take': 1  # Apenas o primeiro resultado
        }

        result = self._make_request('GET', '/api/v2/members', params)

        if result and len(result) > 0:
            return result[0]

        return None

    def get_members_by_phones(self, phones: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Busca múltiplos membros por telefone

        Args:
            phones: Lista de telefones

        Returns:
            dict: {phone: member_data} ou {phone: None} se não encontrado
        """
        results = {}

        for i, phone in enumerate(phones):
            if i > 0 and i % 10 == 0:
                print(f"   Processados {i}/{len(phones)} telefones...")

            member = self.get_member_by_phone(phone)
            results[phone] = member

        return results

    def get_member_sales(
        self,
        id_member: int,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Busca vendas de um membro específico

        Args:
            id_member: ID do membro no EVO
            date_start: Data inicial (default: 30 dias atrás)
            date_end: Data final (default: hoje)

        Returns:
            list: Lista de vendas
        """
        if date_start is None:
            date_start = datetime.now() - timedelta(days=30)
        if date_end is None:
            date_end = datetime.now()

        params = {
            'idMember': id_member,
            'dateSaleStart': date_start.strftime('%Y-%m-%d'),
            'dateSaleEnd': date_end.strftime('%Y-%m-%d'),
            'take': 100
        }

        result = self._make_request('GET', '/api/v2/sales', params)

        return result if result else []

    def get_all_active_members(
        self,
        conversion_date_start: Optional[datetime] = None,
        take: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """
        Busca todos os membros ativos

        Args:
            conversion_date_start: Data inicial de conversão
            take: Registros por página (max 50)
            skip: Registros a pular

        Returns:
            list: Lista de membros
        """
        params = {
            'status': 1,
            'showMemberships': True,
            'take': min(take, 50),
            'skip': skip
        }

        if conversion_date_start:
            params['conversionDateStart'] = conversion_date_start.strftime('%Y-%m-%d')

        result = self._make_request('GET', '/api/v2/members', params)

        return result if result else []

    def get_member_by_id(self, id_member: int) -> Optional[Dict]:
        """
        Busca membro por ID

        Args:
            id_member: ID do membro

        Returns:
            dict: Dados do membro
        """
        result = self._make_request('GET', f'/api/v2/members/{id_member}')
        return result


# Singleton para reutilizar conexão
_evo_client = None


def get_evo_client() -> EvoCRM:
    """
    Retorna cliente EVO CRM singleton

    Returns:
        EvoCRM: Cliente configurado
    """
    global _evo_client

    if _evo_client is None:
        # Buscar credenciais do ambiente
        dns = os.getenv('EVO_DNS', 'allpfit')
        token = os.getenv('EVO_API_TOKEN', 'AF61C223-2C8D-4619-94E3-0A5A37D1CD8D')

        _evo_client = EvoCRM(dns, token)

    return _evo_client


# Exemplo de uso
if __name__ == '__main__':
    print("🔌 Testando integração com EVO CRM...")

    client = get_evo_client()

    # Teste 1: Buscar membro por telefone
    print("\n📞 Teste 1: Buscar por telefone")
    test_phone = "11987654321"  # Substitua por um telefone real
    member = client.get_member_by_phone(test_phone)

    if member:
        print(f"✅ Membro encontrado: {member.get('firstName')} {member.get('lastName')}")
        print(f"   ID: {member.get('idMember')}")
        print(f"   Email: {member.get('email')}")
        print(f"   Data conversão: {member.get('conversionDate')}")
    else:
        print(f"❌ Nenhum membro encontrado com telefone {test_phone}")

    # Teste 2: Buscar vendas
    if member:
        print(f"\n💰 Teste 2: Buscar vendas do membro {member.get('idMember')}")
        sales = client.get_member_sales(member.get('idMember'))

        if sales:
            print(f"✅ Encontradas {len(sales)} vendas:")
            for sale in sales[:3]:
                print(f"   - Venda #{sale.get('idSale')} em {sale.get('saleDate')}")
        else:
            print("   Nenhuma venda encontrada")

    print("\n✅ Teste concluído!")
