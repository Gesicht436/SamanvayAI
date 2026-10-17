import asyncio
import os
import sys

os.environ["JWT_SECRET"] = "test-secret-for-api-unit-tests-minimum-32-characters"
os.environ["DEMO_MODE"] = "true"

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_async_engine

# psycopg3 async requires WindowsSelectorEventLoopPolicy on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
async def async_session():
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def db_session(async_session):
    yield async_session
