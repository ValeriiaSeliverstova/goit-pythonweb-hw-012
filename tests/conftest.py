import os

os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///./test_int.db")
os.environ.setdefault("JWT_SECRET", "testsecret")
os.environ.setdefault("JWT_EXPIRATION_SECONDS", "3600")
os.environ.setdefault("JWT_REFRESH_EXPIRATION_SECONDS", "86400")

import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from src.database.models import Base
from fakeredis.aioredis import FakeRedis


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(os.environ["DB_URL"], future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncSession:
    conn = await engine.connect()
    outer = await conn.begin()

    Session = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
    session: AsyncSession = Session()

    nested = await session.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await outer.rollback()
        await conn.close()


@pytest.fixture(autouse=True)
async def fake_redis(monkeypatch):
    from fakeredis.aioredis import FakeRedis

    r = FakeRedis(encoding="utf-8", decode_responses=True)

    async def _get_redis():
        return r

    monkeypatch.setattr("src.cache.redis_client._redis", None, raising=False)
    monkeypatch.setattr("src.cache.redis_client.get_redis", _get_redis, raising=False)
    monkeypatch.setattr("src.cache.contacts_cache.get_redis", _get_redis, raising=False)
    monkeypatch.setattr("src.cache.token_cache.get_redis", _get_redis, raising=False)
    monkeypatch.setattr("src.services.contacts.get_redis", _get_redis, raising=False)
    monkeypatch.setattr("src.services.users.get_redis", _get_redis, raising=False)

    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()
