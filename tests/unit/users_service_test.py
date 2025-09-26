# tests/test_users_service.py
import os

os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "testsecret")

import pytest
from unittest.mock import AsyncMock
from src.services.users import UserService
from src.schemas import UserModel, UserRole
from types import SimpleNamespace


class DummyHash:
    def get_password_hash(self, password: str) -> str:
        return "hashed-pass"


@pytest.mark.parametrize(
    "user",
    [
        UserModel(username="user1", password="pass1", email="user1@example.com"),
        UserModel(username="user2", password="pass2", email="user2@example.com"),
    ],
)
@pytest.mark.asyncio
async def test_create_user(user):
    service = UserService(db=object())

    repo = AsyncMock()
    service.user_repository = repo
    service.hash = DummyHash()

    # not found user
    repo.get_user_by_email.return_value = None

    # creating user
    repo.create_user.return_value = {
        "id": 1,
        "username": user.username.strip(),
        "email": user.email.strip().lower(),
        "public_id": None,
        "avatar": None,
        "confirmed": False,
    }

    new_user = await service.create_user(user)

    assert new_user.username == user.username
    assert new_user.email == user.email.lower()
    repo.get_user_by_email.assert_awaited_once_with(user.email.lower())
    repo.create_user.assert_awaited_once_with(
        username=user.username.strip(),
        email=user.email.strip().lower(),
        password_hash="hashed-pass",
    )


# test for already existing user
@pytest.mark.asyncio
async def test_create_user_already_exists():
    service = UserService(db=object())
    repo = AsyncMock()
    service.user_repository = repo
    service.hash = DummyHash()

    user = UserModel(username="user1", password="pass1", email="user1@example.com")
    repo.get_user_by_email.return_value = {"id": 1, "email": user.email.lower()}

    with pytest.raises(ValueError, match="User already exists"):
        await service.create_user(user)

    repo.get_user_by_email.assert_awaited_once_with(user.email.lower())
    repo.create_user.assert_not_called()


@pytest.mark.asyncio
async def test_login_by_email_success(monkeypatch):
    service = UserService(db=object())
    repo = AsyncMock()
    service.user_repository = repo

    user = UserModel(username="user1", password="pass1", email="user1@example.com")

    repo.get_user_by_email.return_value = SimpleNamespace(
        id=1,
        username=user.username,
        email=user.email.lower(),
        password_hash="hashed-pass",
        confirmed=True,
    )

    monkeypatch.setattr(
        "src.services.users.Hash.verify_password", lambda self, pw, hashed: True
    )

    access_mock = AsyncMock(return_value="access-token")
    refresh_mock = AsyncMock(return_value="refresh-token")
    monkeypatch.setattr("src.services.users.create_access_token", access_mock)
    monkeypatch.setattr("src.services.users.create_refresh_token", refresh_mock)

    repo.set_refresh_token = AsyncMock()

    tokens = await service.login_by_email(user.email, user.password)

    assert tokens.access_token == "access-token"
    assert tokens.refresh_token == "refresh-token"
    repo.get_user_by_email.assert_awaited_once_with(user.email.lower())
    repo.set_refresh_token.assert_awaited_once_with(user.email.lower(), "refresh-token")
    access_mock.assert_awaited_once()
    refresh_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_by_email_wrong_password(monkeypatch):
    service = UserService(db=object())
    repo = AsyncMock()
    service.user_repository = repo

    user = UserModel(username="user1", password="wrong", email="user1@example.com")

    repo.get_user_by_email.return_value = SimpleNamespace(
        id=1,
        username=user.username,
        email=user.email.lower(),
        password_hash="hashed-pass",
        confirmed=True,
    )

    monkeypatch.setattr(
        "src.services.users.Hash.verify_password", lambda self, pw, hashed: False
    )

    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.login_by_email(user.email, user.password)

    repo.get_user_by_email.assert_awaited_once_with(user.email.lower())


@pytest.mark.asyncio
async def test_login_by_email_unconfirmed_email(monkeypatch):
    service = UserService(db=object())
    repo = AsyncMock()
    service.user_repository = repo

    user = UserModel(username="user1", password="pass1", email="user1@example.com")

    repo.get_user_by_email.return_value = SimpleNamespace(
        id=1,
        username=user.username,
        email=user.email.lower(),
        password_hash="hashed-pass",
        confirmed=False,
    )

    monkeypatch.setattr(
        "src.services.users.Hash.verify_password", lambda self, pw, hashed: True
    )

    with pytest.raises(ValueError, match="Email not confirmed"):
        await service.login_by_email(user.email, user.password)

    repo.get_user_by_email.assert_awaited_once_with(user.email.lower())


@pytest.mark.asyncio
async def test_logout_and_confirmed_email_calls_repo():
    svc = UserService(db=object())
    repo = AsyncMock()
    svc.user_repository = repo
    await svc.logout("u@e.com")
    await svc.confirmed_email("u@e.com")
    repo.set_refresh_token.assert_awaited_once_with("u@e.com", None)
    repo.confirmed_email.assert_awaited_once_with("u@e.com")


@pytest.mark.asyncio
async def test_change_user_role_updates_when_different():
    service = UserService(db=object())
    repo = AsyncMock()
    service.user_repository = repo

    actor = UserModel(username="admin", email="admin@example.com", password="x")

    # existing user has USER role, we promote to ADMIN
    existing = SimpleNamespace(id=7, role=UserRole.USER)
    updated = SimpleNamespace(id=7, role=UserRole.ADMIN)

    repo.get_user_by_id.return_value = existing
    repo.set_role.return_value = updated

    result = await service.change_user_role(
        actor=actor, target_user_id=7, new_role=UserRole.ADMIN
    )

    assert result.role == UserRole.ADMIN
    repo.get_user_by_id.assert_awaited_once_with(7)
    repo.set_role.assert_awaited_once_with(7, UserRole.ADMIN.value)
