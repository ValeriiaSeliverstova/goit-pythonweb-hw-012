"""Модуль з переліком ролей користувачів у системі."""

from enum import StrEnum


class UserRole(StrEnum):
    """Ролі користувачів.

    Attributes:
        ADMIN: Роль адміністратора з повними правами.
        USER: Звичайний користувач із базовими правами.
    """

    ADMIN = "admin"
    USER = "user"
