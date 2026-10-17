import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import contextmanager

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import get_settings
from api.security.jwt_auth import AuthUser, get_current_user

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
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=get_sync_engine())


@contextmanager
def tenant_sync_session(org_id: str):
    """Open a synchronous session with transaction-local tenant context for RLS."""
    with SyncSessionLocal() as session:
        session.execute(text("SELECT set_config('app.current_org', :org_id, false)"), {"org_id": org_id})
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            try:
                session.rollback()
                session.execute(text("SELECT set_config('app.current_org', '', false)"))
                session.commit()
            except SQLAlchemyError:
                session.rollback()

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db(user: AuthUser = Depends(get_current_user)) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session configured with tenant RLS context."""
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_org', :org_id, false)"),
                {"org_id": user.org_id},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            try:
                await session.rollback()
                await session.execute(text("SELECT set_config('app.current_org', '', false)"))
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
