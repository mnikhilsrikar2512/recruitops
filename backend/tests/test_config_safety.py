"""Production configuration guardrails (PRD §10, §13 items 7 and 11)."""

from app.core.config import DEV_CORS_ORIGINS, Settings, validate_settings


def _settings(**env) -> Settings:
    return Settings.model_validate(env)


def test_development_defaults_are_accepted_and_not_wildcard():
    config = _settings(APP_ENV="development")
    assert validate_settings(config) == []
    assert "*" not in config.cors_origin_list()
    assert config.cors_origin_list() == [o for o in DEV_CORS_ORIGINS.split(",")]


def test_production_rejects_wildcard_cors():
    config = _settings(APP_ENV="production", CORS_ORIGINS="*", DB_PASSWORD="x")
    assert any("CORS_ORIGINS" in error for error in validate_settings(config))


def test_production_rejects_plain_http_origins():
    config = _settings(APP_ENV="production", CORS_ORIGINS="http://app.example.com", DB_PASSWORD="x")
    assert any("https" in error for error in validate_settings(config))


def test_production_accepts_exact_https_origins():
    config = _settings(APP_ENV="production", CORS_ORIGINS="https://app.example.com", DB_PASSWORD="x",
                       JWT_SIGNING_KEY="k" * 48, REDIS_URL="redis://cache:6379/0",
                       RATE_LIMIT_ENABLED=True,  # explicit: the verify script exports it false
                       STORAGE_BACKEND="s3", S3_BUCKET="recruitops-files", MALWARE_SCANNER="clamav")
    assert validate_settings(config) == []


def test_production_requires_a_real_jwt_signing_key():
    config = _settings(APP_ENV="production", CORS_ORIGINS="https://app.example.com", DB_PASSWORD="x")
    assert any("JWT_SIGNING_KEY" in error for error in validate_settings(config))


def test_ai_flag_is_off_in_production_and_cannot_be_enabled():
    off = _settings(APP_ENV="staging", CORS_ORIGINS="https://staging.example.com", DB_PASSWORD="x")
    assert off.ai_agents_available is False
    on = _settings(APP_ENV="production", CORS_ORIGINS="https://app.example.com", DB_PASSWORD="x", AI_ENABLED="true")
    assert any("AI_ENABLED" in error for error in validate_settings(on))


def test_ai_agents_stay_available_in_development():
    assert _settings(APP_ENV="development").ai_agents_available is True


def test_production_refuses_disabled_rate_limits():
    config = _settings(APP_ENV="production", CORS_ORIGINS="https://app.example.com", DB_PASSWORD="x",
                       JWT_SIGNING_KEY="k" * 48, REDIS_URL="redis://cache:6379/0", RATE_LIMIT_ENABLED=False)
    assert any("RATE_LIMIT_ENABLED" in error for error in validate_settings(config))


def test_production_refuses_local_storage_and_builtin_scanner():
    config = _settings(APP_ENV="production", CORS_ORIGINS="https://app.example.com", DB_PASSWORD="x",
                       JWT_SIGNING_KEY="k" * 48, REDIS_URL="redis://cache:6379/0", RATE_LIMIT_ENABLED=True)
    errors = validate_settings(config)
    assert any("STORAGE_BACKEND" in e for e in errors)
    assert any("MALWARE_SCANNER" in e for e in errors)
    bucketless = _settings(APP_ENV="production", STORAGE_BACKEND="s3", MALWARE_SCANNER="clamav")
    assert any("S3_BUCKET" in e for e in validate_settings(bucketless))
