import pytest

from tests.conftest import API, login


def opts(correct=0):
    return [{"text": f"v{i}", "is_correct": i == correct} for i in range(4)]


def mk_course(client, h, n=2, publish=True, title="История России"):
    c = client.post(f"{API}/courses", json={"title": title, "description": "d"}, headers=h).json()
    for i in range(n):
        r = client.post(f"{API}/courses/{c['id']}/questions", json={"text": f"Q{i}", "options": opts(i)}, headers=h)
        assert r.status_code == 201, r.text
    if publish:
        assert client.patch(f"{API}/courses/{c['id']}", json={"is_published": True}, headers=h).status_code == 200
    return c["id"]


# ------------------------------------------------------------------ auth
def test_register_login_me(client):
    r = client.post(f"{API}/auth/register", json={"email": "A@Test.ru", "full_name": "Иван", "password": "password123", "role": "admin"})
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == "user" and body["user"]["email"] == "a@test.ru"
    h = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get(f"{API}/auth/me", headers=h).json()["id"] == body["user"]["id"]
    assert client.post(f"{API}/auth/register", json={"email": "a@TEST.ru", "full_name": "Иван", "password": "password123"}).status_code == 409
    assert client.post(f"{API}/auth/register", json={"email": "bad", "full_name": "И", "password": "short"}).status_code == 422
    assert client.post(f"{API}/auth/login", json={"email": "a@test.ru", "password": "wrong-pass"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "A@test.ru", "password": "password123"}).status_code == 200
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_users_admin(client, admin, make_user):
    user = make_user("u@t.ru")
    assert client.get(f"{API}/users", headers=user).status_code == 403
    assert client.get(f"{API}/users").status_code == 401
    page = client.get(f"{API}/users?search=U@T&limit=10", headers=admin).json()
    assert page["total"] == 1 and page["items"][0]["email"] == "u@t.ru" and page["limit"] == 10
    assert client.get(f"{API}/users?search=%25", headers=admin).json()["total"] == 0  # % не wildcard
    assert client.get(f"{API}/users?role=admin", headers=admin).json()["total"] == 1
    uid = page["items"][0]["id"]
    assert client.patch(f"{API}/users/{uid}", json={}, headers=admin).status_code == 422
    assert client.patch(f"{API}/users/{uid}", json={"role": "boss"}, headers=admin).status_code == 422
    assert client.patch(f"{API}/users/999", json={"role": "user"}, headers=admin).status_code == 404
    me = client.get(f"{API}/auth/me", headers=admin).json()
    assert client.patch(f"{API}/users/{me['id']}", json={"role": "user"}, headers=admin).status_code == 409
    assert client.patch(f"{API}/users/{me['id']}", json={"is_active": False}, headers=admin).status_code == 409
    # роль действует сразу, без перелогина
    assert client.post(f"{API}/courses", json={"title": "abc"}, headers=user).status_code == 403
    assert client.patch(f"{API}/users/{uid}", json={"role": "creator"}, headers=admin).json()["role"] == "creator"
    assert client.post(f"{API}/courses", json={"title": "abc"}, headers=user).status_code == 201
    # блокировка: токен перестаёт работать, вход закрыт (403)
    client.patch(f"{API}/users/{uid}", json={"is_active": False}, headers=admin)
    assert client.get(f"{API}/auth/me", headers=user).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "u@t.ru", "password": "password123"}).status_code == 403


# --------------------------------------------------------------- courses
def test_catalog_and_visibility(client, make_user, admin):
    c1, c2 = make_user("c1@t.ru", "creator"), make_user("c2@t.ru", "creator")
    pub = mk_course(client, c1, title="История России")
    draft = mk_course(client, c1, publish=False, title="Черновик Физики")
    # каталог публичный, без токена, только опубликованные
    page = client.get(f"{API}/courses").json()
    assert [c["id"] for c in page["items"]] == [pub] and page["total"] == 1
    assert page["items"][0]["questions_count"] == 2 and page["items"][0]["author"]["full_name"].startswith("User")
    assert client.get(f"{API}/courses?search=ИСТОР").json()["total"] == 1
    assert client.get(f"{API}/courses?search=физик").json()["total"] == 0  # черновик не в каталоге
    # одиночный курс
    assert client.get(f"{API}/courses/{pub}").status_code == 200
    assert client.get(f"{API}/courses/{draft}").status_code == 404
    assert client.get(f"{API}/courses/{draft}", headers=c2).status_code == 404
    assert client.get(f"{API}/courses/{draft}", headers=c1).status_code == 200
    assert client.get(f"{API}/courses/{draft}", headers=admin).status_code == 200
    # мои курсы
    assert {c["id"] for c in client.get(f"{API}/courses/my", headers=c1).json()["items"]} == {pub, draft}
    assert client.get(f"{API}/courses/my", headers=c2).json()["total"] == 0
    assert client.get(f"{API}/courses/my").status_code == 401
    # изменение: чужой опубликованный -> 403, чужой черновик -> 404, админ можно
    assert client.patch(f"{API}/courses/{pub}", json={"title": "хак!"}, headers=c2).status_code == 403
    assert client.patch(f"{API}/courses/{draft}", json={"title": "хак!"}, headers=c2).status_code == 404
    assert client.delete(f"{API}/courses/{pub}", headers=c2).status_code == 403
    assert client.patch(f"{API}/courses/{draft}", json={"title": "Админ"}, headers=admin).json()["title"] == "Админ"
    assert client.patch(f"{API}/courses/{draft}", json={}, headers=c1).status_code == 422
    assert client.patch(f"{API}/courses/{draft}", json={"title": None}, headers=c1).status_code == 422


