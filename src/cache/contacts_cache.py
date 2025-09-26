"""Кешування пошуку контактів і днів народження у Redis."""

from typing import List, Optional, Iterable, Dict
from hashlib import sha1
from fastapi.encoders import jsonable_encoder
import json

from src.schemas import ContactModel
from src.cache.redis_client import get_redis

SEARCH_TTL = 60
BIRTHDAYS_TTL = 600


def _norm(s: Optional[str]) -> str:
    """Нормалізує рядок: обрізає пробіли та переводить у нижній регістр."""
    return (s or "").strip().lower()


def make_search_key(
    user_id: int,
    first_name: Optional[str],
    last_name: Optional[str],
    email: Optional[str],
    skip: int,
    limit: int,
) -> str:
    """Генерує унікальний ключ для кешу пошуку контактів.

    Args:
        user_id: ID користувача.
        first_name: Ім'я для пошуку.
        last_name: Прізвище для пошуку.
        email: Email для пошуку.
        skip: Кількість елементів для пропуску.
        limit: Кількість елементів для повернення.

    Returns:
        Строковий ключ для Redis.
    """
    payload = json.dumps(
        {
            "fn": _norm(first_name),
            "ln": _norm(last_name),
            "em": _norm(email),
            "s": skip,
            "l": limit,
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = sha1(payload.encode("utf-8")).hexdigest()
    return f"contacts:search:{user_id}:{digest}"


def make_birthdays_key(user_id: int, days_ahead: int) -> str:
    """Генерує ключ для кешу майбутніх днів народження.

    Args:
        user_id: ID користувача.
        days_ahead: Кількість днів наперед.

    Returns:
        Строковий ключ для Redis.
    """
    return f"contacts:birthdays:{user_id}:{days_ahead}"


async def get_search_contacts(key: str) -> Optional[List[Dict]]:
    """Отримати результати пошуку контактів з кешу.

    Args:
        key: Ключ у Redis.

    Returns:
        Список контактів у вигляді словників або None.
    """
    r = await get_redis()
    data = await r.get(key)
    if not data:
        return None
    return json.loads(data)


async def set_search_contacts(
    key: str,
    contacts: Iterable,
    ttl: int = SEARCH_TTL,
) -> None:
    """Зберегти результати пошуку контактів у кеш.

    Args:
        key: Ключ у Redis.
        contacts: Список контактів (ORM або Pydantic моделі).
        ttl: Час життя кешу у секундах.
    """
    r = await get_redis()
    payload = jsonable_encoder(contacts)
    await r.set(key, json.dumps(payload), ex=ttl)


async def get_birthdays(key: str) -> Optional[List[Dict]]:
    """Отримати список майбутніх днів народження з кешу.

    Args:
        key: Ключ у Redis.

    Returns:
        Список контактів або None.
    """
    r = await get_redis()
    data = await r.get(key)
    if not data:
        return None
    return json.loads(data)


async def set_birthdays(key: str, contacts: List[ContactModel]) -> None:
    """Зберегти список контактів з днями народження у кеш.

    Args:
        key: Ключ у Redis.
        contacts: Список контактів.
    """
    r = await get_redis()
    payload = jsonable_encoder(contacts)
    await r.set(key, json.dumps(payload), ex=BIRTHDAYS_TTL)
