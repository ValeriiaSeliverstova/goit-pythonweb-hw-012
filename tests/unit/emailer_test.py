# tests/unit/test_emailer.py
import os

os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "secret")
os.environ.setdefault("MAIL_FROM", "test@example.com")
os.environ.setdefault("MAIL_SERVER", "smtp.example.com")
os.environ.setdefault("MAIL_PORT", "465")

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import BackgroundTasks

from src.emailer import Mailer


def _assert_message(msg, *, subject, recipients, template_body):
    from fastapi_mail import MessageSchema, MessageType

    assert isinstance(msg, MessageSchema)
    assert msg.subject == subject
    assert msg.recipients == recipients
    assert msg.template_body == template_body
    assert msg.subtype is MessageType.html


def test_enqueue_template_with_str_recipient(monkeypatch):
    m = Mailer()
    fm = Mock()
    m._fm = fm  # inject mock FastMail

    bt = BackgroundTasks()
    captured = {}

    def fake_add_task(func, msg, **kwargs):
        captured["func"] = func
        captured["msg"] = msg
        captured["kwargs"] = kwargs

    monkeypatch.setattr(bt, "add_task", fake_add_task)

    m.enqueue_template(
        bt,
        recipients="rcpt@example.com",
        subject="Hello",
        template_name="welcome.html",
        context={"name": "Val"},
    )

    assert captured["func"] is fm.send_message
    _assert_message(
        captured["msg"],
        subject="Hello",
        recipients=["rcpt@example.com"],
        template_body={"name": "Val"},
    )
    assert captured["kwargs"] == {"template_name": "welcome.html"}


def test_enqueue_template_with_list_recipients(monkeypatch):
    m = Mailer()
    fm = Mock()
    m._fm = fm

    bt = BackgroundTasks()
    captured = {}

    def fake_add_task(func, msg, **kwargs):
        captured["func"] = func
        captured["msg"] = msg
        captured["kwargs"] = kwargs

    monkeypatch.setattr(bt, "add_task", fake_add_task)

    m.enqueue_template(
        bt,
        recipients=["a@example.com", "b@example.com"],
        subject="Hi",
        template_name="note.html",
        context={"x": 1},
    )

    _assert_message(
        captured["msg"],
        subject="Hi",
        recipients=["a@example.com", "b@example.com"],
        template_body={"x": 1},
    )
    assert captured["kwargs"] == {"template_name": "note.html"}


@pytest.mark.asyncio
async def test_send_template_calls_fastmail(monkeypatch):
    m = Mailer()
    fm = Mock()
    fm.send_message = AsyncMock()
    m._fm = fm

    await m.send_template(
        recipients="solo@example.com",
        subject="Async",
        template_name="async.html",
        context={"k": "v"},
    )

    assert fm.send_message.await_count == 1
    called_args, called_kwargs = fm.send_message.await_args
    _assert_message(
        called_args[0],
        subject="Async",
        recipients=["solo@example.com"],
        template_body={"k": "v"},
    )
    assert called_kwargs == {"template_name": "async.html"}
