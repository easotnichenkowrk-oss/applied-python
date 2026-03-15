import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
import main
from main import app

@pytest.fixture
def mock_dependencies(mocker):
    mock_redis = AsyncMock()
    main.redis_client = mock_redis
    
    mock_pool = AsyncMock()
    main.db_pool = mock_pool
    
    return mock_pool, mock_redis

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client