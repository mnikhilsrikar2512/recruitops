from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Recruitment System API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    session_ttl_hours: int = Field(default=12, alias="SESSION_TTL_HOURS")
    token_expiry_hours: int = Field(default=24, alias="TOKEN_EXPIRY_HOURS")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=1433, alias="DB_PORT")
    db_name: str = Field(default="recruitment_system", alias="DB_NAME")
    db_user: str = Field(default="sa", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_driver: str = Field(default="ODBC Driver 18 for SQL Server", alias="DB_DRIVER")
    db_encrypt: bool = Field(default=False, alias="DB_ENCRYPT")
    db_trust_server_certificate: bool = Field(default=True, alias="DB_TRUST_SERVER_CERTIFICATE")
    upload_dir: str = Field(default="uploads", alias="UPLOAD_DIR")
    max_upload_size_bytes: int = Field(default=10_485_760, alias="MAX_UPLOAD_SIZE_BYTES")
    allowed_upload_extensions: str = Field(
        default=".pdf,.doc,.docx,.jpg,.jpeg,.png",
        alias="ALLOWED_UPLOAD_EXTENSIONS",
    )
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    email_from_name: str = Field(default="Recruitment System", alias="EMAIL_FROM_NAME")
    email_from_address: str = Field(default="", alias="EMAIL_FROM_ADDRESS")
    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    ai_max_items_per_run: int = Field(default=20, alias="AI_MAX_ITEMS_PER_RUN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
