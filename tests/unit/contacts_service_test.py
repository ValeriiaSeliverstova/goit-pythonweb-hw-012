# tests/contacts_service_test.py

import os

os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "testsecret")

import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from datetime import date

from src.services.contacts import ContactService
from src.schemas import ContactModel, ContactUpdate


@pytest.fixture
def user():
    return SimpleNamespace(id=1, email="owner@example.com")


# test create contact
@pytest.mark.asyncio
async def test_create_contact(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    body = ContactModel(
        first_name="Alice",
        last_name="A",
        email="a@example.com",
        phone="+10001",
        birthday=date(1990, 1, 1),
        extra_info="vip",
        done=False,
    )

    repo.create_contact.return_value = {
        "id": 10,
        "first_name": "Alice",
        "last_name": "A",
        "email": "a@example.com",
        "phone": "+10001",
        "birthday": str(date(1990, 1, 1)),
        "extra_info": "vip",
        "done": False,
    }

    created = await service.create_contact(body, user)

    assert created["id"] == 10
    repo.create_contact.assert_awaited_once_with(body, user)


# test get contacts
@pytest.mark.asyncio
async def test_get_contacts(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.get_contacts.return_value = [{"id": 1}, {"id": 2}]
    result = await service.get_contacts(user, skip=0, limit=2)

    assert len(result) == 2
    repo.get_contacts.assert_awaited_once_with(user, 0, 2)


# test get contact by id
@pytest.mark.asyncio
async def test_get_contact_found(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.get_contact_by_id.return_value = {"id": 5}
    result = await service.get_contact(5, user)

    assert result["id"] == 5
    repo.get_contact_by_id.assert_awaited_once_with(5, user)


# test get contact by id not found
@pytest.mark.asyncio
async def test_get_contact_not_found(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.get_contact_by_id.return_value = None
    result = await service.get_contact(999, user)

    assert result is None
    repo.get_contact_by_id.assert_awaited_once_with(999, user)


# test update contact
@pytest.mark.asyncio
async def test_update_contact(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    body = ContactUpdate(
        first_name="Bob", phone="+20002", done=True, extra_info="updated"
    )
    repo.update_contact.return_value = {"id": 7, "first_name": "Bob", "phone": "+20002"}

    result = await service.update_contact(7, body, user)

    assert result["first_name"] == "Bob"
    repo.update_contact.assert_awaited_once_with(7, body, user)


# test remove contact
@pytest.mark.asyncio
async def test_remove_contact(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.remove_contact.return_value = None
    ok = await service.remove_contact(3, user)

    assert ok is True
    repo.remove_contact.assert_awaited_once_with(3, user)


# test search contacts
@pytest.mark.asyncio
async def test_search_contacts(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.search_contacts.return_value = [{"id": 1}, {"id": 2}]
    result = await service.search_contacts(
        "Al", None, None, skip=0, limit=10, user=user
    )

    assert len(result) == 2
    repo.search_contacts.assert_awaited_once_with("Al", None, None, 0, 10, user)


# test upcoming birthdays
@pytest.mark.asyncio
async def test_upcoming_birthdays(user):
    service = ContactService(db=object())
    repo = AsyncMock()
    service.contact_repository = repo

    repo.upcoming_birthdays.return_value = [{"id": 1}]
    result = await service.upcoming_birthdays(7, user)

    assert result == [{"id": 1}]
    repo.upcoming_birthdays.assert_awaited_once_with(7, user)
