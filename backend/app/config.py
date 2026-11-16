"""Application configuration via pydantic-settings.

Every variable declared in ``.env.example`` is mirrored here as a typed field.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cruisealert:cruisealert@localhost:5432/cruisealert"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # RapidAPI
    RAPIDAPI_KEY: str = "your_key_here"
    RAPIDAPI_HOST: str = "cruise-prices.p.rapidapi.com"

    # Auth
    JWT_SECRET: str = "change_me_to_64_random_chars"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str = "sk_test_..."
    STRIPE_WEBHOOK_SECRET: str = "whsec_..."
    STRIPE_PRO_MONTHLY_PRICE_ID: str = "price_..."
    STRIPE_PRO_ANNUAL_PRICE_ID: str = "price_..."

    # SendGrid
    SENDGRID_API_KEY: str = "SG...."
    SENDGRID_FROM_EMAIL: str = "alerts@cruisealert.io"
    SENDGRID_PRICE_DROP_TEMPLATE_ID: str = "d-..."
    SENDGRID_BACK_IN_STOCK_TEMPLATE_ID: str = "d-..."
    SENDGRID_AVAIL_WARNING_TEMPLATE_ID: str = "d-..."
    SENDGRID_VERIFY_EMAIL_TEMPLATE_ID: str = "d-..."

    # Twilio
    TWILIO_ACCOUNT_SID: str = "AC..."
    TWILIO_AUTH_TOKEN: str = "..."
    TWILIO_FROM_NUMBER: str = "+1..."
    TWILIO_VERIFY_SERVICE_SID: str = "VA..."

    # App
    FRONTEND_URL: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"

    # RapidAPI monthly call budget (leave headroom below the hard 100 cap)
    RAPIDAPI_MONTHLY_CAP: int = 95

    # Scheduled-task (Vercel Cron) auth + demo price feed toggle
    CRON_SECRET: str = ""
    DEMO_PRICE_FEED: bool = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
