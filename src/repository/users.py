"""Репозиторій для роботи з користувачами (CRUD та службові операції)."""

from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User


class UserRepository:
    """Репозиторій для доступу до таблиці користувачів."""

    def __init__(self, session: AsyncSession):
        """Ініціалізація з асинхронною сесією БД."""
        self.db = session

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Отримати користувача за email."""
        res = await self.db.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return res.scalar_one_or_none()

    async def create_user(
        self, *, username: str, email: str, password_hash: str
    ) -> User:
        """Створити нового користувача.

        Raises:
            ValueError: Якщо користувач з таким email уже існує.
        """
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("User already exists")
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Отримати користувача за його ID."""
        res = await self.db.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def set_avatar(
        self, user_id: int, avatar_url: str, public_id: str | None
    ) -> User:
        """Оновити аватар користувача.

        Args:
            user_id: ID користувача.
            avatar_url: URL зображення.
            public_id: Публічний ідентифікатор у хмарному сховищі.
        """
        res = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(avatar=avatar_url, public_id=public_id)
            .returning(User)
        )
        user = res.scalar_one()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user_by_refresh_token(self, refresh_token: str) -> Optional[User]:
        """Отримати користувача за refresh-токеном."""
        res = await self.db.execute(
            select(User).where(User.refresh_token == refresh_token)
        )
        return res.scalar_one_or_none()

    async def set_refresh_token(
        self, user_email: str, refresh_token: Optional[str]
    ) -> None:
        """Прив’язати/скинути refresh-токен користувача за email."""
        await self.db.execute(
            update(User)
            .where(User.email == user_email)
            .values(refresh_token=refresh_token)
        )
        await self.db.commit()

    async def confirmed_email(self, email: str) -> None:
        """Позначити email користувача як підтверджений."""
        user = await self.get_user_by_email(email)
        user.confirmed = True
        await self.db.commit()

    async def set_role(self, user_id: int, role: str) -> User | None:
        """Встановити роль користувачу за його ID."""
        await self.db.execute(update(User).where(User.id == user_id).values(role=role))
        await self.db.commit()
        return await self.get_user_by_id(user_id)

    async def set_password_hash(self, email: str, password_hash: str) -> User | None:
        """Оновити пароль користувача та скинути refresh-токен."""
        stmt = (
            update(User)
            .where(User.email == email)
            .values(password_hash=password_hash, refresh_token=None)
            .returning(User)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()
