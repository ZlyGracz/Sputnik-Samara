from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core import errors
from app.core.config import settings
from app.core.db import engine
from app.media.router import router as media_router
from app.routers import attempts, auth, courses, questions, users

app = FastAPI(
    title="Спутник Самарского университета — API",
    version="1.0.0",
    description="REST API платформы с курсами. Полный контракт — docs/openapi.yaml.",
)
errors.register(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


#errors.register(app)

for r in (auth.router, users.router, courses.router, questions.router,
          attempts.router, media_router):
    app.include_router(r)


@app.get("/api/health", tags=["System"], summary="Проверка работоспособности")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="База данных недоступна")
    return {"status": "ok"}
