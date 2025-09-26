import os

os.environ.setdefault("JWT_SECRET", "testsecret")
os.environ.setdefault("JWT_EXPIRATION_SECONDS", "3600")
os.environ.setdefault("JWT_REFRESH_EXPIRATION_SECONDS", "86400")

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import HTTPException
from jose import JWTError, jwt

from src.auth import auth
from src.conf.config import settings


def test_hash_roundtrip():
    pwd = "S3cret!"
    hashed = auth.Hash.get_password_hash(pwd)
    assert hashed and isinstance(hashed, str)
    assert auth.Hash.verify_password(pwd, hashed) is True
    assert auth.Hash.verify_password("wrong", hashed) is False


@pytest.mark.asyncio
async def test_create_access_and_refresh_tokens_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    access = await auth.create_access_token({"sub": "u@example.com"})
    refresh = await auth.create_refresh_token({"sub": "u@example.com"})

    a = jwt.decode(access, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    r = jwt.decode(refresh, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

    assert a["sub"] == "u@example.com"
    assert a["token_type"] == "access"
    assert r["sub"] == "u@example.com"
    assert r["token_type"] == "refresh"


def test_decode_refresh_token_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "right")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    tok = jwt.encode(
        {"sub": "u@example.com", "token_type": "refresh"}, "right", algorithm="HS256"
    )
    with pytest.raises(JWTError):
        auth.decode_refresh_token(tok + "tamper")  # invalid


@pytest.mark.asyncio
async def test_get_email_from_token_success(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    tok = auth.create_email_token({"sub": "u@example.com"})
    email = await auth.get_email_from_token(tok)
    assert email == "u@example.com"


@pytest.mark.asyncio
async def test_get_email_from_token_missing_sub(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    tok = jwt.encode(
        {"iat": 0, "exp": 9999999999},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as e:
        await auth.get_email_from_token(tok)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_get_email_from_token_invalid(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    tok = auth.create_email_token({"sub": "u@example.com"}) + "x"
    with pytest.raises(HTTPException) as e:
        await auth.get_email_from_token(tok)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    user = SimpleNamespace(id=1, email="u@example.com")

    class FakeRepo:
        def __init__(self, _db):
            pass

        async def get_user_by_email(self, email):
            return user

    monkeypatch.setattr(auth, "UserRepository", FakeRepo)

    token = await auth.create_access_token({"sub": "u@example.com"})
    db = AsyncMock()  # not used by FakeRepo, but passed through
    got = await auth.get_current_user(token=token, db=db)
    assert got.email == "u@example.com"


@pytest.mark.asyncio
async def test_get_current_user_wrong_type(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    token = await auth.create_refresh_token({"sub": "u@example.com"})
    db = AsyncMock()

    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(token=token, db=db)
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_jwt(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    token = await auth.create_access_token({"sub": "u@example.com"})
    token += "bad"  # break signature
    db = AsyncMock()

    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(token=token, db=db)
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")
    # token with no "sub"
    token = jwt.encode(
        {"token_type": "access"}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(token=token, db=AsyncMock())
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "testsecret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")

    class RepoNF:
        def __init__(self, _db): ...
        async def get_user_by_email(self, email):
            return None

    monkeypatch.setattr(auth, "UserRepository", RepoNF)

    token = await auth.create_access_token({"sub": "ghost@example.com"})
    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(token=token, db=AsyncMock())
    assert e.value.status_code == 401
