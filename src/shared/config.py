"""
Configuração centralizada do projeto
Gerencia variáveis de ambiente e validações
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


class ConfigError(Exception):
    """Exceção para erros de configuração"""
    pass


class Config:
    """Classe de configuração centralizada"""

    # ============================================
    # BANCO DE DADOS REMOTO (SOURCE)
    # ============================================
    SOURCE_DB_HOST: str = os.getenv('SOURCE_DB_HOST', '')
    SOURCE_DB_PORT: str = os.getenv('SOURCE_DB_PORT', '5432')
    SOURCE_DB_NAME: str = os.getenv('SOURCE_DB_NAME', '')
    SOURCE_DB_USER: str = os.getenv('SOURCE_DB_USER', '')
    SOURCE_DB_PASSWORD: str = os.getenv('SOURCE_DB_PASSWORD', '')
    SOURCE_DB_VIEW: str = os.getenv('SOURCE_DB_VIEW', 'vw_conversas_por_lead')

    # ============================================
    # BANCO DE DADOS LOCAL
    # ============================================
    LOCAL_DB_HOST: str = os.getenv('LOCAL_DB_HOST', '/var/run/postgresql')
    LOCAL_DB_PORT: str = os.getenv('LOCAL_DB_PORT', '5432')
    LOCAL_DB_NAME: str = os.getenv('LOCAL_DB_NAME', '')
    LOCAL_DB_USER: str = os.getenv('LOCAL_DB_USER', '')
    LOCAL_DB_PASSWORD: Optional[str] = os.getenv('LOCAL_DB_PASSWORD', None)
    LOCAL_DB_TABLE: str = os.getenv('LOCAL_DB_TABLE', 'conversas_lead')

    # ============================================
    # CONFIGURAÇÕES GERAIS
    # ============================================
    DATA_DIR: str = os.getenv('DATA_DIR', 'data')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate_source_db(cls) -> None:
        """Valida configurações do banco de dados remoto"""
        required = {
            'SOURCE_DB_HOST': cls.SOURCE_DB_HOST,
            'SOURCE_DB_NAME': cls.SOURCE_DB_NAME,
            'SOURCE_DB_USER': cls.SOURCE_DB_USER,
            'SOURCE_DB_PASSWORD': cls.SOURCE_DB_PASSWORD,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ConfigError(
                f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing)}\n"
                f"Configure no arquivo .env"
            )

    @classmethod
    def validate_local_db(cls) -> None:
        """Valida configurações do banco de dados local"""
        required = {
            'LOCAL_DB_NAME': cls.LOCAL_DB_NAME,
            'LOCAL_DB_USER': cls.LOCAL_DB_USER,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ConfigError(
                f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing)}\n"
                f"Configure no arquivo .env"
            )

    @classmethod
    def get_source_connection_string(cls) -> str:
        """Retorna string de conexão para banco remoto"""
        cls.validate_source_db()
        return (
            f"postgresql://{cls.SOURCE_DB_USER}:{cls.SOURCE_DB_PASSWORD}"
            f"@{cls.SOURCE_DB_HOST}:{cls.SOURCE_DB_PORT}/{cls.SOURCE_DB_NAME}"
        )

    @classmethod
    def get_local_connection_string(cls) -> str:
        """Retorna string de conexão para banco local"""
        cls.validate_local_db()

        # Se tiver password, usa TCP/IP
        if cls.LOCAL_DB_PASSWORD:
            return (
                f"postgresql://{cls.LOCAL_DB_USER}:{cls.LOCAL_DB_PASSWORD}"
                f"@{cls.LOCAL_DB_HOST}:{cls.LOCAL_DB_PORT}/{cls.LOCAL_DB_NAME}"
            )
        else:
            # Sem password, usa Unix socket
            return (
                f"postgresql://{cls.LOCAL_DB_USER}@/{cls.LOCAL_DB_NAME}"
                f"?host={cls.LOCAL_DB_HOST}&port={cls.LOCAL_DB_PORT}"
            )

    @classmethod
    def display_config(cls) -> None:
        """Exibe configurações (sem senhas)"""
        print("=" * 60)
        print("CONFIGURAÇÃO DO PROJETO")
        print("=" * 60)
        print("\n[BANCO REMOTO (SOURCE)]")
        print(f"  Host: {cls.SOURCE_DB_HOST}")
        print(f"  Port: {cls.SOURCE_DB_PORT}")
        print(f"  Database: {cls.SOURCE_DB_NAME}")
        print(f"  User: {cls.SOURCE_DB_USER}")
        print(f"  Password: {'*' * len(cls.SOURCE_DB_PASSWORD) if cls.SOURCE_DB_PASSWORD else '(não configurado)'}")
        print(f"  View: {cls.SOURCE_DB_VIEW}")

        print("\n[BANCO LOCAL]")
        print(f"  Host: {cls.LOCAL_DB_HOST}")
        print(f"  Port: {cls.LOCAL_DB_PORT}")
        print(f"  Database: {cls.LOCAL_DB_NAME}")
        print(f"  User: {cls.LOCAL_DB_USER}")
        print(f"  Password: {'*' * len(cls.LOCAL_DB_PASSWORD) if cls.LOCAL_DB_PASSWORD else '(não configurado)'}")
        print(f"  Table: {cls.LOCAL_DB_TABLE}")

        print("\n[GERAL]")
        print(f"  Data Directory: {cls.DATA_DIR}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print("=" * 60)


# Exemplo de uso
if __name__ == "__main__":
    try:
        Config.validate_source_db()
        Config.display_config()
        print("\n✓ Configuração validada com sucesso!")
    except ConfigError as e:
        print(f"\n✗ Erro de configuração: {e}")
