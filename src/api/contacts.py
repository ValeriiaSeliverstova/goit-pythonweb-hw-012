from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from typing import Annotated, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.auth import get_current_user

from src.database.db import get_db
from src.schemas import (
    UserResponse,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
)

from src.services.contacts import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/search", response_model=List[ContactResponse])
async def search_contacts(
    first_name: Annotated[Optional[str], Query(min_length=1)] = None,
    last_name: Annotated[Optional[str], Query(min_length=1)] = None,
    email: Annotated[Optional[str], Query(min_length=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Пошук контактів за ім’ям, прізвищем або email.

    Args:
        first_name: Ім’я контакту для пошуку.
        last_name: Прізвище контакту для пошуку.
        email: Email контакту для пошуку.
        skip: Кількість елементів, які потрібно пропустити.
        limit: Максимальна кількість результатів (1–500).
        db: Сесія бази даних.
        user: Поточний користувач (з аутентифікації).

    Returns:
        Список контактів, які відповідають критеріям.
    """
    if not any([first_name, last_name, email]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: first_name, last_name, email",
        )
    service = ContactService(db)
    return await service.search_contacts(
        first_name, last_name, email, skip, limit, user
    )


@router.get("/upcoming_birthdays", response_model=List[ContactResponse])
async def get_upcoming_birthdays(
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Отримати список контактів із днями народження,
    які наближаються впродовж зазначеної кількості днів.

    Args:
        days: Кількість днів наперед для пошуку.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Список контактів із днями народження у найближчі `days`.
    """
    service = ContactService(db)
    return await service.upcoming_birthdays(days, user)


@router.get("/", response_model=List[ContactResponse])
async def read_contacts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Отримати всі контакти користувача з пагінацією.

    Args:
        skip: Кількість записів для пропуску.
        limit: Максимальна кількість записів для повернення.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Список контактів.
    """
    contact_service = ContactService(db)
    contacts = await contact_service.get_contacts(user=user, skip=skip, limit=limit)
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Отримати контакт за його ID.

    Args:
        contact_id: Ідентифікатор контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        ContactResponse: Дані контакту.

    Raises:
        HTTPException: Якщо контакт не знайдено (404).
    """
    contact_service = ContactService(db)
    contact = await contact_service.get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Створити новий контакт.

    Args:
        body: Дані нового контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Створений контакт.
    """
    contact_service = ContactService(db)
    return await contact_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    body: ContactUpdate,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Оновити дані існуючого контакту.

    Args:
        body: Нові дані контакту.
        contact_id: Ідентифікатор контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Оновлений контакт.

    Raises:
        HTTPException: Якщо контакт не знайдено (404).
    """
    contact_service = ContactService(db)
    contact = await contact_service.update_contact(contact_id, body, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    contact_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Видалити контакт за його ID.

    Args:
        contact_id: Ідентифікатор контакту (>=1).
        db: Сесія бази даних.
        user: Поточний користувач.

    Raises:
        HTTPException: Якщо контакт не знайдено (404).

    Returns:
        None (HTTP 204).
    """
    svc = ContactService(db)
    ok = await svc.remove_contact(contact_id, user)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    # return nothing (204)
