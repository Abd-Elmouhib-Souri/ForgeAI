from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ============================================================
# Database engine
# ============================================================
#
# Important:
# - echo=False prevents raw SQL logs from flooding the backend logs.
# - Keep SQL logs disabled even when DEBUG=True, because analysis_data can be large.
# ============================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)


# ============================================================
# Async session factory
# ============================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# SQLAlchemy 2.0 declarative base
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# FastAPI database dependency
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an isolated async database session per request.
    The session is always closed after request processing.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()