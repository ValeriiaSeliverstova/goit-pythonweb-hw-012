# models.py
from datetime import date, datetime
from typing import Optional
from src.auth.roles import UserRole
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Text,
    Integer,
    UniqueConstraint,
    Index,
    func,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    extra_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("email", name="uq_contacts_email"),
        Index("ix_contacts_name_email", "first_name", "last_name", "email"),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(600), nullable=True)
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    avatar: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    public_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    confirmed = Column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.USER)
