import string
import random
import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

app = FastAPI()
db_pool = None
redis_client = None

class User(BaseModel):
    username : str
    password : str

class LinkCreate(BaseModel):
    original_url : str
    custom_alias : Optional[str] = None
    expires_at : Optional[datetime] = None

class LinkUpdate(BaseModel):
    new_url : str

class CleanupRequest(BaseModel):
    days : int



@app.on_event('startup')
async def startup():
    global db_pool, redis_client
    db_pool = await asyncpg.create_pool(dsn = 'postgresql://app_user:app_pass@db:5432/shortener')
    redis_client = await aioredis.from_url('redis://redis:6379', decode_responses = True)



@app.on_event('shutdown')
async def shutdown():
    await db_pool.close()
    await redis_client.close()



def generate_code(length = 6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))



async def get_user_id(x_token : str):
    if not x_token:
        return None

    query = 'SELECT id FROM users WHERE username = $1'
    record = await db_pool.fetchrow(query, x_token)

    if not record:
        raise HTTPException(status_code = 401, detail = 'Неавторизован')

    return record['id']



@app.post('/register')
async def register(user : User):
    query = 'INSERT INTO users (username, password) VALUES ($1, $2) RETURNING id'
    
    try:
        await db_pool.execute(query, user.username, user.password)
        return {'token' : user.username, 'message' : 'Успешная регистрация'}
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code = 400, detail = 'Пользователь существует')



@app.post('/links/shorten')
async def shorten_link(link_data : LinkCreate, x_token : Optional[str] = Header(None)):
    user_id = await get_user_id(x_token = x_token)
    short_code = link_data.custom_alias if link_data.custom_alias else generate_code(length = 6)
    check_query = 'SELECT short_code FROM links WHERE short_code = $1'
    
    if await db_pool.fetchval(check_query, short_code):
        raise HTTPException(status_code = 400, detail = 'Алиас занят')
    
    insert_query = 'INSERT INTO links (short_code, original_url, user_id, expires_at) VALUES ($1, $2, $3, $4)'
    await db_pool.execute(insert_query, short_code, link_data.original_url, user_id, link_data.expires_at)
    
    return {'short_url' : f'http://localhost:8000/links/{short_code}', 'short_code' : short_code}



async def update_stats(short_code : str):
    update_query = 'UPDATE links SET clicks_count = clicks_count + 1, last_used = NOW() WHERE short_code = $1'
    await db_pool.execute(update_query, short_code)



@app.get('/links/search')
async def search_links(original_url : str):
    query = 'SELECT short_code FROM links WHERE original_url = $1'
    records = await db_pool.fetch(query, original_url)

    return {'short_codes' : [rec['short_code'] for rec in records]}



@app.get('/links/{short_code}')
async def redirect_to_original(short_code : str, background_tasks : BackgroundTasks):
    cached_url = await redis_client.get(short_code)

    if cached_url:
        background_tasks.add_task(update_stats, short_code = short_code)
        return RedirectResponse(url = cached_url)

    query = 'SELECT original_url, expires_at FROM links WHERE short_code = $1'
    record = await db_pool.fetchrow(query, short_code)
    
    if not record:
        raise HTTPException(status_code = 404, detail = 'Ссылка не найдена')

    now = datetime.now()
    if record['expires_at'] and record['expires_at'] < now:
        move_query = 'INSERT INTO expired_links (short_code, original_url, reason) VALUES ($1, $2, $3)'
        await db_pool.execute(move_query, short_code, record['original_url'], 'Истекло время жизни')
        await db_pool.execute('DELETE FROM links WHERE short_code = $1', short_code)
        raise HTTPException(status_code = 410, detail = 'Ссылка истекла')

    cache_ttl = 3600
    if record['expires_at']:
        remaining_seconds = int((record['expires_at'] - now).total_seconds())
        cache_ttl = min(3600, remaining_seconds)

    if cache_ttl > 0:
        await redis_client.set(short_code, record['original_url'], ex=cache_ttl)

    background_tasks.add_task(update_stats, short_code = short_code)
    
    return RedirectResponse(url = record['original_url'])



@app.delete('/links/{short_code}')
async def delete_link(short_code : str, x_token : Optional[str] = Header(None)):
    user_id = await get_user_id(x_token = x_token)
    if not user_id:
        raise HTTPException(status_code = 401, detail = 'Требуется авторизация')
    
    query = 'SELECT user_id FROM links WHERE short_code = $1'
    owner_id = await db_pool.fetchval(query, short_code)

    if owner_id != user_id:
        raise HTTPException(status_code = 403, detail = 'Нет прав')

    delete_query = 'DELETE FROM links WHERE short_code = $1'
    await db_pool.execute(delete_query, short_code)
    await redis_client.delete(short_code)

    return {'message' : 'Ссылка удалена'}



@app.put('/links/{short_code}')
async def update_link(short_code : str, link_data : LinkUpdate, x_token : Optional[str] = Header(None)):
    user_id = await get_user_id(x_token = x_token)

    if not user_id:
        raise HTTPException(status_code = 401, detail = 'Требуется авторизация')
    
    query = 'SELECT user_id FROM links WHERE short_code = $1'
    owner_id = await db_pool.fetchval(query, short_code)

    if owner_id != user_id:
        raise HTTPException(status_code = 403, detail = 'Нет прав')

    update_query = 'UPDATE links SET original_url = $1 WHERE short_code = $2'
    await db_pool.execute(update_query, link_data.new_url, short_code)
    await redis_client.delete(short_code)

    return {'message' : 'Ссылка обновлена'}



@app.get('/links/{short_code}/stats')
async def get_stats(short_code : str):
    query = 'SELECT original_url, created_at, clicks_count, last_used FROM links WHERE short_code = $1'
    record = await db_pool.fetchrow(query, short_code)

    if not record:
        raise HTTPException(status_code = 404, detail = 'Ссылка не найдена')
    
    return dict(record)




@app.post('/admin/cleanup')
async def cleanup_links(req : CleanupRequest):
    threshold = datetime.now() - timedelta(days = req.days)
    find_query = 'SELECT short_code, original_url FROM links WHERE last_used < $1'
    records = await db_pool.fetch(find_query, threshold)

    for rec in records:
        move_query = 'INSERT INTO expired_links (short_code, original_url, reason) VALUES ($1, $2, $3)'
        await db_pool.execute(move_query, rec['short_code'], rec['original_url'], 'Не использовалась')
        del_query = 'DELETE FROM links WHERE short_code = $1'
        await db_pool.execute(del_query, rec['short_code'])
        await redis_client.delete(rec['short_code'])

    return {'deleted_count' : len(records)}

@app.get('/history/expired')
async def get_expired_history():
    query = 'SELECT * FROM expired_links'
    records = await db_pool.fetch(query)

    return [dict(rec) for rec in records]