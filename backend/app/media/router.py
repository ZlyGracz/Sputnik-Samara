"""Загрузка и выдача фото и аудио (POST /api/media, GET /api/media/{id}). Владелец: инфраструктура.

Контракт: docs/openapi.yaml (тег «Media»). Файлы хранятся в settings.media_dir
(в Docker — том media_data), метаданные — в таблице media.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Media"])

# TODO: реализовать эндпоинты по контракту
