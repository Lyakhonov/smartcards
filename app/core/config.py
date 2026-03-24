import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_123")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
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

    # MinIO / S3 compatible settings
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "smartcards-files")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "0") in ("1", "true", "True")
    # Public endpoint used in presigned URLs (browser access), e.g. http://localhost:9000
    MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    # MinIO Console (browser) endpoint (used as fallback when presigned URL can't be generated)
    MINIO_CONSOLE_ENDPOINT = os.getenv(
        "MINIO_CONSOLE_ENDPOINT", "http://localhost:9001"
    )


settings = Settings()
