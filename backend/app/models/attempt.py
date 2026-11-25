from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Identity,
    Index, Integer, String, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Attempt(Base):
    """Попытка прохождения курса пользователем."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    course_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courses.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(20), server_default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Фиксируются при старте / завершении, чтобы результат не менялся,
    # если автор потом правит курс (осознанная денормализация).
    total_questions: Mapped[int] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'finished')", name="status_valid"),
        CheckConstraint("total_questions >= 1", name="total_positive"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= total_questions)", name="score_range"
        ),
        CheckConstraint(
            "(status = 'in_progress' AND finished_at IS NULL AND score IS NULL) OR "
            "(status = 'finished' AND finished_at IS NOT NULL AND score IS NOT NULL)",
            name="finished_consistent",
        ),
        # «мои попытки», новые первыми
        Index("ix_attempts_user_started", "user_id", text("started_at DESC")),
        Index("ix_attempts_course_id", "course_id"),
    )


class AttemptAnswer(Base):
    """Ответ пользователя на вопрос в рамках попытки. Правильность считается через answer_options."""

    __tablename__ = "attempt_answers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("attempts.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE")
    )
    option_id: Mapped[int] = mapped_column(BigInteger)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attempt: Mapped["Attempt"] = relationship(back_populates="answers")

    __table_args__ = (
        # один ответ на вопрос в попытке
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_attempt_question"),
        # выбранный вариант обязан принадлежать этому же вопросу
        ForeignKeyConstraint(
            ["option_id", "question_id"],
            ["answer_options.id", "answer_options.question_id"],
            ondelete="CASCADE", name="fk_attempt_answers_option_question",
        ),
        # статистика по вопросу
        Index("ix_attempt_answers_question_id", "question_id"),
    )
