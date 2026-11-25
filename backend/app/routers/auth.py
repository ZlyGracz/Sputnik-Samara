"""Регистрация, вход, /auth/me. Владелец: бэкенд.

Контракт: docs/openapi.yaml (тег «Auth»). Пути пишутся полностью после /api.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Auth"])

# TODO: реализовать эндпоинты по контракту