def test_publish_requires_questions_and_cover(client, make_user, make_media):
    h = make_user("c@t.ru", "creator")
    cid = client.post(f"{API}/courses", json={"title": "Курс"}, headers=h).json()["id"]
    assert client.patch(f"{API}/courses/{cid}", json={"is_published": True}, headers=h).status_code == 409
    assert client.patch(f"{API}/courses/{cid}", json={"cover_media_id": make_media("audio")}, headers=h).status_code == 422
    assert client.patch(f"{API}/courses/{cid}", json={"cover_media_id": "00000000-0000-0000-0000-000000000000"}, headers=h).status_code == 422
    img = make_media("image")
    r = client.patch(f"{API}/courses/{cid}", json={"cover_media_id": img}, headers=h).json()
    assert r["cover_url"] == f"/api/media/{img}"
    assert client.patch(f"{API}/courses/{cid}", json={"cover_media_id": None}, headers=h).json()["cover_url"] is None
    assert client.delete(f"{API}/courses/{cid}", headers=h).status_code == 204
    assert client.get(f"{API}/courses/{cid}", headers=h).status_code == 404


# ------------------------------------------------------------- questions
def test_question_validation_media_and_positions(client, make_user, make_media):
    h, other = make_user("c@t.ru", "creator"), make_user("o@t.ru", "creator")
    cid = client.post(f"{API}/courses", json={"title": "Курс"}, headers=h).json()["id"]
    base = f"{API}/courses/{cid}/questions"
    two = opts(); two[1]["is_correct"] = True
    assert client.post(base, json={"text": "q", "options": opts()[:3]}, headers=h).status_code == 422
    assert client.post(base, json={"text": "q", "options": two}, headers=h).status_code == 422
    assert client.post(base, json={"text": "q", "options": [{**o, "is_correct": False} for o in opts()]}, headers=h).status_code == 422
    assert client.post(base, json={"text": "q", "options": opts(), "image_media_id": make_media("audio")}, headers=h).status_code == 422
    assert client.post(base, json={"text": "q", "options": opts(), "audio_media_id": make_media("image")}, headers=h).status_code == 422
    img, aud = make_media("image"), make_media("audio")
    q1 = client.post(base, json={"text": "Фото-вопрос", "image_media_id": img, "audio_media_id": aud, "options": opts(2)}, headers=h)
    assert q1.status_code == 201, q1.text
    q1 = q1.json()
    assert q1["position"] == 1 and q1["image_url"] == f"/api/media/{img}" and q1["audio_url"] == f"/api/media/{aud}"
    assert [o["is_correct"] for o in q1["options"]] == [False, False, True, False]
    q2 = client.post(base, json={"text": "Второй", "options": opts()}, headers=h).json()
    q3 = client.post(base, json={"text": "Третий, на 1-ю позицию", "position": 1, "options": opts()}, headers=h).json()
    order = lambda: [(q["text"], q["position"]) for q in client.get(base, headers=h).json()]
    assert order() == [("Третий, на 1-ю позицию", 1), ("Фото-вопрос", 2), ("Второй", 3)]
    # PUT: переставить на последнюю позицию, сменить правильный вариант (старые id вариантов сохраняются)
    old_ids = [o["id"] for o in q1["options"]]
    r = client.put(f"{API}/questions/{q1['id']}", json={"text": "Новый текст", "position": 3, "options": opts(0)}, headers=h)
    assert r.status_code == 200, r.text
    r = r.json()
    assert r["text"] == "Новый текст" and r["position"] == 3 and r["image_url"] is None
    assert [o["id"] for o in r["options"]] == old_ids and [o["is_correct"] for o in r["options"]] == [True, False, False, False]
    assert order() == [("Третий, на 1-ю позицию", 1), ("Второй", 2), ("Новый текст", 3)]
    # доступ
    assert client.get(base, headers=other).status_code == 404  # черновик чужого
    assert client.put(f"{API}/questions/{q2['id']}", json={"text": "x", "options": opts()}, headers=other).status_code == 404
    assert client.delete(f"{API}/questions/{q2['id']}", headers=other).status_code == 404
    assert client.put(f"{API}/questions/9999", json={"text": "x", "options": opts()}, headers=h).status_code == 404
    # удаление -> позиции без пропусков
    assert client.delete(f"{API}/questions/{q3['id']}", headers=h).status_code == 204
    assert order() == [("Второй", 1), ("Новый текст", 2)]
    # студент не видит вопросы с ответами
    student = make_user("s@t.ru")
    assert client.get(base, headers=student).status_code == 403
    assert client.get(base).status_code == 401


