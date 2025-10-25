"""
Testes para módulo de configuração
"""
import pytest
import os
from unittest.mock import patch


def test_config_module_exists():
    """Test that config module can be imported."""
    from shared import config
    assert config is not None


def test_config_class_exists():
    """Test that Config class exists."""
    from shared.config import Config
    assert Config is not None


@patch.dict(os.environ, {
    'LOCAL_DB_NAME': 'test_db',
    'LOCAL_DB_USER': 'test_user',
    'SOURCE_DB_HOST': 'localhost',
    'SOURCE_DB_NAME': 'test_source',
    'SOURCE_DB_USER': 'test_source_user',
    'SOURCE_DB_PASSWORD': 'test_pass'
})
def test_config_loads_env_variables():
    """Test that Config loads environment variables."""
    from shared.config import Config

    assert Config.LOCAL_DB_NAME == 'test_db'
    assert Config.LOCAL_DB_USER == 'test_user'
    assert Config.SOURCE_DB_HOST == 'localhost'


@patch.dict(os.environ, {
    'LOCAL_DB_NAME': 'test_db',
    'LOCAL_DB_USER': 'test_user',
    'LOCAL_DB_PASSWORD': 'test_password'
})
def test_get_local_connection_string_with_password():
    """Test local connection string generation with password."""
    from shared.config import Config

    conn_str = Config.get_local_connection_string()
    assert 'test_db' in conn_str
    assert 'test_user' in conn_str
    assert 'test_password' in conn_str


def test_config_missing_values_raises_error():
    """Test that missing required config raises ConfigError."""
    from shared.config import Config, ConfigError

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigError):
            Config.validate_source_db()
