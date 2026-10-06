from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./omniflow.db"
    secret_key: str = DEV_SECRET
    cors_origins: str = "http://localhost:5173"
    timezone: str = "Asia/Kolkata"
    default_country_code: str = "91"
    log_level: str = "INFO"
    sentry_dsn: str = ""

    access_token_minutes: int = 30
    refresh_token_days: int = 14
    login_max_attempts: int = 5
    login_window_minutes: int = 15
    allow_signup: bool = True

    whatsapp_verify_token: str = "omniflow-verify"
    whatsapp_app_secret: str = ""
    # Development fallbacks only. In production every workspace stores its own credentials.
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    worker_enabled: bool = True
    retry_interval_seconds: int = 30

    demo_mode: bool = False
    seed_demo_data: bool = True
    seed_admin_email: str = "admin@omniflow.local"
    seed_admin_password: str = "admin123"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @model_validator(mode="after")
    def require_real_secret_in_production(self):
        if self.environment == "production" and (self.secret_key == DEV_SECRET or len(self.secret_key) < 32):
            raise ValueError("SECRET_KEY must be a random string of at least 32 characters in production")
        return self

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allow_env_whatsapp(self) -> bool:
        return self.environment != "production"


settings = Settings()
