from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the root directory (where .env lives)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    # DataBase Settings
    DATABASE_URL: str
    ECHO: bool = False

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth (optional - leave empty to disable Google login)
    GOOGLE_ID: str = ""
    GOOGLE_SECRET: str = ""

    # Redis (for rate limiting)
    REDIS_URL: str = "redis://localhost:6379"

    # Email settings (for verification emails)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 2525

    # App URL (for email links)
    APP_URL: str = "http://localhost:8000"
# Create instance - this loads values from .env
settings = Settings() # type: ignore[call-arg]
