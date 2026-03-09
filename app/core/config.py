import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_123")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 1
    # Refresh token lifetime (days)
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    # Cookie name for refresh token
    REFRESH_TOKEN_COOKIE_NAME = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "refresh_token")

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/smartcards",
    )

    # admin bootstrap
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@admin.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "Super Admin")


settings = Settings()
