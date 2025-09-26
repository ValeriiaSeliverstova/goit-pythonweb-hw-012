"""Репозиторій для роботи з контактами користувача."""

from typing import List, Optional

from sqlalchemy import select, and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta, date
from src.database.models import User
from src.database.models import Contact
from src.schemas import ContactModel, ContactUpdate


class ContactRepository:
    """Репозиторій для CRUD-операцій і пошуку контактів."""

    def __init__(self, session: AsyncSession):
        """Ініціалізація з асинхронною сесією БД."""
        self.db = session

    async def get_contacts(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> List[Contact]:
        """Отримати всі контакти користувача з пагінацією."""
        stmt = (
            select(Contact).where(Contact.user_id == user.id).offset(skip).limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Отримати контакт користувача за його ID."""
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """Створити новий контакт для користувача."""
        data = body.model_dump(
            exclude_unset=True, exclude={"id", "created_at", "updated_at", "user_id"}
        )
        contact = Contact(**data, user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Видалити контакт користувача за його ID."""
        contact = await self.get_contact_by_id(contact_id, user)
        if not contact:
            return None
        await self.db.delete(contact)
        await self.db.commit()
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactUpdate, user: User
    ) -> Contact | None:
        """Оновити дані контакту користувача."""
        contact = await self.get_contact_by_id(contact_id, user)
        if not contact:
            return None

        data = body.model_dump(
            exclude_unset=True, exclude={"id", "created_at", "updated_at"}
        )
        for key, value in data.items():
            setattr(contact, key, value)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise

        await self.db.refresh(contact)
        return contact

    async def search_contacts(
        self,
        first_name: Optional[str],
        last_name: Optional[str],
        email: Optional[str],
        skip: int,
        limit: int,
        user: User,
    ) -> List[Contact]:
        """Шукати контакти користувача за ім’ям, прізвищем або email."""
        stmt = select(Contact).filter_by(user_id=user.id)
        conditions = []
        if first_name:
            conditions.append(Contact.first_name.ilike(f"%{first_name.strip()}%"))
        if last_name:
            conditions.append(Contact.last_name.ilike(f"%{last_name.strip()}%"))
        if email:
            conditions.append(Contact.email.ilike(f"%{email.strip()}%"))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def upcoming_birthdays(self, days: int, user: User) -> List[Contact]:
        """Отримати контакти з днями народження у найближчі `days` днів.

        Коректно працює навіть якщо діапазон переходить через Новий рік.
        """
        today = date.today()
        end = today + timedelta(days=days)

        start_key = today.strftime("%m%d")
        end_key = end.strftime("%m%d")
        key = func.to_char(Contact.birthday, "MMDD")

        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(Contact.birthday.is_not(None))
        )
        if start_key <= end_key:
            stmt = stmt.where(key.between(start_key, end_key))
        else:
            stmt = stmt.where(or_(key >= start_key, key <= end_key))

        stmt = stmt.order_by(key)
        result = await self.db.execute(stmt)
        return result.scalars().all()
