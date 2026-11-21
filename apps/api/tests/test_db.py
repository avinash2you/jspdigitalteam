from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine, get_db


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_db_session_and_vector_extension() -> None:
    async with AsyncSessionLocal() as session:
        # Verify basic DB execution
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Verify pgvector extension presence
        ext_result = await session.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
        )
        row = ext_result.fetchone()
        assert row is not None, "Extension 'vector' must be installed in database"
        assert row[0] == "vector"

        # Verify vector data type operations
        vector_result = await session.execute(text("SELECT '[1,2,3]'::vector"))
        vector_val = vector_result.scalar()
        assert str(vector_val) == "[1,2,3]"


@pytest.mark.asyncio
async def test_get_db_generator() -> None:
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        res = await session.execute(text("SELECT 1"))
        assert res.scalar() == 1
        break


@pytest.mark.asyncio
async def test_engine_connect() -> None:
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT 1"))
        assert res.scalar() == 1
