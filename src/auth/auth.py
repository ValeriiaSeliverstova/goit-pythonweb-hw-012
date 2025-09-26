"""Модуль для роботи з автентифікацією та токенами JWT."""

from datetime import datetime, timedelta, UTC
from typing import Optional, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository.users import UserRepository
from src.conf.config import settings

RESET_TOKEN_TYPE = "password_reset"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class Hash:
    """Утиліти для хешування та перевірки паролів."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Перевіряє пароль на відповідність хешу."""
        return Hash.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Повертає хешований пароль."""
        return Hash.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


def create_token(
    data: dict,
    expires_delta: timedelta,
    token_type: Literal[ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE],
) -> str:
    """Створює JWT токен із заданими даними та часом життя.

    Args:
        data: Дані для кодування.
        expires_delta: Тривалість дії токена.
        token_type: Тип токена ("access" або "refresh").

    Returns:
        Закодований JWT токен.
    """
    now = datetime.now(UTC)
    payload = {**data, "iat": now, "exp": now + expires_delta, "token_type": token_type}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Створює access-токен.

    Args:
        data: Дані користувача.
        expires_delta: Час життя у секундах (якщо None – береться з конфігу).

    Returns:
        JWT access-токен.
    """
    exp_td = (
        timedelta(seconds=expires_delta)
        if expires_delta is not None
        else timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    )
    return create_token(data, exp_td, "access")


async def create_refresh_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Створює refresh-токен.

    Args:
        data: Дані користувача.
        expires_delta: Час життя у секундах (якщо None – береться з конфігу).

    Returns:
        JWT refresh-токен.
    """
    exp_td = (
        timedelta(seconds=expires_delta)
        if expires_delta is not None
        else timedelta(seconds=settings.JWT_REFRESH_EXPIRATION_SECONDS)
    )
    return create_token(data, exp_td, "refresh")


def decode_refresh_token(refresh_token: str) -> dict:
    """Декодує refresh-токен у словник."""
    return jwt.decode(
        refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )


def create_email_token(data: dict) -> str:
    """Створює токен для підтвердження email (діє 7 днів)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


async def get_email_from_token(token: str) -> str:
    """Отримує email з токена підтвердження.

    Args:
        token: JWT токен.

    Returns:
        Email користувача.

    Raises:
        HTTPException: Якщо токен некоректний.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Отримує поточного користувача з access-токена.

    Args:
        token: JWT access-токен (береться з Authorization).
        db: Сесія БД.

    Returns:
        Об’єкт користувача.

    Raises:
        HTTPException: Якщо токен недійсний або користувач не знайдений.
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("token_type") != "access":  # ensure access token
            raise cred_exc
        subject_email = payload.get("sub")
        if not subject_email:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = await UserRepository(db).get_user_by_email(subject_email)
    if user is None:
        raise cred_exc
    return user


async def create_reset_token(payload: dict, expires_seconds: int) -> str:
    """Створює токен для скидання паролю.

    Args:
        payload: Дані користувача.
        expires_seconds: Час життя токена у секундах.

    Returns:
        JWT токен для скидання паролю.
    """
    to_encode = payload.copy()
    now = datetime.now(UTC)
    to_encode.update(
        {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
            "token_type": RESET_TOKEN_TYPE,
        }
    )
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_reset_token(token: str) -> dict:
    """Декодує токен скидання паролю та перевіряє його тип.

    Args:
        token: JWT токен.

    Returns:
        Дані з токена.

    Raises:
        JWTError: Якщо токен має неправильний тип.
    """
    data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if data.get("token_type") != RESET_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    return data
