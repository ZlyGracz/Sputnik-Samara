"""Вопросы и варианты: /courses/{id}/questions, /questions/{id}. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Questions»). Пути пишутся полностью после /api.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Questions"])

# TODO: реализовать эндпоинты по контракту
