"""Тесты идут на настоящем PostgreSQL (схема — через Alembic).

TEST_DATABASE_URL по умолчанию: postgresql+psycopg://sputnik:sputnik_dev_password@localhost:5433/sputnik_test
(порт 5433 — БД из docker compose; создайте базу: docker compose exec db createdb -U sputnik sputnik_test)
"""
import os
import uuid

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sputnik:sputnik_dev_password@localhost:5433/sputnik_test"
)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models import Media, User

API = "/api"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture()
def client(_schema):
    with engine.begin() as c:
        c.execute(text("TRUNCATE users, media, courses, questions, answer_options, attempts, attempt_answers RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        db.add(User(email="admin@test.ru", full_name="Admin", password_hash=hash_password("adminpass1"), role="admin"))
        db.commit()
    with TestClient(app) as c:
        yield c


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, email, password="password123"):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return hdr(r.json()["access_token"])


@pytest.fixture()
def admin(client):
    return login(client, "admin@test.ru", "adminpass1")


@pytest.fixture()
def make_user(client, admin):
    def _make(email, role="user"):
        r = client.post(f"{API}/auth/register", json={"email": email, "full_name": "User " + email, "password": "password123"})
        assert r.status_code == 201, r.text
        if role != "user":
            assert client.patch(f"{API}/users/{r.json()['user']['id']}", json={"role": role}, headers=admin).status_code == 200
        return login(client, email)
    return _make


@pytest.fixture()
def make_media():
    def _make(kind="image"):
        mid = uuid.uuid4()
        with SessionLocal() as db:
            db.add(Media(id=mid, kind=kind, content_type="image/png" if kind == "image" else "audio/mpeg",
                         size_bytes=10, storage_path=f"{mid}.bin"))
            db.commit()
        return str(mid)
    return _make