def test_published_course_questions_403_for_foreign_creator(client, make_user):
    h, other = make_user("c@t.ru", "creator"), make_user("o@t.ru", "creator")
    cid = mk_course(client, h)
    q = client.get(f"{API}/courses/{cid}/questions", headers=h).json()[0]
    assert client.get(f"{API}/courses/{cid}/questions", headers=other).status_code == 403
    assert client.post(f"{API}/courses/{cid}/questions", json={"text": "x", "options": opts()}, headers=other).status_code == 403
    assert client.put(f"{API}/questions/{q['id']}", json={"text": "x", "options": opts()}, headers=other).status_code == 403
    assert client.delete(f"{API}/questions/{q['id']}", headers=other).status_code == 403


# -------------------------------------------------------------- attempts
def test_attempt_flow(client, make_user):
    creator, student, other = make_user("c@t.ru", "creator"), make_user("s@t.ru"), make_user("o@t.ru")
    cid = mk_course(client, creator, n=3)
    qs = client.get(f"{API}/courses/{cid}/questions", headers=creator).json()
    r = client.post(f"{API}/courses/{cid}/attempts", headers=student)
    assert r.status_code == 201
    att = r.json()
    assert att["status"] == "in_progress" and att["total_questions"] == 3 and att["answered_count"] == 0
    assert att["score"] is None and att["percent"] is None
    for q in att["questions"]:  # до ответа правильное не раскрывается
        assert q["correct_option_id"] is None and q["is_correct"] is None and q["selected_option_id"] is None
        assert all(set(o) == {"id", "text"} for o in q["options"])
    assert client.post(f"{API}/courses/{cid}/attempts", headers=student).json()["id"] == att["id"]  # продолжение
    url = f"{API}/attempts/{att['id']}"
    q0, q1, q2 = qs
    ok0 = next(o for o in q0["options"] if o["is_correct"])
    bad1 = next(o for o in q1["options"] if not o["is_correct"])
    # изоляция
    body = {"question_id": q0["id"], "option_id": ok0["id"]}
    assert client.post(f"{url}/answers", json=body, headers=other).status_code == 404
    assert client.get(url, headers=other).status_code == 404
    assert client.post(f"{url}/finish", headers=other).status_code == 404
    assert client.get(url).status_code == 401
    r = client.post(f"{url}/answers", json=body, headers=student)
    assert r.status_code == 201 and r.json() == {"question_id": q0["id"], "selected_option_id": ok0["id"], "is_correct": True, "correct_option_id": ok0["id"]}
    assert client.post(f"{url}/answers", json=body, headers=student).status_code == 409
    r = client.post(f"{url}/answers", json={"question_id": q1["id"], "option_id": bad1["id"]}, headers=student).json()
    assert r["is_correct"] is False and r["correct_option_id"] != bad1["id"]
    assert client.post(f"{url}/answers", json={"question_id": q2["id"], "option_id": ok0["id"]}, headers=student).status_code == 422
    assert client.post(f"{url}/answers", json={"question_id": 99999, "option_id": ok0["id"]}, headers=student).status_code == 422
    d = client.get(url, headers=student).json()
    assert d["answered_count"] == 2
    assert d["questions"][0]["is_correct"] is True and d["questions"][1]["is_correct"] is False
    assert d["questions"][2]["correct_option_id"] is None  # без ответа не раскрыт
    res = client.post(f"{url}/finish", headers=student).json()
    assert (res["status"], res["score"], res["total_questions"], res["percent"]) == ("finished", 1, 3, 33.3)
    assert res["finished_at"] is not None
    assert client.post(f"{url}/finish", headers=student).json()["score"] == 1  # идемпотентно
    assert client.post(f"{url}/answers", json={"question_id": q2["id"], "option_id": q2["options"][0]["id"]}, headers=student).status_code == 409
    # после завершения новая попытка — отдельная
    assert client.post(f"{API}/courses/{cid}/attempts", headers=student).json()["id"] != att["id"]
    hist = client.get(f"{API}/attempts/my", headers=student).json()
    assert hist["total"] == 2 and hist["items"][1]["id"] == att["id"] and hist["items"][1]["course_title"] == "История России"
    assert client.get(f"{API}/attempts/my?course_id=999", headers=student).json()["total"] == 0
    assert client.get(f"{API}/attempts/my", headers=other).json()["total"] == 0


