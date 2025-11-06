"""
Lead Analyzer - ETL V4 Multi-Tenant
====================================

Responsável por analisar conversas e detectar:
- Leads qualificados (interesse real em comprar/contratar)
- Visitas agendadas (dia/hora marcados)
- Conversões CRM (venda confirmada, contrato assinado)

Usa análise de keywords, padrões regex e regras de negócio.

Fase: 4 - Dashboard Cliente Avançado
Autor: Isaac (via Claude Code)
Data: 2025-11-06
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LeadAnalyzer:
    """Analisa conversas para detectar leads, visitas e conversões"""

    # ========================================================================
    # KEYWORDS DE DETECÇÃO (Configuráveis por tenant no futuro)
    # ========================================================================

    # Keywords de INTERESSE (Lead)
    LEAD_KEYWORDS = [
        # Interesse direto
        r'\bquero\b',
        r'\btenho interesse\b',
        r'\bgostaria\b',
        r'\bpreciso\b',
        r'\bqueria\b',
        r'\bestou interessado\b',
        r'\bestou interessada\b',
        r'\bme interessa\b',

        # Perguntas de compra
        r'\bquanto custa\b',
        r'\bqual.*pre[cç]o\b',
        r'\bvalor\b',
        r'\bplanos?\b',
        r'\bpacotes?\b',
        r'\bpromoc[aã]o\b',
        r'\bdesconto\b',

        # Academia específico
        r'\bmatricula\b',
        r'\bmatr[ií]cula\b',
        r'\baula experimental\b',
        r'\bexperimental\b',
        r'\bquero treinar\b',
        r'\bquero come[cç]ar\b',
        r'\bhorarios?\b',
        r'\bhor[aá]rios?\b',
        r'\bunidades?\b',

        # Urgência
        r'\bquando posso\b',
        r'\bcomo fa[cç]o\b',
        r'\bj[aá] posso\b',
        r'\bhoje mesmo\b',
        r'\bagora\b',
        r'\brapido\b',
        r'\br[aá]pido\b',

        # CrossFit específico
        r'\bcrossfit\b',
        r'\bwod\b',
        r'\bfuncional\b',
        r'\bmuscula[cç][aã]o\b',
        r'\bemagre[cç]\w+\b',
        r'\bperder peso\b',
        r'\bganha.*peso\b',
        r'\bganha.*massa\b',
    ]

    # Keywords de AGENDAMENTO (Visita)
    VISIT_KEYWORDS = [
        # Agendamento explícito
        r'\bquero agendar\b',
        r'\bagenda\b',
        r'\bmarcar.*visita\b',
        r'\bmarcar.*aula\b',
        r'\breservar\b',

        # Datas/horários
        r'\bsegunda\b',
        r'\bter[cç]a\b',
        r'\bquarta\b',
        r'\bquinta\b',
        r'\bsexta\b',
        r'\bs[aá]bado\b',
        r'\bdomingo\b',
        r'\bhoje\b',
        r'\bamanh[aã]\b',
        r'\bsemana que vem\b',
        r'\bpr[oó]xima semana\b',

        # Horários
        r'\b\d{1,2}h\d{0,2}\b',  # 18h, 18h30
        r'\b\d{1,2}:\d{2}\b',     # 18:00
        r'\bmanh[aã]\b',
        r'\btarde\b',
        r'\bnoite\b',

        # Confirmação
        r'\bconfirmado\b',
        r'\bagendado\b',
        r'\bmarcado\b',
        r'\bok.*hor[aá]rio\b',
        r'\bvou.*ir\b',
        r'\bte vejo\b',
        r'\bat[eé] l[aá]\b',
        r'\bat[eé] amanh[aã]\b',
    ]

    # Keywords de CONVERSÃO (CRM)
    CONVERSION_KEYWORDS = [
        # Venda confirmada
        r'\bmatricula realizada\b',
        r'\bmatr[ií]cula realizada\b',
        r'\bmatricula confirmada\b',
        r'\bmatr[ií]cula confirmada\b',
        r'\bmatricula efetuada\b',
        r'\bmatricula.*sucesso\b',

        # Pagamento
        r'\bpago\b',
        r'\bpaguei\b',
        r'\bpagamento\b',
        r'\bpix.*enviado\b',
        r'\bpix.*feito\b',
        r'\bcomprovante\b',
        r'\btransfer[eê]ncia\b',
        r'\bfaturado\b',

        # Contrato/assinatura
        r'\bcontrato assinado\b',
        r'\bcontrato.*pronto\b',
        r'\bassinei\b',
        r'\bassinado\b',
        r'\baceitei.*termo\b',

        # Confirmações admin
        r'\baluno ativo\b',
        r'\bcadastro completo\b',
        r'\bcarteirinha\b',
        r'\bacesso liberado\b',
        r'\bbem[- ]vindo.*equipe\b',

        # Início de atividades
        r'\bcome[cç]o.*treinar\b',
        r'\bprimeira aula\b',
        r'\bj[aá] treinou\b',
        r'\bcheck[- ]in\b',
    ]

    # Keywords NEGATIVAS (filtro de falsos positivos)
    NEGATIVE_KEYWORDS = [
        r'\bn[aã]o quero\b',
        r'\bn[aã]o tenho interesse\b',
        r'\bcancelei\b',
        r'\bdesisti\b',
        r'\bj[aá] [eé] cliente\b',
        r'\bj[aá] sou aluno\b',
        r'\bj[aá] treino\b',
        r'\bapenas.*informa[cç][aã]o\b',
        r'\bs[oó] queria saber\b',
        r'\bcuriosidade\b',
    ]

    def __init__(self, tenant_id: int):
        """
        Inicializa o analisador de leads.

        Args:
            tenant_id: ID do tenant (para logging e configs futuras)
        """
        self.tenant_id = tenant_id

        # Compilar regex para performance
        self.lead_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.LEAD_KEYWORDS]
        self.visit_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.VISIT_KEYWORDS]
        self.conversion_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CONVERSION_KEYWORDS]
        self.negative_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.NEGATIVE_KEYWORDS]

        logger.info(f"LeadAnalyzer inicializado para tenant {tenant_id}")
        logger.info(f"Padrões carregados: {len(self.lead_patterns)} lead, "
                   f"{len(self.visit_patterns)} visit, "
                   f"{len(self.conversion_patterns)} conversion")

    def analyze_conversation(
        self,
        message_text: Optional[str],
        status: Optional[str] = None,
        has_human_intervention: bool = False,
    ) -> Dict[str, any]:
        """
        Analisa uma única conversa e retorna classificações.

        Args:
            message_text: Texto compilado da conversa (todas as mensagens)
            status: Status da conversa (open, resolved, pending)
            has_human_intervention: Se teve intervenção humana

        Returns:
            Dict com:
                - is_lead: bool
                - visit_scheduled: bool
                - crm_converted: bool
                - ai_probability_label: str ('Alto', 'Médio', 'Baixo', 'N/A')
                - ai_probability_score: float (0-100)
                - lead_keywords_found: List[str]
                - visit_keywords_found: List[str]
                - conversion_keywords_found: List[str]

        Example:
            >>> analyzer = LeadAnalyzer(tenant_id=1)
            >>> result = analyzer.analyze_conversation(
            ...     "Olá! Quero agendar uma aula experimental para amanhã às 18h"
            ... )
            >>> result['is_lead']
            True
            >>> result['visit_scheduled']
            True
        """
        # Resultado default
        result = {
            'is_lead': False,
            'visit_scheduled': False,
            'crm_converted': False,
            'ai_probability_label': 'N/A',
            'ai_probability_score': 0.0,
            'lead_keywords_found': [],
            'visit_keywords_found': [],
            'conversion_keywords_found': [],
        }

        # Se não tem texto, retornar default
        if not message_text or not isinstance(message_text, str):
            return result

        # Limpar texto (remover excessos de espaços, quebras de linha)
        text = ' '.join(message_text.split())

        # 1. Verificar keywords NEGATIVAS (filtro de falsos positivos)
        has_negative = any(pattern.search(text) for pattern in self.negative_patterns)

        if has_negative:
            logger.debug(f"Conversa descartada por keyword negativa: {text[:100]}...")
            return result

        # 2. Detectar LEAD
        lead_matches = []
        for pattern in self.lead_patterns:
            matches = pattern.findall(text)
            lead_matches.extend(matches)

        if lead_matches:
            result['is_lead'] = True
            result['lead_keywords_found'] = list(set(lead_matches))  # Remover duplicadas
            logger.debug(f"Lead detectado: {len(lead_matches)} keywords encontradas")

        # 3. Detectar VISITA AGENDADA
        visit_matches = []
        for pattern in self.visit_patterns:
            matches = pattern.findall(text)
            visit_matches.extend(matches)

        if visit_matches:
            result['visit_scheduled'] = True
            result['visit_keywords_found'] = list(set(visit_matches))
            logger.debug(f"Visita detectada: {len(visit_matches)} keywords encontradas")

        # 4. Detectar CONVERSÃO CRM
        conversion_matches = []
        for pattern in self.conversion_patterns:
            matches = pattern.findall(text)
            conversion_matches.extend(matches)

        if conversion_matches:
            result['crm_converted'] = True
            result['conversion_keywords_found'] = list(set(conversion_matches))
            logger.debug(f"Conversão detectada: {len(conversion_matches)} keywords encontradas")

        # 5. Calcular SCORE e LABEL de probabilidade
        score = self._calculate_lead_score(
            lead_count=len(lead_matches),
            visit_count=len(visit_matches),
            conversion_count=len(conversion_matches),
            status=status,
            has_human_intervention=has_human_intervention,
        )

        result['ai_probability_score'] = score
        result['ai_probability_label'] = self._score_to_label(score)

        return result

    def analyze_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analisa um DataFrame completo de conversas.

        Args:
            df: DataFrame com colunas:
                - message_compiled (texto das mensagens)
                - status (opcional)
                - has_human_intervention (opcional)

        Returns:
            DataFrame com colunas adicionadas:
                - is_lead
                - visit_scheduled
                - crm_converted
                - ai_probability_label
                - ai_probability_score

        Example:
            >>> analyzer = LeadAnalyzer(tenant_id=1)
            >>> df_analyzed = analyzer.analyze_dataframe(df)
            >>> df_analyzed['is_lead'].sum()  # Total de leads
            42
        """
        if df.empty:
            logger.warning("DataFrame vazio recebido para análise")
            return df

        logger.info(f"Analisando {len(df)} conversas para tenant {self.tenant_id}")

        # Aplicar análise linha por linha
        results = df.apply(
            lambda row: self.analyze_conversation(
                message_text=row.get('message_compiled', None),
                status=row.get('status', None),
                has_human_intervention=row.get('has_human_intervention', False),
            ),
            axis=1
        )

        # Extrair cada campo do resultado
        df['is_lead'] = results.apply(lambda x: x['is_lead'])
        df['visit_scheduled'] = results.apply(lambda x: x['visit_scheduled'])
        df['crm_converted'] = results.apply(lambda x: x['crm_converted'])
        df['ai_probability_label'] = results.apply(lambda x: x['ai_probability_label'])
        df['ai_probability_score'] = results.apply(lambda x: x['ai_probability_score'])

        # Estatísticas
        lead_count = df['is_lead'].sum()
        visit_count = df['visit_scheduled'].sum()
        conversion_count = df['crm_converted'].sum()

        logger.info(f"Análise concluída: {lead_count} leads, "
                   f"{visit_count} visitas, {conversion_count} conversões")

        return df

    def _calculate_lead_score(
        self,
        lead_count: int,
        visit_count: int,
        conversion_count: int,
        status: Optional[str],
        has_human_intervention: bool,
    ) -> float:
        """
        Calcula score de probabilidade de lead (0-100).

        Fatores considerados:
        - Quantidade de keywords de lead encontradas
        - Quantidade de keywords de agendamento
        - Se tem conversão confirmada
        - Status da conversa (resolved = mais provável)
        - Se teve intervenção humana (agente confirmou)

        Returns:
            float: Score 0-100
        """
        score = 0.0

        # Base: keywords de lead (5 pontos cada, max 50)
        score += min(lead_count * 5, 50)

        # Bônus: agendamento confirmado (+20)
        if visit_count > 0:
            score += 20

        # Bônus: conversão confirmada (+30)
        if conversion_count > 0:
            score += 30

        # Bônus: status resolved (+10, indica conclusão)
        if status == 'resolved':
            score += 10

        # Bônus: intervenção humana (+10, agente confirmou)
        if has_human_intervention:
            score += 10

        # Limitar a 100
        score = min(score, 100.0)

        return round(score, 1)

    def _score_to_label(self, score: float) -> str:
        """
        Converte score numérico em label qualitativo.

        Args:
            score: Score 0-100

        Returns:
            str: 'Alto', 'Médio', 'Baixo', 'N/A'
        """
        if score >= 70:
            return 'Alto'
        elif score >= 40:
            return 'Médio'
        elif score > 0:
            return 'Baixo'
        else:
            return 'N/A'

    def get_statistics(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Calcula estatísticas de conversão.

        Args:
            df: DataFrame com análises feitas

        Returns:
            Dict com estatísticas
        """
        if df.empty:
            return {
                'total_conversations': 0,
                'total_leads': 0,
                'total_visits': 0,
                'total_conversions': 0,
                'conversion_rate': 0.0,
                'visit_rate': 0.0,
            }

        total = len(df)
        leads = df['is_lead'].sum() if 'is_lead' in df.columns else 0
        visits = df['visit_scheduled'].sum() if 'visit_scheduled' in df.columns else 0
        conversions = df['crm_converted'].sum() if 'crm_converted' in df.columns else 0

        return {
            'total_conversations': total,
            'total_leads': int(leads),
            'total_visits': int(visits),
            'total_conversions': int(conversions),
            'conversion_rate': round((conversions / total * 100) if total > 0 else 0, 2),
            'visit_rate': round((visits / leads * 100) if leads > 0 else 0, 2),
            'lead_rate': round((leads / total * 100) if total > 0 else 0, 2),
        }


# ============================================================================
# FUNÇÃO HELPER PARA USAR NO TRANSFORMER
# ============================================================================

def add_lead_analysis(df: pd.DataFrame, tenant_id: int) -> pd.DataFrame:
    """
    Função helper para adicionar análise de leads ao DataFrame.

    Uso no transformer:
        df = add_lead_analysis(df, tenant_id=1)

    Args:
        df: DataFrame de conversas
        tenant_id: ID do tenant

    Returns:
        DataFrame com colunas de análise adicionadas
    """
    analyzer = LeadAnalyzer(tenant_id=tenant_id)
    df_analyzed = analyzer.analyze_dataframe(df)

    # Mostrar estatísticas
    stats = analyzer.get_statistics(df_analyzed)
    logger.info(f"Estatísticas tenant {tenant_id}: {stats}")

    return df_analyzed


# ============================================================================
# TESTE LOCAL
# ============================================================================

if __name__ == "__main__":
    # Teste com conversas fictícias
    test_data = pd.DataFrame([
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

    # Analisar
    analyzer = LeadAnalyzer(tenant_id=1)
    result = analyzer.analyze_dataframe(test_data)

    # Exibir resultados
    print("\n=== RESULTADOS DA ANÁLISE ===\n")
    print(result[['conversation_id', 'is_lead', 'visit_scheduled', 'crm_converted',
                  'ai_probability_label', 'ai_probability_score']])

    # Estatísticas
    stats = analyzer.get_statistics(result)
    print("\n=== ESTATÍSTICAS ===\n")
    for key, value in stats.items():
        print(f"{key}: {value}")
