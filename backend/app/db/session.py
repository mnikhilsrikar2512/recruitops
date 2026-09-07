from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings


def build_odbc_connection_string() -> str:
    encrypt_value = "yes" if settings.db_encrypt else "no"
    trust_value = "yes" if settings.db_trust_server_certificate else "no"
    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        f"Encrypt={encrypt_value};"
        f"TrustServerCertificate={trust_value};"
    )


def build_sqlalchemy_url() -> str:
    odbc_connection = quote_plus(build_odbc_connection_string())
    return f"mssql+pyodbc:///?odbc_connect={odbc_connection}"


def create_db_engine() -> Engine:
    return create_engine(build_sqlalchemy_url(), future=True, pool_pre_ping=True)

