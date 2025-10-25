"""
Testes de importação de módulos
Garante que todos os módulos principais podem ser importados sem erros
"""
import pytest
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def test_import_shared_config():
    """Test importing shared.config module."""
    from shared import config
    assert hasattr(config, 'Config')


def test_import_shared_database():
    """Test importing shared.database module."""
    from shared import database
    assert database is not None


def test_import_etl_extractor():
    """Test importing ETL extractor module."""
    from features.etl import extractor
    assert hasattr(extractor, 'extract_incremental')


def test_import_etl_transformer():
    """Test importing ETL transformer module."""
    from features.etl import transformer
    assert hasattr(transformer, 'transform_data')


def test_import_etl_loader():
    """Test importing ETL loader module."""
    from features.etl import loader
    assert hasattr(loader, 'load_upsert')


def test_import_analyzers_rule_based():
    """Test importing rule-based analyzer."""
    from features.analyzers import rule_based
    assert rule_based is not None


def test_import_analyzers_gpt4():
    """Test importing GPT-4 analyzer."""
    from features.analyzers import gpt4
    assert gpt4 is not None


def test_import_crm_crossmatch():
    """Test importing CRM crossmatch module."""
    from features.crm import crossmatch
    assert hasattr(crossmatch, 'normalizar_telefone')


def test_import_integrations_evo():
    """Test importing EVO CRM integration."""
    from integrations import evo_crm
    assert evo_crm is not None


def test_import_app_config():
    """Test importing app config (Streamlit)."""
    from app import config
    assert hasattr(config, 'THEME')


def test_all_modules_have_init():
    """Test that all package directories have __init__.py."""
    packages = [
        project_root / 'src',
        project_root / 'src' / 'shared',
        project_root / 'src' / 'features',
        project_root / 'src' / 'features' / 'etl',
        project_root / 'src' / 'features' / 'analyzers',
        project_root / 'src' / 'features' / 'crm',
        project_root / 'src' / 'integrations',
        project_root / 'src' / 'app',
        project_root / 'tests',
    ]

    for package in packages:
        init_file = package / '__init__.py'
        assert init_file.exists(), f"Missing __init__.py in {package}"