def test_cannot_play_unpublished_or_empty(client, make_user):
    creator, student = make_user("c@t.ru", "creator"), make_user("s@t.ru")
    draft = mk_course(client, creator, publish=False)
    assert client.post(f"{API}/courses/{draft}/attempts", headers=student).status_code == 404
    assert client.post(f"{API}/courses/{draft}/attempts", headers=creator).status_code == 404
    assert client.post(f"{API}/courses/9999/attempts", headers=student).status_code == 404
    assert client.post(f"{API}/courses/{draft}/attempts").status_code == 401
    # опубликованный, но опустевший курс
    cid = mk_course(client, creator, n=1)
    q = client.get(f"{API}/courses/{cid}/questions", headers=creator).json()[0]
    client.delete(f"{API}/questions/{q['id']}", headers=creator)
    assert client.post(f"{API}/courses/{cid}/attempts", headers=student).status_code == 409


def test_stats(client, make_user, admin):
    creator, s1, s2, other = make_user("c@t.ru", "creator"), make_user("s1@t.ru"), make_user("s2@t.ru"), make_user("o@t.ru", "creator")
    cid = mk_course(client, creator, n=2)
    qs = client.get(f"{API}/courses/{cid}/questions", headers=creator).json()

    def play(h, picks):
        att = client.post(f"{API}/courses/{cid}/attempts", headers=h).json()
        for q, good in picks:
            o = next(o for o in q["options"] if o["is_correct"] == good)
            assert client.post(f"{API}/attempts/{att['id']}/answers", json={"question_id": q["id"], "option_id": o["id"]}, headers=h).status_code == 201
        return att["id"]

    a1 = play(s1, [(qs[0], True), (qs[1], True)])      # 2/2
    client.post(f"{API}/attempts/{a1}/finish", headers=s1)
    a2 = play(s2, [(qs[0], True), (qs[1], False)])     # 1/2
    client.post(f"{API}/attempts/{a2}/finish", headers=s2)
    client.post(f"{API}/courses/{cid}/attempts", headers=s1)  # незавершённая
    st = client.get(f"{API}/courses/{cid}/stats", headers=creator).json()
    assert (st["attempts_count"], st["finished_count"], st["average_percent"]) == (3, 2, 75.0)
    assert [(q["answers_count"], q["correct_rate"]) for q in st["questions"]] == [(2, 1.0), (2, 0.5)]
    assert client.get(f"{API}/courses/{cid}/stats", headers=admin).status_code == 200
    assert client.get(f"{API}/courses/{cid}/stats", headers=other).status_code == 403
    assert client.get(f"{API}/courses/{cid}/stats", headers=s1).status_code == 403
    # курс без попыток
    empty = mk_course(client, creator, n=1)
    st = client.get(f"{API}/courses/{empty}/stats", headers=creator).json()
    assert st["attempts_count"] == 0 and st["average_percent"] == 0 and st["questions"][0]["correct_rate"] == 0


def test_put_keeps_student_answers(client, make_user):
    """PUT обновляет варианты на месте — ответы студентов не пропадают."""
    creator, student = make_user("c@t.ru", "creator"), make_user("s@t.ru")
    cid = mk_course(client, creator, n=1)
    q = client.get(f"{API}/courses/{cid}/questions", headers=creator).json()[0]
    att = client.post(f"{API}/courses/{cid}/attempts", headers=student).json()
    client.post(f"{API}/attempts/{att['id']}/answers", json={"question_id": q["id"], "option_id": q["options"][1]["id"]}, headers=student)
    r = client.put(f"{API}/questions/{q['id']}", json={"text": "Правка", "options": opts(1)}, headers=creator)
    assert r.status_code == 200
    d = client.get(f"{API}/attempts/{att['id']}", headers=student).json()
    assert d["answered_count"] == 1 and d["questions"][0]["is_correct"] is True and d["questions"][0]["text"] == "Правка"
