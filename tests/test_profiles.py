from uuid import uuid4

from fastapi.testclient import TestClient

from api.database import SessionLocal
from api.main import app
from api.models import User


client = TestClient(app)


def register(name: str) -> tuple[dict, dict]:
    response = client.post("/api/auth/register", json={"email": f"{name}-{uuid4().hex}@example.com", "display_name": name, "password": "SecurePass123!"})
    token = response.json()["access_token"]
    return response.json(), {"Authorization": f"Bearer {token}"}


def test_profile_visibility_and_alumni_catalog():
    user, headers = register("Выпускник")
    lessons = client.get("/api/full-program").json()["lessons"]
    progress = client.put("/api/me/progress", headers=headers, json={"completed_lessons": [lesson["id"] for lesson in lessons], "mastery": {"GNN": 100}, "next_review": []})
    assert progress.status_code == 200
    with SessionLocal() as db:
        db.get(User, user["user"]["id"]).profile.final_exam_passed = True
        db.commit()
    update = client.put("/api/profile/me", headers=headers, json={"display_name": "Выпускник ML", "bio": "Инженер ML", "status": "graduate", "level": "младший практик", "interests": ["GNN", "RAG"], "city": "Казань", "country": "Россия", "cohort_name": "Поток 2026", "start_date": "2026-09-01", "portfolio_url": "https://example.com/portfolio", "publish_in_catalog": True})
    assert update.status_code == 200
    restored = client.get("/api/profile/me", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["display_name"] == "Выпускник ML"
    assert restored.json()["level"] == "младший практик"
    assert restored.json()["interests"] == ["GNN", "RAG"]
    assert restored.json()["city"] == "Казань"
    assert restored.json()["country"] == "Россия"
    assert restored.json()["cohort_name"] == "Поток 2026"
    assert restored.json()["start_date"].startswith("2026-09-01")
    assert restored.json()["portfolio_url"] == "https://example.com/portfolio"
    visibility = client.put("/api/profile/me/visibility", headers=headers, json={"scope": "catalog", "show_projects": True, "show_certificates": True})
    assert visibility.status_code == 200
    project = client.post("/api/profile/me/projects", headers=headers, json={"title": "RAG-помощник", "summary": "Поиск по учебным материалам", "is_public": True})
    assert project.status_code == 200
    catalog = client.get("/api/alumni", params={"q": "GNN"})
    assert catalog.status_code == 200
    assert any(item["user_id"] == user["user"]["id"] for item in catalog.json())
    exported = client.get("/api/me/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["user"]["id"] == user["user"]["id"]


def test_mentor_dashboard_and_admin_export():
    admin, admin_headers = register("Наставник")
    admin_id = admin["user"]["id"]
    with SessionLocal() as db:
        db.get(User, admin_id).role = "mentor"
        db.commit()
    cohort = client.post("/api/cohorts", headers=admin_headers, json={"name": "Поток выпускников"})
    assert cohort.status_code == 201
    learner, learner_headers = register("Участник")
    joined = client.post("/api/cohorts/join", headers=learner_headers, params={"invite_code": cohort.json()["invite_code"]})
    assert joined.status_code == 200
    joined_cohorts = client.get("/api/cohorts", headers=learner_headers)
    assert joined_cohorts.status_code == 200
    assert joined_cohorts.json()[0]["invite_code"] == cohort.json()["invite_code"]
    dashboard = client.get(f"/api/mentor/cohorts/{cohort.json()['id']}/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["member_count"] >= 2
    with SessionLocal() as db:
        db.get(User, admin_id).role = "admin"
        db.commit()
    admin_dashboard = client.get("/api/admin/dashboard", headers=admin_headers)
    assert admin_dashboard.status_code == 200
    assert admin_dashboard.json()["users"] >= 2
    export = client.get("/api/admin/export/alumni.csv", headers=admin_headers)
    assert export.status_code == 200
    assert "display_name" in export.text


def test_profile_data_export_and_account_deletion():
    user, headers = register("Удаляемый пользователь")
    exported = client.get("/api/me/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["user"]["display_name"] == "Удаляемый пользователь"
    deleted = client.delete("/api/me/account", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
