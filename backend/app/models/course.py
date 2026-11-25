import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index,
    Integer, SmallInteger, String, Text, UniqueConstraint, func,
)
# `text` — имя колонки в моделях ниже, поэтому функцию SQL-выражений импортируем под другим именем
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, server_default="")
    cover_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=sa_text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="course", order_by="Question.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_courses_author_id", "author_id"),
        # каталог: опубликованные курсы, новые первыми
        Index("ix_courses_published_created", "created_at", postgresql_where=sa_text("is_published")),
        # поиск по названию и описанию
        Index(
            "ix_courses_title_trgm", "title",
            postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_courses_description_trgm", "description",
            postgresql_using="gin", postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    course_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courses.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(1000))
    image_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    audio_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="questions")
    options: Mapped[list["AnswerOption"]] = relationship(
        back_populates="question", order_by="AnswerOption.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        # DEFERRABLE: порядок вопросов можно менять внутри одной транзакции
        UniqueConstraint(
            "course_id", "position", name="uq_questions_course_position",
            deferrable=True, initially="DEFERRED",
        ),
    )


class AnswerOption(Base):
    """Вариант ответа. У вопроса ровно 4 варианта, один правильный (см. docs/db-schema.md)."""

    __tablename__ = "answer_options"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(String(300))
    is_correct: Mapped[bool] = mapped_column(Boolean, server_default=sa_text("false"))

    question: Mapped["Question"] = relationship(back_populates="options")

    __table_args__ = (
        CheckConstraint("position BETWEEN 1 AND 4", name="position_range"),
        UniqueConstraint("question_id", "position", name="uq_answer_options_question_position"),
        # нужен для составного внешнего ключа из attempt_answers:
        # гарантирует, что выбранный вариант принадлежит именно этому вопросу
        UniqueConstraint("id", "question_id", name="uq_answer_options_id_question"),
        # не больше одного правильного варианта на вопрос
        Index(
            "uq_answer_options_one_correct", "question_id",
            unique=True, postgresql_where=sa_text("is_correct"),
        ),
    )
