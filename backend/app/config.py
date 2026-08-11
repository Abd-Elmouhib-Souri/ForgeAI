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


    # Runtime analysis and web-search configuration.
    GEMINI_SEARCH_MODEL: str = "gemini-3-flash-preview"
    ANALYSIS_MAX_CONCURRENT_RUNS: int = 2
    ENABLE_TAVILY_SEARCH: bool = True
    TAVILY_API_KEY: str = ""
    TAVILY_SEARCH_URL: str = "https://api.tavily.com/search"
    TAVILY_SEARCH_DEPTH: str = "basic"
    TAVILY_MAX_RESULTS: int = 8
    TAVILY_MIN_SCORE: float = 0.35
    TAVILY_CHUNKS_PER_SOURCE: int = 2
    TAVILY_INCLUDE_RAW_CONTENT: bool = False
    TAVILY_SAFE_SEARCH: bool = False
    TAVILY_MAX_CONCURRENT_REQUESTS: int = 3

    ENABLE_GEMINI_GROUNDED_SEARCH: bool = False
    ENABLE_DDGS_FALLBACK: bool = True
    SEARCH_PRIMARY_PROVIDER: str = "tavily"
    SEARCH_FALLBACK_PROVIDER: str = "ddgs"
    SEARCH_MAX_RESULTS_PER_QUERY: int = 8
    SEARCH_MIN_RESULTS: int = 4
    SEARCH_PROVIDER_TIMEOUT_SECONDS: int = 35
    SEARCH_CACHE_TTL_SECONDS: int = 21600
    SEARCH_CIRCUIT_FAILURES: int = 2
    SEARCH_CIRCUIT_COOLDOWN_SECONDS: int = 900
    SEARCH_MAX_QUERIES_PER_ANALYSIS: int = 10

settings = Settings()