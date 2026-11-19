from __future__ import annotations

import json
import os
import csv
import io
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.gzip import GZipMiddleware

from .feature_routes import router as feature_router
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .auth import LoginPayload, RegisterPayload, TokenResponse, UserPublic, authenticate, create_token, get_current_user, get_optional_user, password_hasher, user_public
from .database import SessionLocal, get_db, init_db
from .models import Attempt, AuditLog, Certificate, Cohort, CohortMembership, Enrollment, Exam, Profile, ProfileVisibility, ProgressRecord, ProjectPublication, User
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
APP = ROOT / "app"


def read_json(filename: str) -> Any:
    with (DATA / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


def audit_event(db: Session, action: str, actor_user_id: int | None = None, resource_type: str = "system", resource_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor_user_id, action=action, resource_type=resource_type, resource_id=resource_id, metadata_json=json.dumps(metadata or {}, ensure_ascii=False)))


class ProgressPayload(BaseModel):
    completed_lessons: list[str] = Field(default_factory=list)
    mastery: dict[str, int] = Field(default_factory=dict)
    next_review: list[str] = Field(default_factory=list)


progress_store: dict[str, ProgressPayload] = {"demo": ProgressPayload()}


def curriculum_lesson_ids() -> set[str]:
    return {normalize_lesson_id(item.get("id")) for item in read_json("full_program.json").get("lessons", []) if item.get("id")}


def normalize_lesson_id(value: Any) -> str:
    return re.sub(r"^0(?=\d\.)", "", str(value or "").strip())


def validate_progress_payload(payload: ProgressPayload) -> ProgressPayload:
    valid_ids = curriculum_lesson_ids()
    completed: list[str] = []
    for lesson_id in payload.completed_lessons:
        normalized = normalize_lesson_id(lesson_id)
        if normalized not in valid_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Неизвестный урок: {normalized}")
        if normalized not in completed:
            completed.append(normalized)
    mastery: dict[str, int] = {}
    for concept, value in payload.mastery.items():
        score = int(value)
        if not 0 <= score <= 100:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Оценка должна быть от 0 до 100: {concept}")
        mastery[str(concept).strip()] = score
    return ProgressPayload(completed_lessons=completed, mastery=mastery, next_review=payload.next_review)

@asynccontextmanager
async def lifespan(_application: FastAPI):
    ensure_db_ready()
    yield


app = FastAPI(title="AI Learning Lab API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWLIST", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(feature_router)

db_ready = False
try:
    init_db()
    db_ready = True
except Exception:
    db_ready = False


def ensure_db_ready(retries: int = 15, delay_seconds: float = 2.0) -> bool:
    global db_ready
    if db_ready:
        return True
    for attempt in range(retries):
        try:
            init_db()
            db_ready = True
            return True
        except Exception:
            if attempt + 1 < retries:
                time.sleep(delay_seconds)
    return False


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "ai-learning-lab"}


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    required = [DATA / "curriculum.json", DATA / "full_program.json", DATA / "lesson_content.json", DATA / "labs.json", DATA / "terms.json", DATA / "questions.json", DATA / "projects.json"]
    database_ok = False
    try:
        global db_ready
        if not db_ready:
            init_db()
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            database_ok = True
            db_ready = True
    except Exception:
        db_ready = False
    production = os.getenv("APP_ENV", "demo").lower() == "production"
    configured_secret = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", ""))
    secrets_ok = not production or (len(configured_secret) >= 32 and not configured_secret.startswith("change-me"))
    if not all(path.exists() for path in required) or not database_ok or not secrets_ok:
        raise HTTPException(status_code=503, detail="content_not_ready")
    return {"status": "ready", "content_version": "0.2.0"}


@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterPayload, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже зарегистрирован")
    user = User(email=email, display_name=payload.display_name.strip(), password_hash=password_hasher.hash(payload.password), role="learner")
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, status="learning", level="начинающий"))
    audit_event(db, "auth.register", user.id, "user", str(user.id))
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_token(user), user=user_public(user))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate(db, payload.email, payload.password)
    audit_event(db, "auth.login", user.id, "user", str(user.id))
    db.commit()
    return TokenResponse(access_token=create_token(user), user=user_public(user))


