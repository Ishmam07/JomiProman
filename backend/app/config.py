"""Application settings, loaded from environment variables / .env files."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REGISTRAR_KEY = "demo-registrar"
DEFAULT_ADMIN_KEY = "demo-admin-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "JomiProman API"
    environment: str = "development"  # development | production
    log_level: str = "INFO"

    # Storage
    database_url: str = "sqlite:///./jomiproman.db"
    redis_url: str = ""  # empty -> in-memory fallback cache

    # Web
    cors_origins: str = "http://localhost:5173,http://localhost:3100"
    public_base_url: str = "http://localhost:3100"  # used inside QR codes

    # Security
    registrar_key: str = DEFAULT_REGISTRAR_KEY
    admin_key: str = DEFAULT_ADMIN_KEY
    signing_key_b64: str = ""  # base64 of a 32-byte Ed25519 seed (optional)
    signing_key_path: str = "./data/ed25519.key"
    rate_limit_per_minute: int = 30

    # Demo data
    auto_seed: bool = True

    # Cache
    plot_cache_ttl: int = 60

    # AI (Groq, OpenAI-compatible API). Empty key -> deterministic fallbacks.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ai_timeout_seconds: float = 20.0
    ai_cache_ttl: int = 3600

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
