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

    _hours = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "12"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_hours)

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    JSON_SORT_KEYS = False
