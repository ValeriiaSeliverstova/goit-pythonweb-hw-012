import pytest
from datetime import date, timedelta

from src.repository.contacts import ContactRepository
from src.schemas import ContactModel, ContactUpdate


async def _make_user(db, *, email: str, username: str | None = None):
    from src.database.models import User

    if username is None:
        username = email.split("@")[0]

    user = User(
        email=email,
        username=username,
        password_hash="test-hash",
        confirmed=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_and_get_contact(db_session):
    repo = ContactRepository(db_session)
    user = await _make_user(db_session, email="owner_create_get@example.com")

    body = ContactModel(
        first_name="Alice",
        last_name="A",
        email="alice@example.com",
        phone="+10001",
        birthday=date(1990, 1, 1),
        extra_info="",
        done=False,
    )

    created = await repo.create_contact(body, user)
    assert created.id is not None
    assert created.user_id == user.id
    assert created.email == "alice@example.com"

    fetched = await repo.get_contact_by_id(created.id, user)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_contacts_with_pagination(db_session):
    repo = ContactRepository(db_session)
    user = await _make_user(db_session, email="owner_pagination@example.com")

    for i in range(3):
        await repo.create_contact(
            ContactModel(
                first_name=f"N{i}",
                last_name="Last",
                email=f"n{i}@example.com",
                phone=f"+1{i}",
                birthday=date(1990, 1, 1),
                extra_info="",
                done=False,
            ),
            user,
        )

    first_two = await repo.get_contacts(user, skip=0, limit=2)
    last_one = await repo.get_contacts(user, skip=2, limit=10)

    assert len(first_two) == 2
    assert len(last_one) == 1


@pytest.mark.asyncio
async def test_update_contact_found_and_not_found(db_session):
    repo = ContactRepository(db_session)
    user = await _make_user(db_session, email="owner_update@example.com")

    created = await repo.create_contact(
        ContactModel(
            first_name="Bob",
            last_name="B",
            email="bob@example.com",
            phone="+20002",
            birthday=date(1991, 2, 2),
            extra_info="",
            done=False,
        ),
        user,
    )

    # Build kwargs only for fields present in ContactUpdate
    upd_kwargs = {}
    if "first_name" in ContactUpdate.model_fields:
        upd_kwargs["first_name"] = "Bobby"
    if "phone" in ContactUpdate.model_fields:
        upd_kwargs["phone"] = "+33333"
    if "extra_info" in ContactUpdate.model_fields:
        upd_kwargs["extra_info"] = "upd"
    if "done" in ContactUpdate.model_fields:
        upd_kwargs["done"] = True

    updated = await repo.update_contact(created.id, ContactUpdate(**upd_kwargs), user)
    assert updated is not None
    if "first_name" in ContactUpdate.model_fields:
        assert updated.first_name == "Bobby"
    if "phone" in ContactUpdate.model_fields:
        assert updated.phone == "+33333"

    # Update non-existing -> None
    payload = {k: v for k, v in upd_kwargs.items()}
    if not payload:
        # ensure at least one field so ContactUpdate(...) is valid
        payload = (
            {"first_name": "X"} if "first_name" in ContactUpdate.model_fields else {}
        )
    upd_none = await repo.update_contact(999999, ContactUpdate(**payload), user)
    assert upd_none is None


@pytest.mark.asyncio
async def test_remove_contact_found_and_not_found(db_session):
    repo = ContactRepository(db_session)
    user = await _make_user(db_session, email="owner_remove@example.com")

    created = await repo.create_contact(
        ContactModel(
            first_name="Del",
            last_name="Me",
            email="del@example.com",
            phone="+40004",
            birthday=date(1992, 3, 3),
            extra_info="",
            done=False,
        ),
        user,
    )

    removed = await repo.remove_contact(created.id, user)
    assert removed is not None

    gone = await repo.get_contact_by_id(created.id, user)
    assert gone is None

    removed_none = await repo.remove_contact(created.id, user)
    assert removed_none is None


@pytest.mark.asyncio
async def test_search_contacts_filters(db_session):
    repo = ContactRepository(db_session)
    user = await _make_user(db_session, email="owner_search@example.com")

    await repo.create_contact(
        ContactModel(
            first_name="Ann",
            last_name="Lee",
            email="ann@example.com",
            phone="+1",
            birthday=date(1990, 1, 1),
            extra_info="",
            done=False,
        ),
        user,
    )
    await repo.create_contact(
        ContactModel(
            first_name="Anna",
            last_name="Lemon",
            email="anna@example.com",
            phone="+2",
            birthday=date(1990, 1, 1),
            extra_info="",
            done=False,
        ),
        user,
    )
    await repo.create_contact(
        ContactModel(
            first_name="Bob",
            last_name="Mar",
            email="bob@example.com",
            phone="+3",
            birthday=date(1990, 1, 1),
            extra_info="",
            done=False,
        ),
        user,
    )

    res1 = await repo.search_contacts("Ann", None, None, 0, 10, user)
    assert len(res1) == 2

    res2 = await repo.search_contacts(None, "Lee", None, 0, 10, user)
    assert len(res2) == 1
    assert res2[0].email == "ann@example.com"

    res3 = await repo.search_contacts(None, None, "bob@", 0, 10, user)
    assert len(res3) == 1
    assert res3[0].first_name == "Bob"

    res4 = await repo.search_contacts("Ann", "Lem", "anna@", 0, 10, user)
    assert len(res4) == 1
    assert res4[0].email == "anna@example.com"
