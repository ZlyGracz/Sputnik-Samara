"""Единый формат ошибок: всегда {"detail": "текст на русском"}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

FIELDS = {
    "email": "email", "password": "пароль", "full_name": "имя", "title": "название",
    "description": "описание", "text": "текст", "options": "варианты ответа",
    "role": "роль", "is_active": "активность", "question_id": "вопрос",
    "option_id": "вариант", "limit": "limit", "offset": "offset",
}

STATUS_TEXT = {
    404: "Не найдено", 405: "Метод не поддерживается",
    401: "Требуется авторизация", 403: "Недостаточно прав",
}


def _message(err: dict) -> str:
    t, ctx, msg = err["type"], err.get("ctx") or {}, err["msg"]
    if t == "missing":
        return "обязательное поле"
    if t == "string_too_short":
        return f"минимум символов: {ctx.get('min_length')}"
    if t == "string_too_long":
        return f"максимум символов: {ctx.get('max_length')}"
    if t == "too_short":
        return f"минимум элементов: {ctx.get('min_length')}"
    if t == "too_long":
        return f"максимум элементов: {ctx.get('max_length')}"
    if t in ("int_parsing", "int_type"):
        return "должно быть целым числом"
    if t in ("greater_than_equal", "greater_than"):
        return f"значение не меньше {ctx.get('ge', ctx.get('gt'))}"
    if t in ("less_than_equal", "less_than"):
        return f"значение не больше {ctx.get('le', ctx.get('lt'))}"
    if t == "uuid_parsing":
        return "некорректный идентификатор файла"
    if t in ("bool_parsing", "bool_type"):
        return "должно быть true или false"
    if t == "literal_error":
        return "недопустимое значение"
    if t == "json_invalid":
        return "некорректный JSON"
    if t == "value_error":
        if "email" in msg.lower():
            return "некорректный email"
        return msg.removeprefix("Value error, ")  # ваши сообщения из валидаторов
    return "некорректное значение"


async def validation_handler(request: Request, exc: RequestValidationError):
    parts = []
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        field = FIELDS.get(loc[-1] if loc else "", None)
        # для вложенных полей списка (options.0.text) оставляем «вариант ответа»
        text = _message(err)
        parts.append(f"{field}: {text}" if field and err["type"] != "value_error" else text)
    return JSONResponse(status_code=422, content={"detail": "; ".join(dict.fromkeys(parts)) or "Некорректные данные"})


async def http_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса"
    if detail in ("Not Found", "Method Not Allowed"):  # стандартные английские тексты Starlette
        detail = STATUS_TEXT.get(exc.status_code, detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail},
                        headers=getattr(exc, "headers", None))  # важно: WWW-Authenticate у 401


async def unhandled_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


def register(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_handler)
    app.add_exception_handler(Exception, unhandled_handler)