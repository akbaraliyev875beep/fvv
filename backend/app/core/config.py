"""
Tez Yordam EMS — Markaziy Konfiguratsiya

Barcha muhit o'zgaruvchilari Pydantic Settings orqali boshqariladi.
.env faylidan avtomatik o'qiladi.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ilova sozlamalari — .env faylidan yuklanadi."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Umumiy ---
    app_name: str = "Tez Yordam EMS"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    allowed_origins: str = "http://localhost:8000"

    # --- Ma'lumotlar bazasi ---
    database_url: str = "postgresql+asyncpg://tez_yordam_user:tez_yordam_pass@localhost:5432/tez_yordam_db"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- JWT ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # --- OneID OAuth2/OIDC ---
    oneid_client_id: str = ""
    oneid_client_secret: str = ""
    oneid_authorization_url: str = "https://sso.egov.uz/sso/oauth/Authorization.do"
    oneid_token_url: str = "https://sso.egov.uz/sso/oauth/Authorization.do"
    oneid_userinfo_url: str = "https://sso.egov.uz/sso/oauth/Authorization.do"
    oneid_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"

    # --- OpenAI Whisper ---
    openai_api_key: str = ""
    whisper_model: str = "whisper-1"

    # --- LLM Risk Scorer ---
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_api_key: str = ""

    # --- SMS (Eskiz.uz) ---
    eskiz_email: str = ""
    eskiz_password: str = ""
    eskiz_base_url: str = "https://notify.eskiz.uz/api"

    # --- Firebase Cloud Messaging ---
    fcm_server_key: str = ""

    # --- Shifrlash (AES-256) ---
    encryption_key: str = "change-me-32-byte-key-in-prod!!"

    @property
    def allowed_origins_list(self) -> list[str]:
        """CORS uchun ruxsat berilgan domenlar ro'yxati."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
