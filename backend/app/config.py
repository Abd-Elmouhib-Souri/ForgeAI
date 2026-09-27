from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ðŸŽ¯ CONFIGURATION GÃ‰NÃ‰RALE DE L'APPLICATION
    APP_NAME: str = "ForgeAI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ðŸ”’ SÃ‰CURITÃ‰, SESSIONS & CHIFFREMENT
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AES_SECRET_KEY: str

    # ðŸ” GOOGLE OAUTH 2.0
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    SESSION_SECRET_KEY: str

    # ðŸ“§ VÃ‰RIFICATION EMAIL
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # ðŸ“¤ SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "ForgeAI"
    SMTP_USE_TLS: bool = True

    # ðŸ—„ï¸ POSTGRESQL
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

     # ðŸ¤– LLM PROVIDERS
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_FALLBACK_MODEL: str = ""

    GROQ_API_KEY: str = ""
    GROQ_API_BASE: str = ""
    # Defaults only apply when .env leaves them empty. llama-3.3-70b-versatile,
    # llama-3.1-8b-instant and groq/compound(-mini) are decommissioned by Groq
    # (HTTP 404 model_not_found): verify with GET /openai/v1/models.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODEL: str = "qwen/qwen3.8-27b"

    LLM_PRIMARY_PROVIDER: str = "gemini"
    LLM_FALLBACK_PROVIDER: str = "groq"
    LLM_REQUEST_TIMEOUT_SECONDS: int = 90
    # Groq free tier answers 429 "Please try again in 7.6s" when the
    # per-minute token budget is spent: wait that long (bounded) instead of
    # failing the whole generation. 0 disables in-call waiting.
    LLM_RATE_LIMIT_MAX_WAIT_SECONDS: float = 20.0
    # Private folder holding generated exports (PDF/DOCX/PPTX). Never
    # served statically: files are streamed by the owner-filtered
    # /projects/{id}/exports/{export_id}/download endpoint only.
    EXPORTS_DIR: str = "/app/exports"
    # Smallest useful answer budget: below it a structured JSON answer would
    # be truncated, so the model is skipped instead of producing junk.
    LLM_MIN_OUTPUT_TOKENS: int = 1200
    # gpt-oss models spend hidden reasoning tokens that count against the
    # per-minute budget; "low" keeps them small. Empty string disables.
    GROQ_REASONING_EFFORT: str = "low"
    LLM_CIRCUIT_FAILURES: int = 3
    LLM_CIRCUIT_COOLDOWN_SECONDS: int = 180

    ENABLE_PARALLEL_AGENTS: bool = False

    OPENAI_API_KEY: Optional[str] = ""

    # ðŸ“Š MONITORING
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"

    # ðŸŒ CORS
    
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

    # Optional source classifier:
    # dedicated Gemini key -> Groq -> deterministic rules.
    ENABLE_AI_SOURCE_CLASSIFIER: bool = True
    GEMINI_SEARCH_CLASSIFIER_API_KEY: str = ""
    GEMINI_SEARCH_CLASSIFIER_MODEL: str = "gemini-3-flash-preview"
    SEARCH_CLASSIFIER_PRIMARY: str = "gemini"
    SEARCH_CLASSIFIER_FALLBACK: str = "groq"
    SEARCH_CLASSIFIER_TIMEOUT_SECONDS: int = 35
    SEARCH_CLASSIFIER_MAX_SOURCES: int = 16


settings = Settings()


