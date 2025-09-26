"""Pydantic-схеми для користувачів, контактів та службових моделей."""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from src.auth.roles import UserRole


class UserModel(BaseModel):
    """Вхідна модель для створення користувача (реєстрація)."""

    username: str
    password: str
    email: EmailStr


class UserResponse(BaseModel):
    """Вихідна модель користувача для відповіді API."""

    id: int
    username: str
    email: EmailStr
    role: UserRole = UserRole.USER
    avatar: str | None = None
    public_id: str | None = None
    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Модель для оновлення ролі користувача."""

    role: UserRole


class LoginModel(BaseModel):
    """Модель для входу користувача."""

    username: str
    password: str


class TokenModel(BaseModel):
    """Модель токенів доступу та оновлення."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Модель запиту для оновлення access-токена."""

    refresh_token: str


class ContactModel(BaseModel):
    """Базова модель контакту."""

    model_config = ConfigDict(from_attributes=True)
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    email: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=50)
    birthday: Optional[datetime]
    extra_info: Optional[str]


class ContactCreate(ContactModel):
    """Модель для створення нового контакту (без id, дат)."""

    pass


class ContactUpdate(ContactModel):
    """Модель для оновлення існуючого контакту."""

    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    birthday: Optional[date] = None
    extra_info: Optional[str] = None
    done: bool


class ContactResponse(ContactModel):
    """Вихідна модель контакту для відповіді API."""

    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EmailModel(BaseModel):
    """Модель з єдиним полем email (службова)."""

    email: EmailStr


class RequestEmail(BaseModel):
    """Модель запиту для відправки листа підтвердження email."""

    email: EmailStr


class ResetPasswordModel(BaseModel):
    """Модель для скидання пароля."""

    token: str
    new_password: str
