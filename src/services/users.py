"""Сервіс для роботи з користувачами: автентифікація, аватар, ролі та відновлення паролю."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.repository.users import UserRepository
from src.schemas import UserModel, UserResponse, TokenModel
from src.cache.redis_client import get_redis
from src.cache.token_cache import is_refresh_token_active, save_refresh_token
from jose import JWTError
from src.conf.config import settings
from src.cloudinary_service import upload_user_avatar, delete_asset
from src.auth.roles import UserRole
from src.emailer import mailer
from src.auth.auth import (
    Hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    create_reset_token,
    decode_reset_token,
)


class UserService:
    """Сервісний шар для роботи з користувачами."""

    def __init__(self, db: AsyncSession):
        """Ініціалізація з асинхронною сесією БД."""
        self.user_repository = UserRepository(db)
        self.hash = Hash()

    async def create_user(self, body: UserModel) -> UserResponse:
        """Створити нового користувача.

        Args:
            body: Модель користувача з email, username, password.

        Returns:
            UserResponse: Створений користувач.

        Raises:
            ValueError: Якщо користувач із таким email уже існує.
        """
        email = body.email.strip().lower()
        username = body.username.strip()

        if await self.user_repository.get_user_by_email(email):
            raise ValueError("User already exists")

        pwd_hash = self.hash.get_password_hash(body.password)

        user = await self.user_repository.create_user(
            username=username, email=email, password_hash=pwd_hash
        )
        return UserResponse.model_validate(user)

    async def update_avatar_from_file(self, user_id: int, file_obj) -> UserResponse:
        """Оновити аватар користувача у Cloudinary.

        Args:
            user_id: ID користувача.
            file_obj: Файл-зображення.

        Returns:
            UserResponse: Користувач із оновленим аватаром.

        Raises:
            ValueError: Якщо користувача не знайдено.
        """
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        old_public_id = user.public_id
        new_url, new_pid = upload_user_avatar(file_obj, user_id)
        updated = await self.user_repository.set_avatar(user_id, new_url, new_pid)

        if old_public_id and old_public_id != new_pid:
            try:
                delete_asset(old_public_id)
            except Exception:
                pass

        return UserResponse.model_validate(updated)

    async def login_by_email(self, email: str, password: str) -> TokenModel:
        """Увійти за email/паролем та отримати токени.

        Args:
            email: Email користувача.
            password: Пароль користувача.

        Returns:
            TokenModel: Access і refresh токени.

        Raises:
            ValueError: Якщо дані некоректні або email не підтверджено.
        """
        email = email.strip().lower()
        user = await self.user_repository.get_user_by_email(email)
        if not user or not self.hash.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        if not user.confirmed:
            raise ValueError("Email not confirmed")

        access = await create_access_token(
            {"sub": user.email}, settings.JWT_EXPIRATION_SECONDS
        )
        refresh = await create_refresh_token(
            {"sub": user.email}, settings.JWT_REFRESH_EXPIRATION_SECONDS
        )

        await self.user_repository.set_refresh_token(user.email, refresh)

        r = await get_redis()
        await save_refresh_token(r, refresh, user.email)

        return TokenModel(access_token=access, refresh_token=refresh)

    async def refresh_access_token(self, refresh_token: str) -> TokenModel:
        """Оновити access-токен за дійсним refresh-токеном.

        Args:
            refresh_token: Refresh-токен користувача.

        Returns:
            TokenModel: Новий access-токен + той самий refresh-токен.

        Raises:
            ValueError: Якщо токен недійсний або прострочений.
        """
        r = await get_redis()
        active_in_redis = await is_refresh_token_active(r, refresh_token)

        user = None
        if active_in_redis:
            try:
                payload = decode_refresh_token(refresh_token)
            except JWTError:
                raise ValueError("Invalid or expired refresh token")

            user = await self.user_repository.get_user_by_email(payload["sub"])
            if not user:
                raise ValueError("Invalid or expired refresh token")
        else:
            user = await self.user_repository.get_user_by_refresh_token(refresh_token)
            if not user:
                raise ValueError("Invalid or expired refresh token")

            try:
                payload = decode_refresh_token(refresh_token)
            except JWTError:
                raise ValueError("Invalid or expired refresh token")

            if (
                payload.get("token_type") != "refresh"
                or payload.get("sub") != user.email
            ):
                raise ValueError("Invalid or expired refresh token")

            await save_refresh_token(r, refresh_token, user.email)

        access = await create_access_token(
            {"sub": user.email}, settings.JWT_EXPIRATION_SECONDS
        )
        return TokenModel(access_token=access, refresh_token=refresh_token)

    async def logout(self, user_email: str) -> None:
        """Вийти з системи, скинувши refresh-токен у БД."""
        await self.user_repository.set_refresh_token(user_email, None)

    async def get_user_by_email(self, email: str) -> UserResponse | None:
        """Отримати користувача за email (UserResponse)."""
        user = await self.user_repository.get_user_by_email(email)
        if user:
            return UserResponse.model_validate(user)
        return None

    async def confirmed_email(self, email: str) -> None:
        """Позначити email користувача як підтверджений."""
        await self.user_repository.confirmed_email(email)
        return

    async def change_user_role(
        self,
        actor: UserModel,
        target_user_id: int,
        new_role: UserRole,
    ) -> UserModel:
        """Змінити роль користувача (адміністраторський ендпойнт).

        Args:
            actor: Користувач, що виконує дію (має бути адміністратором).
            target_user_id: ID користувача, якому змінюється роль.
            new_role: Нова роль.

        Returns:
            UserModel: Користувач із оновленою роллю.

        Raises:
            HTTPException: Якщо користувача не знайдено.
        """
        user = await self.user_repository.get_user_by_id(target_user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == new_role:
            return user

        updated_user = await self.user_repository.set_role(user.id, new_role.value)
        return updated_user

    async def request_password_reset(self, email: str) -> None:
        """Надіслати лист із токеном для скидання паролю.

        Args:
            email: Email користувача.
        """
        user = await self.user_repository.get_user_by_email(email.strip().lower())
        if user:
            token = await create_reset_token(
                {"sub": user.email}, settings.RESET_TOKEN_EXPIRATION_SECONDS
            )
            r = await get_redis()
            await r.setex(f"pr:{token}", 15 * 60, user.email)
            await mailer.send_password_reset_email(user.email, token)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Скинути пароль користувача за токеном.

        Перевіряє токен у Redis і JWT, оновлює пароль у БД,
        інвалідуючи refresh-токен, і видаляє токен скидання.

        Args:
            token: Токен для скидання паролю.
            new_password: Новий пароль користувача.

        Raises:
            HTTPException: Якщо токен недійсний, прострочений або користувача не знайдено.
        """
        r = await get_redis()
        email = await r.get(f"pr:{token}")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        if isinstance(email, bytes):
            email = email.decode()

        try:
            payload = decode_reset_token(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        if payload.get("token_type") != "password_reset" or payload.get("sub") != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = await self.user_repository.get_user_by_email(email)
        if not user:
            await r.delete(f"pr:{token}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        new_hash = self.hash.get_password_hash(new_password)
        await self.user_repository.set_password_hash(user.email, new_hash)
        await self.user_repository.set_refresh_token(email, None)
        await r.delete(f"pr:{token}")
