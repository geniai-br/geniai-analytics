"""
CampaignCSVExporter - Exportação CSV para Disparador
=====================================================

Este módulo gera arquivos CSV compatíveis com o sistema de disparo
externo (Disparador), seguindo a especificação documentada.

Formato do CSV:
    telefone,nome,variavel_1,variavel_2
    5511999999999,João,contexto personalizado,oferta da campanha

Autor: Isaac (via Claude Code)
Data: 2025-11-26
"""

import csv
import io
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from .models import CampaignLead, Campaign


class CampaignCSVExporter:
    """
    Exporta dados de campanha para CSV compatível com Disparador.

    Especificação do formato:
    - Coluna 1: telefone (apenas números, com DDI 55)
    - Coluna 2: nome (primeiro nome do lead)
    - Coluna 3+: variáveis do template (variavel_1, variavel_2, etc.)

    Uso:
        >>> exporter = CampaignCSVExporter()
        >>> csv_content, stats = exporter.export(leads, campaign)
        >>> with open("campanha.csv", "w", encoding="utf-8-sig") as f:
        ...     f.write(csv_content)
    """

    # Configurações do formato CSV
    ENCODING = "utf-8"
    DELIMITER = ","
    QUOTECHAR = '"'

    # Limites de caracteres (conforme especificação)
    MAX_LEN_NOME = 50
    MAX_LEN_VAR1 = 200  # variavel_1 ({{2}})
    MAX_LEN_VAR2 = 200  # variavel_2 ({{3}})

    # Colunas do CSV
    COLUMNS = ["telefone", "nome", "variavel_1", "variavel_2"]

    def __init__(
        self,
        add_bom: bool = True,
        include_header: bool = True,
        phone_format: str = "ddi"  # "ddi" (5511...) ou "local" (11...)
    ):
        """
        Inicializa o exportador.

        Args:
            add_bom: Se True, adiciona BOM UTF-8 para Excel
            include_header: Se True, inclui linha de cabeçalho
            phone_format: Formato do telefone ("ddi" ou "local")
        """
        self.add_bom = add_bom
        self.include_header = include_header
        self.phone_format = phone_format

    def _format_phone(self, phone: str) -> str:
        """
        Formata telefone para o padrão do Disparador.

        Remove caracteres não numéricos e garante DDI 55 se necessário.

        Args:
            phone: Telefone em qualquer formato

        Returns:
            Telefone formatado (apenas números)
        """
        if not phone:
            return ""

        # Remove tudo que não é número
        numbers_only = re.sub(r'\D', '', phone)

        # Adiciona DDI 55 se não tiver
        if self.phone_format == "ddi":
            if len(numbers_only) <= 11:  # Sem DDI
                numbers_only = "55" + numbers_only
            elif numbers_only.startswith("55") and len(numbers_only) > 13:
                # Remove DDI duplicado se houver
                numbers_only = numbers_only[:13]

        return numbers_only

    def _sanitize_text(self, text: str, max_len: int, field_name: str = "") -> str:
        """
        Limpa e trunca texto para CSV.

        Remove quebras de linha e caracteres problemáticos.

        Args:
            text: Texto original
            max_len: Tamanho máximo
            field_name: Nome do campo (para log)

        Returns:
            Texto sanitizado
        """
        if not text:
            return ""

        # Remove quebras de linha
        text = text.replace('\n', ' ').replace('\r', ' ')

        # Remove tabs
        text = text.replace('\t', ' ')

        # Remove espaços duplicados
        text = re.sub(r'\s+', ' ', text)

        # Strip
        text = text.strip()

        # Trunca se necessário
        if len(text) > max_len:
            text = text[:max_len - 3] + "..."

        return text

    def _extract_first_name(self, full_name: str) -> str:
        """
        Extrai primeiro nome de um nome completo.

        Args:
            full_name: Nome completo

        Returns:
            Primeiro nome ou "você" se não disponível
        """
        if not full_name:
            return "você"

        # Limpar e pegar primeiro nome
        name = full_name.strip()
        if not name or name.lower() in ["lead", "cliente", "contato", ""]:
            return "você"

        first_name = name.split()[0]

        # Capitalizar corretamente
        return first_name.capitalize()

    def _lead_to_row(self, lead: CampaignLead) -> Dict[str, str]:
        """
        Converte um CampaignLead para linha do CSV.

        Args:
            lead: Lead com variáveis geradas

        Returns:
            Dicionário com as colunas do CSV
        """
        # Nome (var1 ou primeiro nome do contact_name)
        nome = lead.var1 or self._extract_first_name(lead.contact_name)

        return {
            "telefone": self._format_phone(lead.contact_phone),
            "nome": self._sanitize_text(nome, self.MAX_LEN_NOME, "nome"),
            "variavel_1": self._sanitize_text(lead.var2 or "", self.MAX_LEN_VAR1, "variavel_1"),
            "variavel_2": self._sanitize_text(lead.var3 or "", self.MAX_LEN_VAR2, "variavel_2"),
        }

    def export(
        self,
        leads: List[CampaignLead],
        campaign: Optional[Campaign] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Exporta leads para CSV.

        Args:
            leads: Lista de leads processados
            campaign: Campanha (opcional, para metadados)

        Returns:
            Tupla (conteúdo CSV como string, estatísticas)
        """
        output = io.StringIO()

        # Adicionar BOM se configurado (para Excel)
        if self.add_bom:
            output.write('\ufeff')

        writer = csv.DictWriter(
            output,
            fieldnames=self.COLUMNS,
            delimiter=self.DELIMITER,
            quotechar=self.QUOTECHAR,
            quoting=csv.QUOTE_MINIMAL,
            extrasaction='ignore'
        )

        # Cabeçalho
        if self.include_header:
            writer.writeheader()

        # Estatísticas
        stats = {
            "total_leads": len(leads),
            "exported": 0,
            "skipped_no_phone": 0,
            "skipped_no_vars": 0,
        }

        # Processar leads
        for lead in leads:
            # Validações
            if not lead.contact_phone:
                stats["skipped_no_phone"] += 1
                continue

            if not lead.var2 and not lead.var3:
                stats["skipped_no_vars"] += 1
                continue

            # Converter para linha CSV
            row = self._lead_to_row(lead)

            # Escrever linha
            writer.writerow(row)
            stats["exported"] += 1

        csv_content = output.getvalue()

        # Calcular tamanho
        stats["file_size_bytes"] = len(csv_content.encode(self.ENCODING))

        return csv_content, stats

    def export_to_bytes(
        self,
        leads: List[CampaignLead],
        campaign: Optional[Campaign] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Exporta leads para bytes (para download direto).

        Args:
            leads: Lista de leads processados
            campaign: Campanha (opcional)

        Returns:
            Tupla (bytes do CSV, estatísticas)
        """
        csv_content, stats = self.export(leads, campaign)
        return csv_content.encode(self.ENCODING), stats

    def generate_filename(
        self,
        campaign: Campaign,
        suffix: str = ""
    ) -> str:
        """
        Gera nome de arquivo para a exportação.

        Formato: campanha_{slug}_{data}_{hora}.csv

        Args:
            campaign: Campanha
            suffix: Sufixo opcional

        Returns:
            Nome do arquivo
        """
        # Slug da campanha
        slug = campaign.slug or campaign.name.lower().replace(" ", "_")
        slug = re.sub(r'[^a-z0-9_-]', '', slug)[:30]

        # Data/hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        # Montar nome
        filename = f"campanha_{slug}_{timestamp}"
        if suffix:
            filename += f"_{suffix}"
        filename += ".csv"

        return filename

    def preview_rows(
        self,
        leads: List[CampaignLead],
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Gera preview das primeiras linhas do CSV.

        Útil para exibir no dashboard antes de exportar.

        Args:
            leads: Lista de leads
            limit: Máximo de linhas

        Returns:
            Lista de dicionários com as linhas
        """
        rows = []
        for lead in leads[:limit]:
            if lead.contact_phone and (lead.var2 or lead.var3):
                rows.append(self._lead_to_row(lead))
        return rows

    @staticmethod
    def get_format_spec() -> Dict[str, Any]:
        """
        Retorna especificação do formato CSV.

        Útil para documentação e validação.

        Returns:
            Dicionário com especificação
        """
        return {
            "encoding": "UTF-8 with BOM",
            "delimiter": ",",
            "quotechar": '"',
            "columns": [
                {
                    "name": "telefone",
                    "description": "Número de telefone (apenas números, com DDI 55)",
                    "example": "5511999999999",
                    "max_length": 15,
                    "required": True,
                },
                {
                    "name": "nome",
                    "description": "Primeiro nome do lead (variável {{1}})",
                    "example": "João",
                    "max_length": 50,
                    "required": True,
                },
                {
                    "name": "variavel_1",
                    "description": "Contexto personalizado (variável {{2}})",
                    "example": "você perguntou sobre matrícula há alguns dias",
                    "max_length": 200,
                    "required": False,
                },
                {
                    "name": "variavel_2",
                    "description": "Oferta/CTA da campanha (variável {{3}})",
                    "example": "temos uma condição especial para você",
                    "max_length": 200,
                    "required": False,
                },
            ],
            "notes": [
                "Arquivo compatível com sistema Disparador",
                "Use o BOM UTF-8 para abrir corretamente no Excel",
                "Telefones sem DDI terão 55 adicionado automaticamente",
            ]
        }


class CampaignXLSXExporter:
    """
    Exportador para formato XLSX (Excel).

    Requer openpyxl instalado.
    """

    def __init__(self):
        """Inicializa exportador XLSX"""
        try:
            import openpyxl
            self._openpyxl = openpyxl
        except ImportError:
            raise ImportError(
                "openpyxl não está instalado. "
                "Instale com: pip install openpyxl"
            )

    def export(
        self,
        leads: List[CampaignLead],
        campaign: Optional[Campaign] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Exporta leads para XLSX.

        Args:
            leads: Lista de leads
            campaign: Campanha

        Returns:
            Tupla (bytes do arquivo, estatísticas)
        """
        wb = self._openpyxl.Workbook()
        ws = wb.active
        ws.title = "Campanha"

        # Cabeçalhos
        headers = ["telefone", "nome", "variavel_1", "variavel_2"]
        ws.append(headers)

        # Formatar cabeçalhos
        for cell in ws[1]:
            cell.font = self._openpyxl.styles.Font(bold=True)

        # CSV exporter para reutilizar lógica
        csv_exporter = CampaignCSVExporter(add_bom=False)

        stats = {"exported": 0, "skipped": 0}

        for lead in leads:
            if not lead.contact_phone:
                stats["skipped"] += 1
                continue

            row = csv_exporter._lead_to_row(lead)
            ws.append([row["telefone"], row["nome"], row["variavel_1"], row["variavel_2"]])
            stats["exported"] += 1

        # Ajustar largura das colunas
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 50

        # Salvar em bytes
        output = io.BytesIO()
        wb.save(output)
        xlsx_bytes = output.getvalue()

        stats["file_size_bytes"] = len(xlsx_bytes)
        stats["total_leads"] = len(leads)

        return xlsx_bytes, stats
