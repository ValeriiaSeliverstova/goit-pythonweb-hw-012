import pytest

pytestmark = pytest.mark.integration

from src.services.users import UserService
from src.schemas import UserModel


@pytest.mark.asyncio
async def test_user_create_and_login_flow(db_session):
    service = UserService(db_session)

    u = UserModel(username="alice", password="s3cret!", email="alice@example.com")
    created = await service.create_user(u)
    assert created.username == "alice"
    assert created.email == "alice@example.com"

    # confirm email before login
    await service.confirmed_email("alice@example.com")

    tokens = await service.login_by_email("alice@example.com", "s3cret!")
    assert tokens.access_token and isinstance(tokens.access_token, str)
    assert tokens.refresh_token and isinstance(tokens.refresh_token, str)

    # refresh access token
    refreshed = await service.refresh_access_token(tokens.refresh_token)
    assert refreshed.access_token and isinstance(refreshed.access_token, str)
    assert refreshed.refresh_token == tokens.refresh_token


@pytest.mark.asyncio
async def test_user_duplicate_email_rejected(db_session):
    service = UserService(db_session)
    u1 = UserModel(username="bob", password="p@ss", email="bob@example.com")
    await service.create_user(u1)

    u2 = UserModel(username="other", password="p@ss", email="bob@example.com")
    with pytest.raises(ValueError, match="User already exists"):
        await service.create_user(u2)


@pytest.mark.asyncio
async def test_login_invalid_password_and_unconfirmed(db_session):
    service = UserService(db_session)
    u = UserModel(
        username="charlie", password="right-pass", email="charlie@example.com"
    )
    await service.create_user(u)

    # wrong password
    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.login_by_email("charlie@example.com", "wrong-pass")

    # unconfirmed email blocks login
    with pytest.raises(ValueError, match="Email not confirmed"):
        await service.login_by_email("charlie@example.com", "right-pass")

    # confirm and login succeeds
    await service.confirmed_email("charlie@example.com")
    tokens = await service.login_by_email("charlie@example.com", "right-pass")
    assert tokens.access_token and tokens.refresh_token
