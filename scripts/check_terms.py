"""Content lint for the Russian terminology and prerequisite graph."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def check_graph(curriculum: dict) -> list[str]:
    lessons = {lesson["id"]: lesson for lesson in curriculum["lessons"]}
    errors: list[str] = []
    for lesson in lessons.values():
        for prerequisite in lesson["prerequisite_ids"]:
            if prerequisite not in lessons:
                errors.append(f"{lesson['id']}: unknown prerequisite {prerequisite}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            errors.append("cycle: " + " -> ".join(trail + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for prerequisite in lessons[node]["prerequisite_ids"]:
            if prerequisite in lessons:
                visit(prerequisite, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for lesson_id in lessons:
        visit(lesson_id, [])
    return errors


def main() -> int:
    terms = load("terms.json")
    curriculum = load("curriculum.json")
    questions = load("questions.json")
    projects = load("projects.json")
    errors: list[str] = []
    required = {"approved_ru_term", "english_term", "short_definition", "extended_definition", "first_lesson_id", "related_concepts", "forbidden_or_discouraged_forms", "example", "hint_text"}
    seen_ru: set[str] = set()
    for index, term in enumerate(terms):
        missing = required - term.keys()
        if missing:
            errors.append(f"term[{index}] missing fields: {sorted(missing)}")
        if term.get("approved_ru_term") in seen_ru:
            errors.append(f"duplicate Russian term: {term.get('approved_ru_term')}")
        seen_ru.add(term.get("approved_ru_term", ""))
        if re.search(r"\b[A-Z]{2,}\b", term.get("short_definition", "")) and not term.get("acronym"):
            errors.append(f"unexplained acronym in {term.get('approved_ru_term')}")
    errors.extend(check_graph(curriculum))
    question_ids = {question.get("id") for question in questions}
    if len(questions) < 250:
        errors.append("questions.json must contain at least 250 questions")
    for question in questions:
        for field in ("prompt", "answer", "solution", "prerequisite_ids", "misconception_tags"):
            if field not in question:
                errors.append(f"{question.get('id')}: missing question field {field}")
    project_ids = {project.get("id") for project in projects}
    for lesson in curriculum["lessons"]:
        if lesson.get("assessment") not in question_ids and lesson.get("assessment") != "final-exam":
            errors.append(f"{lesson['id']}: missing assessment {lesson.get('assessment')}")
        if lesson.get("project") not in project_ids:
            errors.append(f"{lesson['id']}: missing project {lesson.get('project')}")
    full_program = load("full_program.json")
    labs = load("labs.json")["labs"]
    lesson_content = load("lesson_content.json")["lessons"]
    if len(full_program.get("modules", [])) != 25 or len(full_program.get("lessons", [])) != 100:
        errors.append("full_program.json must contain 25 modules and 100 lessons")
    if len(labs) < 26:
        errors.append("labs.json must contain at least 26 labs")
    required_lesson_blocks = {"learning_objectives", "what_is_known", "intuition", "visualization", "formal_explanation", "manual_example", "code_example", "interactive_lab", "independent_exercise", "misconceptions", "mini_test", "summary", "remediation", "spaced_repetition", "table", "formulas"}
    if len(lesson_content) != 100:
        errors.append("lesson_content.json must contain all 100 course lessons")
    program_ids = {str(lesson.get("id", "")).lstrip("0") for lesson in full_program.get("lessons", [])}
    content_ids = {str(lesson.get("lesson_id", "")).lstrip("0") for lesson in lesson_content}
    if program_ids != content_ids:
        errors.append("lesson_content.json ids must match full_program.json")
    for lesson in lesson_content:
        missing = required_lesson_blocks - lesson.keys()
        if missing:
            errors.append(f"lesson content {lesson.get('lesson_id')} missing: {sorted(missing)}")
        if not lesson.get("visualization", {}).get("graph"):
            errors.append(f"lesson content {lesson.get('lesson_id')} missing visualization.graph")
    if errors:
        print("CONTENT LINT FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"CONTENT LINT OK · {len(terms)} terms · {len(full_program['lessons'])} lessons · prerequisite graph acyclic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
