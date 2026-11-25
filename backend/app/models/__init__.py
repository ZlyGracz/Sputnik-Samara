"""Все модели импортируются здесь, чтобы Alembic видел полную схему."""
from app.models.attempt import Attempt, AttemptAnswer
from app.models.course import AnswerOption, Course, Question
from app.models.media import Media
from app.models.user import User

__all__ = [
    "User", "Media", "Course", "Question", "AnswerOption", "Attempt", "AttemptAnswer",
]
