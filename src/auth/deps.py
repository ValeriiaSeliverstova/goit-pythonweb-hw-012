from src.auth.auth import get_current_user
from src.schemas import UserModel
from fastapi import HTTPException, status, Depends
from src.auth.roles import UserRole


# Authorisation Check
async def admin_required(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Перевіряє, що поточний користувач має роль адміністратора.

    Args:
        current_user: Користувач, отриманий із токена доступу.

    Returns:
        UserModel: Поточний користувач, якщо він адміністратор.

    Raises:
        HTTPException: 403, якщо роль користувача не ADMIN.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current_user
