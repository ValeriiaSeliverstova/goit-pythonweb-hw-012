"""Модуль для підключення до Redis та отримання клієнта."""

from redis import asyncio as aioredis
from src.conf.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Повертає єдиний екземпляр Redis-клієнта.

    Якщо клієнт ще не створений, створює нове підключення з параметрами
    з конфігурації.

    Returns:
        aioredis.Redis: Асинхронний клієнт Redis.
    """
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis
