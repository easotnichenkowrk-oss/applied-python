import pytest
from datetime import datetime, timedelta
import asyncpg

pytestmark = pytest.mark.asyncio

async def test_register_success(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.execute.return_value = None
    
    response = await async_client.post("/register", json={"username": "testuser", "password": "123"})
    assert response.status_code == 200
    assert response.json() == {"token": "testuser", "message": "Успешная регистрация"}



async def test_shorten_link_success(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.fetchrow.return_value = {"id": 1}
    mock_pool.fetchval.return_value = None
    
    response = await async_client.post(
        "/links/shorten", 
        json={"original_url": "https://example.com", "custom_alias": "myalias"},
        headers={"x-token": "testuser"}
    )
    
    assert response.status_code == 200
    assert response.json()["short_code"] == "myalias"
    assert "short_url" in response.json()




async def test_redirect_cached(async_client, mock_dependencies):
    _, mock_redis = mock_dependencies
    mock_redis.get.return_value = "https://example.com"
    
    response = await async_client.get("/links/myalias", follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"
    mock_redis.get.assert_called_once_with("myalias")




async def test_redirect_db_fallback(async_client, mock_dependencies):
    mock_pool, mock_redis = mock_dependencies
    mock_redis.get.return_value = None
    
    future_date = datetime.now() + timedelta(days=1)
    mock_pool.fetchrow.return_value = {"original_url": "https://google.com", "expires_at": future_date}
    
    response = await async_client.get("/links/db_alias", follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["location"] == "https://google.com"
    assert mock_redis.set.called



async def test_delete_link(async_client, mock_dependencies):
    mock_pool, mock_redis = mock_dependencies
    mock_pool.fetchrow.return_value = {"id": 1}
    mock_pool.fetchval.return_value = 1
    
    response = await async_client.delete("/links/myalias", headers={"x-token": "testuser"})
    
    assert response.status_code == 200
    assert response.json() == {"message": "Ссылка удалена"}
    assert mock_pool.execute.called
    assert mock_redis.delete.called




async def test_search_links(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.fetch.return_value = [{"short_code": "abc"}, {"short_code": "xyz"}]
    
    response = await async_client.get("/links/search?original_url=https://test.com")
    assert response.status_code == 200
    assert response.json() == {"short_codes": ["abc", "xyz"]}



async def test_redirect_expired(async_client, mock_dependencies):
    mock_pool, mock_redis = mock_dependencies
    mock_redis.get.return_value = None
    past_date = datetime.now() - timedelta(days=1)
    mock_pool.fetchrow.return_value = {
        "original_url": "https://old.com", 
        "expires_at": past_date
    }

    response = await async_client.get("/links/old_alias")
    assert response.status_code == 410
    assert response.json()["detail"] == "Ссылка истекла"



async def test_update_link_forbidden(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    
    mock_pool.fetchrow.return_value = {"id": 1}
    
    mock_pool.fetchval.return_value = 2

    response = await async_client.put("/links/some_alias", json={"new_url": "https://new.com"}, headers={"x-token": "current_user"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Нет прав"



async def test_get_stats_not_found(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.fetchrow.return_value = None
    
    response = await async_client.get("/links/missing/stats")
    assert response.status_code == 404



async def test_admin_cleanup(async_client, mock_dependencies):
    mock_pool, mock_redis = mock_dependencies
    mock_pool.fetch.return_value = [
        {"short_code": "old1", "original_url": "https://old1.com"}
    ]
    
    response = await async_client.post("/admin/cleanup", json={"days": 30})
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
    assert mock_pool.execute.called



async def test_get_expired_history(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.fetch.return_value = [{"short_code": "old", "original_url": "http://ex.com", "reason": "expired"}]
    
    response = await async_client.get("/history/expired")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["short_code"] == "old"



async def test_register_duplicate(async_client, mock_dependencies):
    mock_pool, _ = mock_dependencies
    mock_pool.execute.side_effect = asyncpg.exceptions.UniqueViolationError()
    
    response = await async_client.post(
        "/register", 
        json={"username": "exists", "password": "123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Пользователь существует"