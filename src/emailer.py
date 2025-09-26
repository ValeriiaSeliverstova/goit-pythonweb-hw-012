"""Сервіс для відправки email-повідомлень із шаблонів (FastMail)."""

import os
from pathlib import Path
from typing import Dict, List, Union

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType


CONF = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME")),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "465")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.meta.ua"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "My App"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "false").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "true").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).resolve().parent / "email/templates",
)

RESET_TOKEN_TTL_MIN = 15


class Mailer:
    """Клас для асинхронної відправки email-листів на основі шаблонів."""

    def __init__(self) -> None:
        """Створює обгортку для FastMail із налаштованим ConnectionConfig."""
        self._fm = FastMail(CONF)

    def enqueue_template(
        self,
        background_tasks: BackgroundTasks,
        *,
        recipients: Union[str, List[str]],
        subject: str,
        template_name: str,
        context: Dict,
    ) -> None:
        """Додати задачу відправки email у чергу фонового процесу FastAPI.

        Args:
            background_tasks: Об’єкт BackgroundTasks.
            recipients: Email-адреса або список адрес.
            subject: Тема листа.
            template_name: Назва HTML-шаблону.
            context: Дані для шаблону.
        """
        if isinstance(recipients, str):
            recipients = [recipients]

        msg = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html,
        )
        background_tasks.add_task(
            self._fm.send_message, msg, template_name=template_name
        )

    async def send_template(
        self,
        *,
        recipients: Union[str, List[str]],
        subject: str,
        template_name: str,
        context: Dict,
    ) -> None:
        """Надіслати email із шаблону одразу (без фонового завдання)."""
        if isinstance(recipients, str):
            recipients = [recipients]

        msg = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html,
        )
        await self._fm.send_message(msg, template_name=template_name)

    def build_reset_url(self, token: str) -> str:
        """Сформувати посилання на сторінку скидання пароля у фронтенді."""
        base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
        return f"{base}/reset-password?token={token}"

    async def send_password_reset_email(self, email: str, token: str) -> None:
        """Відправити лист із посиланням для скидання паролю.

        Args:
            email: Email користувача.
            token: Токен для скидання паролю.
        """
        template_name = "password_reset.html"
        subject = "Instructions to change your Contacts App sign-in"
        context = {
            "reset_url": self.build_reset_url(token),
            "token": token,
            "email": email,
            "ttl_minutes": RESET_TOKEN_TTL_MIN,
        }
        await self.send_template(
            recipients=email,
            subject=subject,
            template_name=template_name,
            context=context,
        )


# simple singleton
mailer = Mailer()
