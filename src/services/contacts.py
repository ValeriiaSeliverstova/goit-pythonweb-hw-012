"""Сервіс для роботи з контактами: CRUD, пошук та кешування."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel, ContactUpdate
from src.cache import contacts_cache
from src.database.models import User


class ContactService:
    """Сервісний шар для роботи з контактами."""

    def __init__(self, db: AsyncSession):
        """Ініціалізація з асинхронною сесією БД."""
        self.contact_repository = ContactRepository(db)

    async def create_contact(self, body: ContactModel, user: User):
        """Створити новий контакт для користувача."""
        return await self.contact_repository.create_contact(body, user)

    async def get_contacts(self, user: User, skip: int, limit: int):
        """Отримати список контактів користувача з пагінацією."""
        return await self.contact_repository.get_contacts(user, skip, limit)

    async def get_contact(self, contact_id: int, user: User):
        """Отримати контакт користувача за ID."""
        return await self.contact_repository.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: ContactUpdate, user: User):
        """Оновити дані існуючого контакту користувача."""
        return await self.contact_repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        """Видалити контакт користувача за ID."""
        await self.contact_repository.remove_contact(contact_id, user)
        return True

    async def search_contacts(
        self,
        first_name: Optional[str],
        last_name: Optional[str],
        email: Optional[str],
        skip: int,
        limit: int,
        user: User,
    ) -> List[ContactModel]:
        """Шукати контакти з кешуванням результатів.

        Args:
            first_name: Ім’я для пошуку.
            last_name: Прізвище для пошуку.
            email: Email для пошуку.
            skip: Кількість записів для пропуску.
            limit: Кількість записів для повернення.
            user: Поточний користувач.

        Returns:
            Список знайдених контактів.
        """
        key = contacts_cache.make_search_key(
            user.id, first_name, last_name, email, skip, limit
        )
        cached = await contacts_cache.get_search_contacts(key)
        if cached is not None:
            return cached

        result = await self.contact_repository.search_contacts(
            first_name, last_name, email, skip, limit, user
        )
        await contacts_cache.set_search_contacts(key, result)
        return result

    async def upcoming_birthdays(
        self, days_ahead: int, user: User
    ) -> List[ContactModel]:
        """Отримати контакти з днями народження у найближчі дні (з кешем).

        Args:
            days_ahead: Кількість днів наперед.
            user: Поточний користувач.

        Returns:
            Список контактів із днями народження.
        """
        key = contacts_cache.make_birthdays_key(user.id, days_ahead)
        cached = await contacts_cache.get_birthdays(key)
        if cached is not None:
            return cached

        result = await self.contact_repository.upcoming_birthdays(days_ahead, user)
        await contacts_cache.set_birthdays(key, result)
        return result
