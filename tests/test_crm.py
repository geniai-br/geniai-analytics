"""
Testes para funcionalidades de CRM
"""
import pytest
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from features.crm.crossmatch import normalizar_telefone, formatar_data
from datetime import datetime
import pandas as pd


class TestNormalizarTelefone:
    """Testes para normalização de telefone."""

    def test_normalizar_telefone_com_ddi_ddd(self):
        """Test normalization with DDI and DDD."""
        result = normalizar_telefone('55 83988439500')
        assert '988439500' in result
        assert '88439500' in result

    def test_normalizar_telefone_com_9_digitos(self):
        """Test normalization with 9 digits."""
        result = normalizar_telefone('988439500')
        assert '988439500' in result
        assert '88439500' in result

    def test_normalizar_telefone_com_8_digitos(self):
        """Test normalization with 8 digits."""
        result = normalizar_telefone('88439500')
        assert '88439500' in result
        assert '988439500' in result

    def test_normalizar_telefone_com_formatacao(self):
        """Test normalization with formatting."""
        result = normalizar_telefone('(83) 98843-9500')
        assert '988439500' in result or '8843' in str(result)

    def test_normalizar_telefone_vazio(self):
        """Test normalization with empty value."""
        result = normalizar_telefone(None)
        assert result == []

    def test_normalizar_telefone_retorna_lista(self):
        """Test that normalization returns a list."""
        result = normalizar_telefone('83988439500')
        assert isinstance(result, list)
        assert len(result) > 0


class TestFormatarData:
    """Testes para formatação de data."""

    def test_formatar_data_com_datetime(self):
        """Test date formatting with datetime object."""
        dt = datetime(2025, 10, 25, 14, 30)
        result = formatar_data(dt)
        assert result == '25/10/2025'

    def test_formatar_data_com_timestamp(self):
        """Test date formatting with pandas Timestamp."""
        dt = pd.Timestamp('2025-10-25')
        result = formatar_data(dt)
        assert '25' in result
        assert '10' in result
        assert '2025' in result

    def test_formatar_data_vazia(self):
        """Test date formatting with None."""
        result = formatar_data(None)
        assert result is None

    def test_formatar_data_com_string(self):
        """Test date formatting with string."""
        result = formatar_data('2025-10-25')
        assert result == '2025-10-25'