@app.get("/api/auth/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> UserPublic:
    return user_public(user)


class EnrollmentPayload(BaseModel):
    user_id: int | None = None
    course_key: str = Field(default="ai-learning-lab", min_length=2, max_length=120)


class ExamPublic(BaseModel):
    id: int
    title: str
    version: str
    question_count: int
    pass_percent: int


class AttemptSubmitPayload(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


def exam_question_ids(exam: Exam) -> list[str]:
    ids = json.loads(exam.question_ids or "[]")
    if ids:
        return [str(item) for item in ids]
    questions = read_json("questions.json")
    preferred = {f"exam-{index:03d}" for index in range(1, 51)}
    selected = [str(item["id"]) for item in questions if str(item.get("id")) in preferred]
    if selected:
        return selected
    return [str(item["id"]) for item in questions if item.get("type") not in {"code_output", "numeric"}][:10]


def exam_public(exam: Exam) -> ExamPublic:
    return ExamPublic(id=exam.id, title=exam.title, version=exam.version, question_count=len(exam_question_ids(exam)), pass_percent=exam.pass_percent)


@app.get("/api/enrollments")
def list_enrollments(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = list(db.scalars(select(Enrollment).where(Enrollment.user_id == user.id).order_by(Enrollment.started_at.desc())).all())
    return [{"id": row.id, "course_key": row.course_key, "status": row.status, "started_at": row.started_at.isoformat(), "completed_at": row.completed_at.isoformat() if row.completed_at else None} for row in rows]


@app.post("/api/enrollments", status_code=status.HTTP_201_CREATED)
def create_enrollment(payload: EnrollmentPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    target_id = payload.user_id or user.id
    if target_id != user.id and user.role not in {"admin", "instructor", "mentor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нельзя назначить курс другому пользователю")
    if not db.get(User, target_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    existing = db.scalar(select(Enrollment).where(Enrollment.user_id == target_id, Enrollment.course_key == payload.course_key))
    if existing:
        return {"id": existing.id, "course_key": existing.course_key, "status": existing.status, "created": False}
    enrollment = Enrollment(user_id=target_id, course_key=payload.course_key, assigned_by=user.id if target_id != user.id else None)
    db.add(enrollment)
    audit_event(db, "enrollment.created", user.id, "enrollment", str(target_id), {"course_key": payload.course_key})
    db.commit()
    db.refresh(enrollment)
    return {"id": enrollment.id, "course_key": enrollment.course_key, "status": enrollment.status, "created": True}


@app.get("/api/exams", response_model=list[ExamPublic])
def list_exams(db: Session = Depends(get_db)) -> list[ExamPublic]:
    return [exam_public(exam) for exam in db.scalars(select(Exam).where(Exam.is_published.is_(True)).order_by(Exam.created_at.desc())).all()]


@app.post("/api/exams/{exam_id}/start")
def start_exam(exam_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    exam = db.get(Exam, exam_id)
    if not exam or not exam.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Экзамен не найден")
    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_key == exam.course_key))
    if not enrollment:
        enrollment = Enrollment(user_id=user.id, course_key=exam.course_key)
        db.add(enrollment)
    attempt = Attempt(exam_id=exam.id, user_id=user.id, status="started")
    db.add(attempt)
    db.flush()
    audit_event(db, "exam.started", user.id, "exam", str(exam.id), {"attempt_id": attempt.id})
    db.commit()
    db.refresh(attempt)
    return {"attempt_id": attempt.id, "exam": exam_public(exam), "question_ids": exam_question_ids(exam)}


@app.post("/api/attempts/{attempt_id}/submit")
def submit_attempt(attempt_id: int, payload: AttemptSubmitPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    attempt = db.get(Attempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Попытка не найдена")
    if attempt.status == "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Попытка уже отправлена")
    exam = db.get(Exam, attempt.exam_id)
    question_map = {str(item["id"]): item for item in read_json("questions.json")}
    question_ids = exam_question_ids(exam)
    correct = 0
    for question_id in question_ids:
        expected = question_map.get(question_id, {}).get("answer")
        actual = payload.answers.get(question_id)
        if isinstance(expected, list) and isinstance(actual, list):
            if sorted(map(str, expected)) == sorted(map(str, actual)):
                correct += 1
        elif expected is not None and str(expected).strip().lower() == str(actual).strip().lower():
            correct += 1
    score = round(correct / max(len(question_ids), 1) * 100)
    attempt.answers = json.dumps(payload.answers, ensure_ascii=False)
    attempt.score_percent = score
    attempt.passed = score >= exam.pass_percent
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    if attempt.passed:
        profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
        if profile:
            profile.final_exam_passed = True
    audit_event(db, "exam.submitted", user.id, "attempt", str(attempt.id), {"exam_id": exam.id, "score_percent": score, "passed": attempt.passed})
    db.commit()
    return {"attempt_id": attempt.id, "exam_id": exam.id, "score_percent": score, "passed": attempt.passed, "question_count": len(question_ids)}


@app.get("/api/attempts/me")
def list_my_attempts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = list(db.scalars(select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.started_at.desc())).all())
    return [{"id": row.id, "exam_id": row.exam_id, "score_percent": row.score_percent, "passed": row.passed, "status": row.status, "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None} for row in rows]


@app.get("/api/admin/audit")
def list_audit_logs(limit: int = 100, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))).all())
    return [{"id": row.id, "actor_user_id": row.actor_user_id, "action": row.action, "resource_type": row.resource_type, "resource_id": row.resource_id, "metadata": json.loads(row.metadata_json or "{}"), "created_at": row.created_at.isoformat()} for row in rows]


@app.get("/api/me/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = ensure_profile(db, user)
    record = db.scalar(select(ProgressRecord).where(ProgressRecord.user_id == user.id))
    audit_event(db, "data.export", user.id, "user", str(user.id))
    db.commit()
    return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}, "profile": profile_view(profile, user, db, full=True), "progress": {"completed_lessons": json.loads(record.completed_lessons), "mastery": json.loads(record.mastery), "next_review": json.loads(record.next_review)} if record else None, "projects": [{"title": item.title, "summary": item.summary, "url": item.url, "status": item.status} for item in user.projects], "certificates": [{"title": item.title, "code": item.code, "issued_at": item.issued_at.isoformat()} for item in user.certificates]}


@app.delete("/api/me/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    user.is_active = False
    user.display_name = "Удалённый пользователь"
    user.email = f"deleted-{user.id}@invalid.local"
    audit_event(db, "account.deleted", user.id, "user", str(user.id))
    db.commit()


class CohortPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class CohortPublic(BaseModel):
    id: int
    name: str
    invite_code: str
    owner_id: int
    is_archived: bool
    member_count: int = 0


class MemberPublic(BaseModel):
    id: int
    display_name: str
    email: str
    role: str
    membership_role: str


class RolePayload(BaseModel):
    role: str = Field(pattern="^(learner|instructor|mentor|admin)$")


class ProfilePayload(BaseModel):
    bio: str = Field(default="", max_length=2_000)
    photo_url: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    start_date: str | None = Field(default=None, max_length=40)
    cohort_name: str | None = Field(default=None, max_length=120)
    status: str = Field(default="learning", pattern="^(learning|completed|graduate)$")
    level: str = Field(default="начинающий", max_length=64)
    interests: list[str] = Field(default_factory=list, max_length=20)
    portfolio_url: str | None = Field(default=None, max_length=500)
    completion_percent: int = Field(default=0, ge=0, le=100)
    final_exam_passed: bool = False
    publish_in_catalog: bool = False


class VisibilityPayload(BaseModel):
    scope: str = Field(default="owner", pattern="^(owner|cohort|mentors|catalog)$")
    show_projects: bool = False
    show_certificates: bool = False
    show_photo: bool = False
    show_contacts: bool = False


class ProjectPublicationPayload(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    summary: str = Field(default="", max_length=2_000)
    url: str | None = Field(default=None, max_length=500)
    status: str = Field(default="completed", pattern="^(in_progress|completed|review)$")
    is_public: bool = False


class CertificatePayload(BaseModel):
    user_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=3, max_length=120)
    is_public: bool = False


def ensure_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id, status="learning", level="начинающий")
        db.add(profile)
        db.flush()
    if not profile.visibility:
        profile.visibility = ProfileVisibility(profile_id=profile.id, scope="owner")
        db.flush()
    return profile


def profile_view(profile: Profile, viewer: User | None, db: Session, full: bool = False) -> dict[str, Any]:
    visibility = profile.visibility or ProfileVisibility(scope="owner")
    is_owner = viewer is not None and viewer.id == profile.user_id
    can_catalog = profile.status == "graduate" and profile.completion_percent >= 100 and profile.final_exam_passed and profile.publish_in_catalog and visibility.scope == "catalog"
    can_mentor = viewer is not None and viewer.role in {"mentor", "instructor", "admin"} and visibility.scope in {"mentors", "cohort", "catalog"}
    can_view = full or is_owner or can_catalog or can_mentor
    if not can_view:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Профиль закрыт настройками видимости")
    data: dict[str, Any] = {
        "user_id": profile.user_id,
        "display_name": profile.user.display_name,
        "bio": profile.bio,
        "city": profile.city,
        "country": profile.country,
        "start_date": profile.start_date.isoformat() if profile.start_date else None,
        "cohort_name": profile.cohort_name,
        "status": profile.status,
        "level": profile.level,
        "interests": json.loads(profile.interests or "[]"),
        "portfolio_url": profile.portfolio_url,
        "completion_percent": profile.completion_percent,
        "final_exam_passed": profile.final_exam_passed,
        "publish_in_catalog": profile.publish_in_catalog if is_owner or full else False,
        "visibility": {"scope": visibility.scope, "show_projects": visibility.show_projects, "show_certificates": visibility.show_certificates, "show_photo": visibility.show_photo, "show_contacts": visibility.show_contacts} if is_owner or full else None,
    }
    if visibility.show_photo and (is_owner or can_catalog or can_mentor):
        data["photo_url"] = profile.photo_url
    if visibility.show_contacts and (is_owner or full):
        data["email"] = profile.user.email
    if visibility.show_projects and (is_owner or can_catalog or can_mentor):
        data["projects"] = [{"title": item.title, "summary": item.summary, "url": item.url, "status": item.status} for item in profile.user.projects if item.is_public or is_owner or full]
    if visibility.show_certificates and (is_owner or can_catalog or can_mentor):
        data["certificates"] = [{"title": item.title, "code": item.code, "issued_at": item.issued_at.isoformat()} for item in profile.user.certificates if item.is_public or is_owner or full]
    return data


@app.get("/api/profile/me")
def get_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = ensure_profile(db, user)
    db.commit()
    return profile_view(profile, user, db, full=True)


@app.put("/api/profile/me")
def update_my_profile(payload: ProfilePayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = ensure_profile(db, user)
    values = payload.model_dump()
    start_date = values.pop("start_date")
    values["interests"] = json.dumps(values["interests"], ensure_ascii=False)
    values.pop("completion_percent", None)
    values.pop("final_exam_passed", None)
    progress = db.scalar(select(ProgressRecord).where(ProgressRecord.user_id == user.id))
    completion_percent = round(len(json.loads(progress.completed_lessons)) / max(len(curriculum_lesson_ids()), 1) * 100) if progress else 0
    profile.completion_percent = completion_percent
    requested_status = values.get("status", profile.status)
    if requested_status in {"completed", "graduate"} and (completion_percent < 100 or not profile.final_exam_passed):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Статус выпуска доступен после завершения курса и экзамена")
    profile.start_date = datetime.fromisoformat(start_date) if start_date else None
    for key, value in values.items():
        setattr(profile, key, value)
    user.display_name = user.display_name.strip() or "Ученик AI Learning Lab"
    audit_event(db, "profile.updated", user.id, "profile", str(profile.id))
    db.commit()
    db.refresh(profile)
    return profile_view(profile, user, db, full=True)


@app.put("/api/profile/me/visibility")
def update_profile_visibility(payload: VisibilityPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = ensure_profile(db, user)
    visibility = profile.visibility or ProfileVisibility(profile_id=profile.id)
    for key, value in payload.model_dump().items():
        setattr(visibility, key, value)
    profile.visibility = visibility
    audit_event(db, "profile.visibility_updated", user.id, "profile", str(profile.id), payload.model_dump())
    db.commit()
    return profile_view(profile, user, db, full=True)


@app.get("/api/profiles/{user_id}")
def get_profile(user_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile_view(profile, user, db)


@app.post("/api/profile/me/projects")
def add_project(payload: ProjectPublicationPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    project = ProjectPublication(user_id=user.id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, **payload.model_dump()}


@app.post("/api/profile/me/certificates")
def add_certificate(payload: CertificatePayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if user.role not in {"admin", "mentor", "instructor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Сертификаты выдаёт наставник или администратор")
    values = payload.model_dump()
    target_id = values.pop("user_id") or user.id
    if target_id != user.id and user.role not in {"admin", "mentor", "instructor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нельзя выдать сертификат другому пользователю")
    if not db.get(User, target_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    certificate = Certificate(user_id=target_id, **values)
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return {"id": certificate.id, "title": certificate.title, "code": certificate.code, "issued_at": certificate.issued_at.isoformat()}


@app.get("/api/alumni")
def alumni_catalog(q: str | None = None, status_filter: str | None = None, competency: str | None = None, project: str | None = None, sort: str = "name", db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    profiles = list(db.scalars(select(Profile).where(Profile.status == "graduate", Profile.completion_percent >= 100, Profile.final_exam_passed.is_(True), Profile.publish_in_catalog.is_(True))).all())
    result = []
    query = (q or "").lower().strip()
    for profile in profiles:
        visibility = profile.visibility or ProfileVisibility(scope="owner")
        if visibility.scope != "catalog":
            continue
        interests = json.loads(profile.interests or "[]")
        haystack = " ".join([profile.user.display_name, profile.bio, profile.level, profile.cohort_name or "", *interests]).lower()
        if query and query not in haystack:
            continue
        if status_filter and profile.status != status_filter:
            continue
        if competency and competency.lower() not in " ".join(interests).lower():
            continue
        if project and not any(project.lower() in item.title.lower() for item in profile.user.projects if item.is_public):
            continue
        result.append(profile_view(profile, None, db))
    if sort == "progress":
        result.sort(key=lambda item: item["completion_percent"], reverse=True)
    else:
        result.sort(key=lambda item: item["display_name"].lower())
    return result


@app.get("/api/mentor/cohorts/{cohort_id}/dashboard")
def mentor_dashboard(cohort_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if user.role not in {"mentor", "instructor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена")
    if user.role != "admin" and cohort.owner_id != user.id and not db.scalar(select(CohortMembership).where(CohortMembership.cohort_id == cohort_id, CohortMembership.user_id == user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к группе")
    lessons = [normalize_lesson_id(lesson["id"]) for lesson in read_json("full_program.json").get("lessons", [])]
    members = []
    for membership in cohort.memberships:
        record = db.scalar(select(ProgressRecord).where(ProgressRecord.user_id == membership.user_id))
        completed = json.loads(record.completed_lessons) if record else []
        members.append({"user_id": membership.user_id, "display_name": membership.user.display_name, "role": membership.user.role, "completed_lessons": len(completed), "total_lessons": len(lessons), "gaps": [lesson for lesson in lessons if lesson not in completed][:10], "projects_on_review": len([item for item in membership.user.projects if item.status == "review"])})
    return {"cohort_id": cohort.id, "cohort_name": cohort.name, "member_count": len(members), "members": members}


@app.get("/api/mentor/cohorts/{cohort_id}/export.csv")
def export_mentor_cohort(cohort_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    dashboard = mentor_dashboard(cohort_id, user, db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["user_id", "display_name", "role", "completed_lessons", "total_lessons", "gaps", "projects_on_review"])
    for member in dashboard["members"]:
        writer.writerow([member["user_id"], member["display_name"], member["role"], member["completed_lessons"], member["total_lessons"], "; ".join(member["gaps"]), member["projects_on_review"]])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=cohort-{cohort_id}.csv"})


@app.get("/api/admin/dashboard")
def admin_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    profiles = list(db.scalars(select(Profile)).all())
    recent_users = [{"id": item.id, "display_name": item.display_name, "email": item.email, "role": item.role} for item in db.scalars(select(User).order_by(User.created_at.desc()).limit(12)).all()]
    return {"users": db.query(User).count(), "cohorts": db.query(Cohort).count(), "graduates": sum(profile.status == "graduate" for profile in profiles), "published_alumni": sum(profile.publish_in_catalog and profile.status == "graduate" for profile in profiles), "average_completion": round(sum(profile.completion_percent for profile in profiles) / len(profiles), 2) if profiles else 0, "recent_users": recent_users}


@app.get("/api/admin/export/alumni.csv")
def export_alumni_csv(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    rows = alumni_catalog(db=db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["user_id", "display_name", "status", "level", "completion_percent", "interests", "portfolio_url"])
    for row in rows:
        writer.writerow([row["user_id"], row["display_name"], row["status"], row["level"], row["completion_percent"], ", ".join(row["interests"]), row.get("portfolio_url") or ""])
    audit_event(db, "admin.alumni_exported", user.id, "alumni", None, {"rows": len(rows)})
    db.commit()
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alumni.csv"})


def cohort_public(cohort: Cohort) -> CohortPublic:
    return CohortPublic(id=cohort.id, name=cohort.name, invite_code=cohort.invite_code, owner_id=cohort.owner_id, is_archived=cohort.is_archived, member_count=len(cohort.memberships))


@app.get("/api/cohorts", response_model=list[CohortPublic])
def list_cohorts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CohortPublic]:
    if user.role in {"admin", "instructor", "mentor"}:
        cohorts = list(db.scalars(select(Cohort).order_by(Cohort.created_at.desc())).all())
    else:
        cohorts = list(db.scalars(select(Cohort).join(CohortMembership).where(CohortMembership.user_id == user.id)).all())
    return [cohort_public(cohort) for cohort in cohorts]


@app.post("/api/cohorts", response_model=CohortPublic, status_code=status.HTTP_201_CREATED)
def create_cohort(payload: CohortPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CohortPublic:
    if user.role not in {"admin", "instructor", "mentor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только наставник или администратор может создать группу")
    code = f"AI-{user.id}-{int(datetime.now(timezone.utc).timestamp()) % 100000:05d}"
    cohort = Cohort(name=payload.name.strip(), invite_code=code, owner_id=user.id)
    db.add(cohort)
    db.flush()
    db.add(CohortMembership(cohort_id=cohort.id, user_id=user.id, membership_role="owner"))
    db.commit()
    db.refresh(cohort)
    return cohort_public(cohort)


@app.post("/api/cohorts/join", response_model=CohortPublic)
def join_cohort(invite_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CohortPublic:
    cohort = db.scalar(select(Cohort).where(Cohort.invite_code == invite_code, Cohort.is_archived.is_(False)))
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена")
    existing = db.scalar(select(CohortMembership).where(CohortMembership.cohort_id == cohort.id, CohortMembership.user_id == user.id))
    if not existing:
        db.add(CohortMembership(cohort_id=cohort.id, user_id=user.id, membership_role="learner"))
        db.commit()
        db.refresh(cohort)
    return cohort_public(cohort)


@app.get("/api/cohorts/{cohort_id}/members", response_model=list[MemberPublic])
def cohort_members(cohort_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MemberPublic]:
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена")
    membership = db.scalar(select(CohortMembership).where(CohortMembership.cohort_id == cohort_id, CohortMembership.user_id == user.id))
    if user.role not in {"admin", "instructor", "mentor"} and not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к группе")
    return [MemberPublic(id=item.user.id, display_name=item.user.display_name, email=item.user.email, role=item.user.role, membership_role=item.membership_role) for item in cohort.memberships]


@app.get("/api/admin/users", response_model=list[UserPublic])
def admin_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[UserPublic]:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return [user_public(item) for item in db.scalars(select(User).order_by(User.created_at.desc())).all()]


@app.patch("/api/admin/users/{user_id}/role", response_model=UserPublic)
def update_user_role(user_id: int, payload: RolePayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserPublic:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    target.role = payload.role
    audit_event(db, "admin.role_updated", user.id, "user", str(target.id), {"role": payload.role})
    db.commit()
    db.refresh(target)
    return user_public(target)


@app.post("/api/cohorts/{cohort_id}/archive", response_model=CohortPublic)
def archive_cohort(cohort_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CohortPublic:
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена")
    if user.role != "admin" and cohort.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только владелец или администратор может архивировать группу")
    cohort.is_archived = True
    db.commit()
    db.refresh(cohort)
    return cohort_public(cohort)


@app.get("/api/curriculum")
def curriculum() -> Any:
    return read_json("curriculum.json")


@app.get("/api/terms")
def terms() -> Any:
    return read_json("terms.json")


@app.get("/api/questions")
def questions() -> Any:
    return read_json("questions.json")


@app.get("/api/projects")
def projects() -> Any:
    return read_json("projects.json")


@app.get("/api/full-program")
def full_program() -> Any:
    return read_json("full_program.json")


@app.get("/api/labs")
def labs() -> Any:
    return read_json("labs.json")


@app.get("/api/lesson-content")
def lesson_content() -> Any:
    return read_json("lesson_content.json")


@app.get("/api/progress/{user_id}")
def get_progress(user_id: str, user: User | None = Depends(get_optional_user)) -> ProgressPayload:
    if user_id == "demo" and user is None:
        return progress_store["demo"]
    if user is None or str(user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ к чужому прогрессу запрещён")
    return progress_store.get(user_id, ProgressPayload())


@app.put("/api/progress/{user_id}")
def put_progress(user_id: str, payload: ProgressPayload, user: User = Depends(get_current_user)) -> ProgressPayload:
    if str(user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ к чужому прогрессу запрещён")
    normalized = validate_progress_payload(payload)
    progress_store[user_id] = normalized
    return normalized


@app.get("/api/me/progress", response_model=ProgressPayload)
def get_my_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressPayload:
    record = db.scalar(select(ProgressRecord).where(ProgressRecord.user_id == user.id))
    if not record:
        return ProgressPayload()
    return ProgressPayload(completed_lessons=json.loads(record.completed_lessons), mastery=json.loads(record.mastery), next_review=json.loads(record.next_review))


@app.put("/api/me/progress", response_model=ProgressPayload)
def put_my_progress(payload: ProgressPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressPayload:
    payload = validate_progress_payload(payload)
    record = db.scalar(select(ProgressRecord).where(ProgressRecord.user_id == user.id))
    values = {"completed_lessons": json.dumps(payload.completed_lessons, ensure_ascii=False), "mastery": json.dumps(payload.mastery, ensure_ascii=False), "next_review": json.dumps(payload.next_review, ensure_ascii=False)}
    if record:
        for key, value in values.items():
            setattr(record, key, value)
    else:
        db.add(ProgressRecord(user_id=user.id, **values))
    profile = ensure_profile(db, user)
    profile.completion_percent = round(len(payload.completed_lessons) / max(len(curriculum_lesson_ids()), 1) * 100)
    audit_event(db, "progress.updated", user.id, "progress", str(user.id), {"completed_lessons": len(payload.completed_lessons), "completion_percent": profile.completion_percent})
    db.commit()
    return payload


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(APP / "index.html")


app.mount("/", StaticFiles(directory=APP), name="app")
