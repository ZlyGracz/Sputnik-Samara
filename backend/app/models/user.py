from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Identity, Index, String, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'creator', 'admin')", name="role_valid"),
        # email уникален без учёта регистра
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
        Index("ix_users_role", "role"),
        # быстрый поиск по подстроке (ILIKE '%...%') в админке
        Index(
            "ix_users_email_trgm", "email",
            postgresql_using="gin", postgresql_ops={"email": "gin_trgm_ops"},
        ),
        Index(
            "ix_users_full_name_trgm", "full_name",
            postgresql_using="gin", postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )
