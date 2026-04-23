import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'journal.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 短 access token，降低降級/停用後仍有效的視窗
    _access_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "30"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=_access_minutes)
    # 長 refresh token，維持體驗
    _refresh_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=_refresh_days)

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Rate limit
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200/minute")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    JSON_SORT_KEYS = False
