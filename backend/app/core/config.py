from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Local development origins (frontend/server.js on 4174, legacy static server
# on 3000). Production must set CORS_ORIGINS explicitly — see validate_settings().
DEV_CORS_ORIGINS = (
    "http://localhost:4174,http://127.0.0.1:4174,"
    "http://localhost:3000,http://127.0.0.1:3000"
)
PRODUCTION_ENVS = {"production", "prod", "staging"}


class Settings(BaseSettings):
    app_name: str = Field(default="Recruitment System API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    # Comma-separated exact origins. Never "*" outside development (PRD §10).
    cors_origins: str = Field(default=DEV_CORS_ORIGINS, alias="CORS_ORIGINS")
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
    # AI is OFF at launch (decision D-10): in staging/production the agents
    # API answers 404 unless AI_ENABLED=true, and validate_settings() refuses
    # true there until the §4.16 gates ship. Development keeps agents on.
    ai_enabled: bool = Field(default=False, alias="AI_ENABLED")

    # ── Scaffolding for production-readiness Phases 3–4 (not yet consumed) ──
    # Object storage (Phase 4.1): "local" keeps core/storage.py's disk path.
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_region: str = Field(default="", alias="S3_REGION")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    signed_url_ttl_seconds: int = Field(default=300, alias="SIGNED_URL_TTL_SECONDS")
    # Rate limiting / session denylist / permission cache (Phase 3.7).
    redis_url: str = Field(default="", alias="REDIS_URL")
    # JWT access + rotating refresh tokens (Phase 3.1–3.2).
    jwt_signing_key: str = Field(default="", alias="JWT_SIGNING_KEY")
    jwt_access_ttl_minutes: int = Field(default=15, alias="JWT_ACCESS_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=14, alias="REFRESH_TOKEN_TTL_DAYS")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in PRODUCTION_ENVS

    @property
    def ai_agents_available(self) -> bool:
        return self.ai_enabled or not self.is_production

    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def validate_settings(config: "Settings") -> list[str]:
    """Return configuration errors that must stop a production/staging boot.

    Development keeps permissive defaults; staging/production fail fast on
    settings that would ship an insecure perimeter (PRD §10, §13 item 7).
    """
    if not config.is_production:
        return []
    errors: list[str] = []
    origins = config.cors_origin_list()
    if not origins or "*" in origins:
        errors.append("CORS_ORIGINS must list exact origins (no '*') in staging/production")
    if any(origin.startswith("http://") for origin in origins):
        errors.append("CORS_ORIGINS must be https:// origins in staging/production")
    if not config.db_password:
        errors.append("DB_PASSWORD must be set in staging/production")
    if config.ai_enabled:
        errors.append("AI_ENABLED must stay false until the §4.16 AI gates ship (decision D-10)")
    return errors


settings = Settings()
