from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 🎯 CONFIGURATION GÉNÉRALE DE L'APPLICATION
    APP_NAME: str = "DotJcom ForgeAI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # 🔒 SÉCURITÉ, SESSIONS & CHIFFREMENT
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AES_SECRET_KEY: str

    # 🔐 GOOGLE OAUTH 2.0
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    SESSION_SECRET_KEY: str

    # 📧 VÉRIFICATION EMAIL
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # 📤 SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "DotJcom ForgeAI"
    SMTP_USE_TLS: bool = True

    # 🗄️ POSTGRESQL
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "forgeai"
    POSTGRES_USER: str = "forgeai_user"
    POSTGRES_PASSWORD: str
    DATABASE_URL: str

    # Base Vectorielle + Cache
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    CHROMA_AUTH_TOKEN: str
    REDIS_URL: str = "redis://redis:6379/0"

     # 🤖 LLM PROVIDERS
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_FALLBACK_MODEL: str = "gemini-3-flash-lite-preview"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "llama-3.1-8b-instant"

    ENABLE_PARALLEL_AGENTS: bool = False

    OPENAI_API_KEY: Optional[str] = ""

    # 📊 MONITORING
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"

    # 🌐 CORS
    
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    PASSWORD_RESET_EXPIRE_HOURS: int = 1


settings = Settings()