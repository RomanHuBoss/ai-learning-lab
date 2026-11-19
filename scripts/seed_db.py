from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from api.auth import password_hasher
from api.database import SessionLocal, init_db
from api.models import Cohort, CohortMembership, Exam, Profile, ProfileVisibility, ProjectPublication, User
import json
import re


def normalize_lesson_id(value: str) -> str:
    value = str(value or '')
    return re.sub(r'^0(?=\d\.)', '', value)


def demo_exam_question_ids() -> list[str]:
    """Return the stable 50-question conceptual final exam."""
    return [f"exam-{index:03d}" for index in range(1, 51)]


def ensure_user(db, email: str, name: str, role: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, display_name=name, role=role, password_hash=password_hasher.hash(password))
    db.add(user)
    db.flush()
    return user


def ensure_profile(db, user: User, **values) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id, **values)
        db.add(profile)
        db.flush()
    if not profile.visibility:
        profile.visibility = ProfileVisibility(profile_id=profile.id, scope=values.get("visibility_scope", "owner"))
    return profile


def main() -> None:
    init_db()
    with SessionLocal() as db:
        admin = ensure_user(db, "admin@ai-learning.local", "Администратор", "admin", "AdminPass123!")
        mentor = ensure_user(db, "mentor@ai-learning.local", "Наставник", "mentor", "MentorPass123!")
        learner = ensure_user(db, "demo@ai-learning.local", "Демо-ученик", "learner", "DemoPass123!")
        ensure_profile(db, admin, status="learning", level="администратор")
        ensure_profile(db, mentor, status="learning", level="наставник")
        ensure_profile(db, learner, status="learning", level="начинающий")
        legacy_alumni = db.scalar(select(User).where(User.email == "alumni@ai-learning.local"))
        if legacy_alumni:
            legacy_profile = ensure_profile(db, legacy_alumni)
            legacy_profile.status = "learning"
            legacy_profile.completion_percent = 0
            legacy_profile.final_exam_passed = False
            legacy_profile.publish_in_catalog = False
            legacy_profile.visibility.scope = "owner"
            legacy_profile.visibility.show_projects = False
            legacy_profile.visibility.show_certificates = False
            for project in db.scalars(select(ProjectPublication).where(ProjectPublication.user_id == legacy_alumni.id)).all():
                project.is_public = False
        cohort = db.scalar(select(Cohort).where(Cohort.invite_code == "AI-DEMO"))
        if not cohort:
            cohort = Cohort(name="Демо-поток AI Learning Lab", invite_code="AI-DEMO", owner_id=mentor.id)
            db.add(cohort)
            db.flush()
        for user, role in ((mentor, "owner"), (learner, "learner")):
            exists = db.scalar(select(CohortMembership).where(CohortMembership.cohort_id == cohort.id, CohortMembership.user_id == user.id))
            if not exists:
                db.add(CohortMembership(cohort_id=cohort.id, user_id=user.id, membership_role=role))
        exam = db.scalar(select(Exam).where(Exam.version == "demo-1.0"))
        question_ids = demo_exam_question_ids()
        if not exam:
            db.add(Exam(title="Демо-экзамен AI Learning Lab", version="demo-1.0", question_ids=json.dumps(question_ids), pass_percent=75, is_published=True))
        elif json.loads(exam.question_ids or "[]") != question_ids:
            exam.question_ids = json.dumps(question_ids)
        db.commit()
    print("Seed complete. Demo accounts: demo@ai-learning.local / DemoPass123!, mentor@ai-learning.local / MentorPass123!, admin@ai-learning.local / AdminPass123!")


if __name__ == "__main__":
    main()
