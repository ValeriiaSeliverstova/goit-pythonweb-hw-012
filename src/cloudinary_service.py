import cloudinary
import cloudinary.uploader
import os
from typing import Tuple

# Ініціалізація з ENV (додайте у .env або змінні середовища)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_user_avatar(file_obj, user_id: int) -> Tuple[str, str]:
    """
    Завантажує аватар користувача.
    Повертає (secure_url, public_id). Перезаписує попередній avatar.
    """
    result = cloudinary.uploader.upload(
        file_obj,
        folder=f"users/{user_id}",
        public_id="avatar",
        overwrite=True,
        invalidate=True,
        resource_type="image",
        transformation=[{"fetch_format": "auto", "quality": "auto"}],
    )
    return result["secure_url"], result["public_id"]


def delete_asset(public_id: str):
    cloudinary.uploader.destroy(public_id, invalidate=True)
