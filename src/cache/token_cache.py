"""Робота з refresh-токенами у Redis (збереження та перевірка активності)."""

from redis import asyncio as aioredis
from src.conf.config import settings


def _rt_key(token: str) -> str:
    """Формує ключ у Redis для refresh-токена.

    Args:
        token: Значення refresh-токена.

    Returns:
        str: Ключ для Redis.
    """
    return f"rt:{token}"


async def save_refresh_token(r: aioredis.Redis, token: str, email: str) -> None:
    """Зберігає refresh-токен у Redis з прив’язкою до email.

    Args:
        r: Клієнт Redis.
        token: Значення refresh-токена.
        email: Email користувача.
    """
    await r.set(_rt_key(token), email, ex=settings.JWT_REFRESH_EXPIRATION_SECONDS)


async def is_refresh_token_active(r: aioredis.Redis, token: str) -> bool:
    """Перевіряє, чи активний refresh-токен у Redis.

    Args:
        r: Клієнт Redis.
        token: Значення refresh-токена.

    Returns:
        bool: True, якщо токен існує, False — інакше.
    """
    return await r.exists(_rt_key(token)) == 1
