from fastapi.testclient import TestClient
from uuid import uuid4

from api.main import app
from api.database import SessionLocal
from api.models import User


client = TestClient(app)


def test_live_health():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health():
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_curriculum_contains_coverage_fields():
    lessons = client.get("/api/curriculum").json()["lessons"]
    assert len(lessons) >= 30
    assert all(lesson["prerequisite_ids"] is not None for lesson in lessons)
    assert all(lesson["assessment"] for lesson in lessons)


def test_full_program_and_lab_catalog_are_substantive():
    program = client.get("/api/full-program").json()
    labs = client.get("/api/labs").json()["labs"]
    questions = client.get("/api/questions").json()
    lesson_content = client.get("/api/lesson-content").json()["lessons"]
    assert len(program["modules"]) == 25
    assert len(program["lessons"]) == 100
    assert len(labs) >= 26
    assert len(questions) >= 250
    assert len(lesson_content) == 49
    assert all(content["learning_objectives"] and content["mini_test"] for content in lesson_content)
    assert any(lab["id"] == "graph-message-passing" for lab in labs)
    assert any(lab["id"] == "hardware-selector" for lab in labs)


def test_progress_round_trip():
    email = f"progress-test-{uuid4().hex}@example.com"
    register = client.post("/api/auth/register", json={"email": email, "display_name": "Прогресс", "password": "SecurePass123!"})
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    payload = {"completed_lessons": ["1.01", "1.02"], "mastery": {"python": 50}, "next_review": ["градиент"]}
    response = client.put("/api/me/progress", headers=headers, json=payload)
    assert response.status_code == 200
    assert client.get("/api/me/progress", headers=headers).json() == payload


def test_progress_isolation():
    email = f"isolation-test-{uuid4().hex}@example.com"
    register = client.post("/api/auth/register", json={"email": email, "display_name": "Изоляция", "password": "SecurePass123!"})
    token = register.json()["access_token"]
    user_id = register.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/progress/demo").status_code == 200
    assert client.get(f"/api/progress/{user_id + 1}", headers=headers).status_code == 403
    assert client.put(f"/api/progress/{user_id + 1}", headers=headers, json={}).status_code == 403


def test_register_login_me_and_private_progress():
    email = f"auth-test-{uuid4().hex}@example.com"
    register = client.post("/api/auth/register", json={"email": email, "display_name": "Тестовый ученик", "password": "SecurePass123!"})
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=headers).json()["email"] == email
    payload = {"completed_lessons": ["4.09"], "mastery": {"llm": 61}, "next_review": ["Веса модели"]}
    assert client.put("/api/me/progress", headers=headers, json=payload).json() == payload
    assert client.get("/api/me/progress", headers=headers).json() == payload
    login = client.post("/api/auth/login", json={"email": email, "password": "SecurePass123!"})
    assert login.status_code == 200


def test_cohort_access_is_role_aware():
    mentor = client.post("/api/auth/register", json={"email": f"mentor-test-{uuid4().hex}@example.com", "display_name": "Наставник", "password": "SecurePass123!"})
    assert mentor.status_code == 201
    # Registration always creates a learner. Only seeded or admin-managed users can create cohorts.
    assert client.post("/api/cohorts", headers={"Authorization": f"Bearer {mentor.json()['access_token']}"}, json={"name": "Закрытая группа"}).status_code == 403


def test_admin_can_manage_roles_and_create_cohort():
    email = f"admin-test-{uuid4().hex}@example.com"
    response = client.post("/api/auth/register", json={"email": email, "display_name": "Администратор", "password": "SecurePass123!"})
    token = response.json()["access_token"]
    user_id = response.json()["user"]["id"]
    with SessionLocal() as db:
        db.get(User, user_id).role = "admin"
        db.commit()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/admin/users", headers=headers).status_code == 200
    changed = client.patch(f"/api/admin/users/{user_id}/role", headers=headers, json={"role": "mentor"})
    assert changed.status_code == 200
    cohort = client.post("/api/cohorts", headers=headers, json={"name": "Тестовый поток"})
    assert cohort.status_code == 201
