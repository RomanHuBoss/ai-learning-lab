from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel, Field

from .services.rag import INDEX, RagDocument, answer_question, serialize_hit
from .services.sandbox import run_sandboxed
from .services.tutor import TutorRequest, ask_tutor
from .auth import get_current_user
from .models import User


router = APIRouter(prefix="/api")


class CodeRunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=8_000)
    timeout_seconds: int = Field(default=3, ge=1, le=10)


class RagDocumentInput(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=20_000)
    lesson_id: str | None = None
    source: str = "user"
    metadata: dict[str, str] = Field(default_factory=dict)


class RagIndexRequest(BaseModel):
    documents: list[RagDocumentInput] = Field(default_factory=list, max_length=500)
    replace: bool = False


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)
    top_k: int = Field(default=4, ge=1, le=10)


class RagEvalCase(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)
    expected_terms: list[str] = Field(default_factory=list, max_length=20)


class RagEvalRequest(BaseModel):
    cases: list[RagEvalCase] = Field(min_length=1, max_length=100)


class TutorAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)
    attempt: str = Field(default="", max_length=4_000)
    lesson_id: str | None = Field(default=None, max_length=40)
    hint_level: int = Field(default=1, ge=1, le=3)
    provider: str = Field(default="demo", max_length=40)


INJECTION_PATTERNS = re.compile(r"(ignore\s+(all|previous)|обойди\s+инструкц|раскрой\s+системн|покажи\s+секрет|выполни\s+команду)", re.IGNORECASE)


@router.post("/code/run")
def run_code(payload: CodeRunRequest) -> dict[str, object]:
    runner_url = os.getenv("RUNNER_URL", "").rstrip("/")
    if runner_url:
        try:
            response = httpx.post(f"{runner_url}/run", json=payload.model_dump(), timeout=payload.timeout_seconds + 2)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="sandbox_worker_unavailable") from exc
    result = run_sandboxed(payload.code, payload.timeout_seconds)
    return result.__dict__


@router.get("/sandbox/policy")
def sandbox_policy() -> dict[str, object]:
    return {
        "mode": "worker-http" if os.getenv("RUNNER_URL") else "isolated-subprocess-demo",
        "production_boundary": "rootless-worker-container",
        "network": "disabled-in-worker-container",
        "limits": {"timeout_seconds": 10, "code_chars": 8_000, "output_chars": 12_000, "memory_mb": 256, "pids": 32},
        "blocked_operations": ["network", "process creation", "filesystem escape", "dynamic code execution"],
    }


@router.get("/rag/status")
def rag_status() -> dict[str, object]:
    return {"documents": INDEX.count(), "provider": "local-lexical", "citations": True, "version": "rag-v1"}


@router.post("/rag/index")
def rag_index(payload: RagIndexRequest, user: User = Depends(get_current_user)) -> dict[str, object]:
    if user.role not in {"admin", "instructor", "mentor"}:
        raise HTTPException(status_code=403, detail="Индексировать материалы могут только наставники и администраторы")
    if payload.replace:
        INDEX.clear()
    documents = [RagDocument(**document.model_dump()) for document in payload.documents]
    count = INDEX.index(documents)
    return {"indexed": count, "documents": INDEX.count(), "version": "rag-v1"}


@router.get("/rag/search")
def rag_search(q: str = Query(min_length=1, max_length=1_000), top_k: int = Query(default=5, ge=1, le=10)) -> dict[str, object]:
    return {"query": q, "hits": [serialize_hit(hit) for hit in INDEX.search(q, top_k)], "documents": INDEX.count()}


@router.post("/rag/answer")
def rag_answer(payload: RagAnswerRequest) -> dict[str, object]:
    result = answer_question(payload.question, payload.top_k)
    result["prompt_version"] = "rag-answer-v1"
    return result


@router.post("/rag/evaluate")
def rag_evaluate(payload: RagEvalRequest) -> dict[str, object]:
    rows = []
    grounded = 0
    matched = 0
    for case in payload.cases:
        result = answer_question(case.question, 4)
        hits = result["citations"]
        hit_text = " ".join(str(item.get("snippet", "")) for item in hits).lower()
        expected = [term.lower() for term in case.expected_terms]
        is_match = not expected or any(term in hit_text for term in expected)
        matched += int(is_match)
        grounded += int(bool(result["grounded"]))
        rows.append({"question": case.question, "grounded": bool(result["grounded"]), "matched": is_match, "citations": hits})
    total = len(rows)
    return {"cases": rows, "retrieval_match_rate": round(matched / total, 4), "grounded_rate": round(grounded / total, 4), "citation_rate": round(sum(bool(row["citations"]) for row in rows) / total, 4), "version": "rag-eval-v1"}


@router.post("/tutor/ask")
def tutor_ask(payload: TutorAskRequest) -> dict[str, object]:
    if INJECTION_PATTERNS.search(payload.question):
        return {"provider": "demo", "mode": "blocked", "answer": "Я работаю только с учебной задачей. Сформулируйте вопрос по теме курса и добавьте свою попытку.", "citations": [], "grounded": False, "prompt_version": "demo-tutor-v1"}
    request = TutorRequest(payload.question, payload.attempt, payload.lesson_id, payload.hint_level)
    return ask_tutor(request, payload.provider)


@router.post("/tutor/stream")
async def tutor_stream(payload: TutorAskRequest) -> StreamingResponse:
    result = tutor_ask(payload)

    async def chunks() -> AsyncIterator[str]:
        for token in str(result["answer"]).split():
            yield json.dumps({"token": token + " ", "done": False}, ensure_ascii=False) + "\n"
        yield json.dumps({"done": True, "citations": result["citations"], "prompt_version": result["prompt_version"]}, ensure_ascii=False) + "\n"

    return StreamingResponse(chunks(), media_type="application/x-ndjson")
