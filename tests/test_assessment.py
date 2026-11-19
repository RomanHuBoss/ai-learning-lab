import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from api.database import SessionLocal
from api.main import app
from api.models import Exam, User
from scripts.seed_db import demo_exam_question_ids

client = TestClient(app)


def test_demo_exam_uses_conceptual_ai_questions():
    question_map = {item["id"]: item for item in json.loads(Path("data/questions.json").read_text(encoding="utf-8"))}
    ids = demo_exam_question_ids()
    assert len(ids) == 50
    assert ids == [f"exam-{index:03d}" for index in range(1, 51)]
    assert all(question_map[item]["type"] not in {"code_output", "numeric"} for item in ids)
    assert not any("len(" in question_map[item]["prompt"] or "2+3" in question_map[item]["prompt"] for item in ids)
    assert all(question_map[item]["lesson_id"] for item in ids)


def test_enrollment_exam_attempt_and_audit_flow():
    email = f"exam-{uuid4().hex}@example.com"
    registered = client.post("/api/auth/register", json={"email": email, "display_name": "Экзамен", "password": "SecurePass123!"})
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/enrollments", headers=headers, json={"course_key": "ai-learning-lab"}).status_code == 201
    with SessionLocal() as db:
        exam = Exam(title="Тестовый экзамен", version=f"test-{uuid4().hex}", question_ids=json.dumps(["q-001"]), pass_percent=50, is_published=True)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        exam_id = exam.id
    started = client.post(f"/api/exams/{exam_id}/start", headers=headers)
    assert started.status_code == 200
    attempt_id = started.json()["attempt_id"]
    question_bank = json.loads(Path("data/questions.json").read_text(encoding="utf-8"))
    q001 = next(item for item in question_bank if item["id"] == "q-001")
    submitted = client.post(f"/api/attempts/{attempt_id}/submit", headers=headers, json={"answers": {"q-001": q001["answer"]}})
    assert submitted.status_code == 200
    assert submitted.json()["passed"] is True
    profile = client.get("/api/profile/me", headers=headers).json()
    assert profile["final_exam_passed"] is True


def test_attempt_isolation_and_audit_requires_admin():
    first = client.post("/api/auth/register", json={"email": f"first-{uuid4().hex}@example.com", "display_name": "Первый", "password": "SecurePass123!"}).json()
    second = client.post("/api/auth/register", json={"email": f"second-{uuid4().hex}@example.com", "display_name": "Второй", "password": "SecurePass123!"}).json()
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    with SessionLocal() as db:
        exam = db.scalar(select(Exam).where(Exam.version.like("test-%")))
        exam_id = exam.id
    attempt = client.post(f"/api/exams/{exam_id}/start", headers=first_headers).json()["attempt_id"]
    assert client.post(f"/api/attempts/{attempt}/submit", headers=second_headers, json={"answers": {}}).status_code == 404
    assert client.get("/api/admin/audit", headers=first_headers).status_code == 403


def test_admin_audit_returns_persisted_events():
    registered = client.post("/api/auth/register", json={"email": f"audit-{uuid4().hex}@example.com", "display_name": "Аудит", "password": "SecurePass123!"}).json()
    user_id = registered["user"]["id"]
    with SessionLocal() as db:
        db.get(User, user_id).role = "admin"
        db.commit()
    response = client.get("/api/admin/audit", headers={"Authorization": f"Bearer {registered['access_token']}"})
    assert response.status_code == 200
    assert any(item["action"] == "auth.register" and item["actor_user_id"] == user_id for item in response.json())
