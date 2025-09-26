"""Users API endpoints: реєстрація, логін, профіль, email-підтвердження,
керування ролями, аватар, та відновлення паролю.
"""

from typing import Annotated
from urllib.parse import urljoin
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks,
    Request,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

from src.database.db import get_db
from src.schemas import (
    UserModel,
    UserResponse,
    TokenModel,
    TokenRefreshRequest,
    RequestEmail,
    RoleUpdate,
    ResetPasswordModel,
)
from src.services.users import UserService
from src.auth.auth import get_current_user, create_email_token, get_email_from_token
from src.auth.deps import admin_required
from src.emailer import mailer

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserModel,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Зареєструвати нового користувача та надіслати лист підтвердження email.

    Args:
        body: Дані нового користувача.
        request: Об’єкт запиту для формування базового URL.
        background_tasks: Черга фоновых задач для відправки листа.
        db: Сесія БД.

    Returns:
        Створений користувач.

    Raises:
        HTTPException: 409, якщо користувач з таким email уже існує.
    """
    try:
        new_user = await UserService(db).create_user(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # create email verification token
    token = create_email_token(
        {"sub": new_user.email, "token_type": "email_confirmation"}
    )

    base = str(request.base_url)
    verify_link = urljoin(base, f"api/users/confirmed_email/{token}")

    # queue email (background)
    mailer.enqueue_template(
        background_tasks,
        recipients=new_user.email,
        subject="Verify your email",
        template_name="verify_email.html",
        context={
            "fullname": new_user.username,
            "verify_link": verify_link,
        },
    )

    return new_user


@router.post("/login", response_model=TokenModel)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Увійти за email/паролем і отримати токени.

    Args:
        form: Дані форми OAuth2 (username=email, password).
        db: Сесія БД.

    Returns:
        TokenModel з access і refresh токенами.

    Raises:
        HTTPException: 401 для некоректних облікових даних.
    """
    try:
        return await UserService(db).login_by_email(form.username, form.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.put("/avatar", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Оновити аватар поточного користувача з файлу зображення.

    Args:
        file: Завантажений файл (``image/*``).
        db: Сесія БД.
        current_user: Поточний користувач (із токена).

    Returns:
        Оновлений користувач.

    Raises:
        HTTPException: 400 якщо файл не є зображенням;
                       404 якщо користувача/ресурс не знайдено;
                       502 для помилок завантаження/зовнішнього сервісу.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Тільки зображення дозволені")
    try:
        return await UserService(db).update_avatar_from_file(current_user.id, file.file)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Помилка завантаження: {e}")


@router.get("/secret")
async def read_item(current_user=Depends(get_current_user)):
    """Демо-ендпойнт, що повертає секретне повідомлення для автентифікованого користувача.

    Args:
        current_user: Поточний користувач.

    Returns:
        dict: Повідомлення та ім’я власника.
    """
    return {"message": "secret router", "owner": current_user.username}


@router.post("/refresh-token", response_model=TokenModel)
async def refresh_token(
    request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Оновити access-токен за дійсним refresh-токеном.

    Args:
        request: Об’єкт із `refresh_token`.
        db: Сесія БД.

    Returns:
        TokenModel з оновленими токенами.

    Raises:
        HTTPException: 401 якщо refresh-токен недійсний/прострочений.
    """
    try:
        return await UserService(db).refresh_access_token(request.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user=Depends(get_current_user)):
    """Повернути профіль поточного користувача.

    Args:
        current_user: Поточний користувач.

    Returns:
        UserResponse: Дані користувача.
    """
    return current_user


@router.get("/confirmed_email/{token}", status_code=status.HTTP_200_OK)
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """Підтвердити електронну пошту за токеном з листа.

    Args:
        token: Токен підтвердження з email.
        db: Сесія БД.

    Returns:
        dict: Повідомлення про статус підтвердження.

    Raises:
        HTTPException: 400 якщо токен некоректний або користувача не знайдено.
    """
    email = await get_email_from_token(token)
    user_service = UserService(db)

    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if getattr(user, "confirmed", False):
        return {"message": "Ваша електронна пошта вже підтверджена"}

    await user_service.confirmed_email(email)
    return {"message": "Електронну пошту підтверджено"}


@router.post("/request_email", status_code=status.HTTP_202_ACCEPTED)
async def request_email(
    body: RequestEmail,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Повторно надіслати лист підтвердження email.

    Args:
        body: Запит із адресою email.
        request: Об’єкт запиту для побудови verify-посилання.
        background_tasks: Черга фоновых задач для відправки листа.
        db: Сесія БД.

    Returns:
        dict: Повідомлення про відправку/стан підтвердження.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)
    if not user:
        return {"message": "Перевірте свою електронну пошту для підтвердження"}

    if getattr(user, "confirmed", False):
        return {"message": "Ваша електронна пошта вже підтверджена"}

    token = create_email_token({"sub": user.email, "token_type": "email_confirmation"})
    verify_link = urljoin(str(request.base_url), f"api/users/confirmed_email/{token}")

    mailer.enqueue_template(
        background_tasks,
        recipients=user.email,
        subject="Verify your email",
        template_name="verify_email.html",
        context={"fullname": user.username, "verify_link": verify_link},
    )
    return {"message": "Перевірте свою електронну пошту для підтвердження"}


@router.patch("/{user_id}/role", response_model=UserResponse)
async def change_role(
    payload: RoleUpdate,
    user_id: int,
    _: UserModel = Depends(admin_required),
    db: AsyncSession = Depends(get_db),
):
    """Змінити роль користувача (адміністраторський ендпойнт).

    Args:
        payload: Нове значення ролі.
        user_id: Ідентифікатор користувача-цілі.
        _: Аутентифікований актор із правами адміністратора.
        db: Сесія БД.

    Returns:
        UserResponse: Користувач із оновленою роллю.
    """
    service = UserService(db)
    user = await service.change_user_role(
        actor=_, target_user_id=user_id, new_role=payload.role
    )
    return user


@router.post("/password/forgot", status_code=202)
async def forgot_password(req: RequestEmail, db: AsyncSession = Depends(get_db)):
    """Надіслати лист із посиланням для скидання пароля.

    Args:
        req: Об’єкт із адресою email.
        db: Сесія БД.

    Returns:
        dict: Повідомлення про відправку.
    """
    service = UserService(db)
    await service.request_password_reset(req.email)
    return {"message": "Посилання на скидання паролю відправлено на пошту."}


@router.post("/password/reset", status_code=204)
async def reset_password(body: ResetPasswordModel, db: AsyncSession = Depends(get_db)):
    """Скинути пароль за токеном із листа.

    Args:
        body: Тіло запиту з токеном і новим паролем.
        db: Сесія БД.

    Returns:
        None: Повертає 204 No Content у разі успіху.
    """
    service = UserService(db)
    await service.reset_password(token=body.token, new_password=body.new_password)
