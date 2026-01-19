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


# Create instance - this loads values from .env
settings = Settings()
