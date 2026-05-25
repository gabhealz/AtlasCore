import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator

from app.main import app
from app.db.session import engine

# Allow async fixtures
pytest_plugins = ('pytest_asyncio',)



@pytest.fixture(scope="function")
async def db_engine():
    # Use the main engine for now (in a real project, maybe override with a test DB)
    yield engine
    # await engine.dispose() # Don't dispose the main engine

import pytest_asyncio

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
