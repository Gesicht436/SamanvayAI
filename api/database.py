import asyncio
import sys
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import get_settings

# psycopg3 async requires SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""


def get_sync_engine():
    """Create synchronous engine (used for migrations and seeding)."""
    settings = get_settings()
    # Ensure psycopg driver is specified
    url = settings.database_url
    if "+psycopg" not in url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")
    return create_engine(url, echo=False)


def get_async_engine():
    """Create async engine for FastAPI request lifecycle."""
    settings = get_settings()
    url = settings.database_url
    # Ensure async driver for psycopg 3
    if "+psycopg" not in url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")
    return create_async_engine(url, echo=False)


# Sync session factory
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_sync_engine())

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db(org_id: str = "") -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session configured with tenant RLS context."""
    async with AsyncSessionLocal() as session:
        if org_id:
            # Set the tenant session variable for Row-Level Security
            await session.execute(text("SET LOCAL app.current_org = :org_id"), {"org_id": org_id})
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
