"""Small, deterministic local retrieval layer for course materials."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TOKEN_RE = re.compile(r"[\wÀ-ÿА-Яа-яЁё]+", re.UNICODE)


@dataclass(frozen=True)
class RagDocument:
    id: str
    title: str
    text: str
    lesson_id: str | None = None
    source: str = "course"
    metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class RagHit:
    id: str
    title: str
    snippet: str
    score: float
    citation: str
    lesson_id: str | None
    metadata: dict[str, str]


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def make_snippet(text: str, limit: int = 280) -> str:
    """Return a compact citation fragment without an orphaned conjunction."""
    snippet = " ".join(text.split())
    if len(snippet) > limit:
        snippet = snippet[: limit - 3].rstrip() + "…"
    return re.sub(r"^(?:и|или|а|но)\s+", "", snippet, flags=re.IGNORECASE)


class LocalRagIndex:
    def __init__(self) -> None:
        self._lock = RLock()
        self._documents: dict[str, RagDocument] = {}
        self._tokens: dict[str, list[str]] = {}
        self._idf: dict[str, float] = {}

    def index(self, documents: Iterable[RagDocument]) -> int:
        incoming: list[RagDocument] = []
        for document in documents:
            text = document.text.strip()
            chunk_size = 900
            overlap = 120
            if len(text) <= chunk_size:
                incoming.append(document)
                continue
            start = 0
            chunk_number = 0
            while start < len(text):
                end = min(len(text), start + chunk_size)
                incoming.append(RagDocument(f"{document.id}#chunk-{chunk_number}", document.title, text[start:end], document.lesson_id, document.source, document.metadata or {}))
                if end == len(text):
                    break
                start = end - overlap
                chunk_number += 1
        with self._lock:
            for document in incoming:
                self._documents[document.id] = document
                self._tokens[document.id] = tokenize(document.text)
            document_count = max(len(self._documents), 1)
            frequencies: dict[str, int] = {}
            for tokens in self._tokens.values():
                for token in set(tokens):
                    frequencies[token] = frequencies.get(token, 0) + 1
            self._idf = {token: math.log((1 + document_count) / (1 + count)) + 1 for token, count in frequencies.items()}
            return len(self._documents)

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._tokens.clear()
            self._idf.clear()

    def search(self, query: str, top_k: int = 5) -> list[RagHit]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        with self._lock:
            scored: list[tuple[float, RagDocument]] = []
            query_set = set(query_tokens)
            for document_id, tokens in self._tokens.items():
                counts = {token: tokens.count(token) for token in query_set if token in tokens}
                if not counts:
                    continue
                score = sum((1 + math.log(count)) * self._idf.get(token, 1.0) for token, count in counts.items())
                score /= math.sqrt(max(len(tokens), 1))
                title_tokens = set(tokenize(self._documents[document_id].title))
                score += 0.15 * len(query_set & title_tokens)
                scored.append((score, self._documents[document_id]))
            scored.sort(key=lambda item: item[0], reverse=True)
            hits: list[RagHit] = []
            for score, document in scored[: max(1, min(top_k, 10))]:
                snippet = make_snippet(document.text)
                hits.append(RagHit(document.id, document.title, snippet, round(score, 4), f"[{document.title}]", document.lesson_id, document.metadata or {}))
            return hits

    def count(self) -> int:
        return len(self._documents)


def default_documents() -> list[RagDocument]:
    documents: list[RagDocument] = []
    lesson_path = DATA / "lesson_content.json"
    if lesson_path.exists():
        payload = json.loads(lesson_path.read_text(encoding="utf-8"))
        for lesson in payload.get("lessons", []):
            text = " ".join(
                [
                    lesson.get("title", ""),
                    lesson.get("why_it_matters", ""),
                    lesson.get("intuition", ""),
                    lesson.get("formal_explanation", ""),
                    lesson.get("manual_example", ""),
                    " ".join(lesson.get("learning_objectives", [])),
                    " ".join(lesson.get("summary", [])),
                ]
            )
            documents.append(RagDocument(f"lesson-{lesson['lesson_id']}", lesson["title"], text, lesson["lesson_id"], "course"))
    terms_path = DATA / "terms.json"
    if terms_path.exists():
        for term in json.loads(terms_path.read_text(encoding="utf-8")):
            text = " ".join([term.get("approved_ru_term", ""), term.get("english_term", ""), term.get("short_definition", ""), term.get("extended_definition", ""), term.get("example", "")])
            documents.append(RagDocument(f"term-{term['approved_ru_term']}", term["approved_ru_term"], text, term.get("first_lesson_id"), "glossary"))
    return documents


INDEX = LocalRagIndex()
INDEX.index(default_documents())


def serialize_hit(hit: RagHit) -> dict[str, object]:
    return asdict(hit)


def answer_question(question: str, top_k: int = 4) -> dict[str, object]:
    hits = INDEX.search(question, top_k)
    if not hits:
        return {"answer": "В учебных материалах не найден подходящий фрагмент. Уточните вопрос или назовите урок.", "citations": [], "grounded": False}
    citations = [serialize_hit(hit) for hit in hits]
    lead = hits[0]
    answer = f"В материалах курса тема связана с уроком «{lead.title}». {lead.snippet}"
    if len(hits) > 1:
        answer += " Дополнительный контекст найден в: " + ", ".join(hit.citation for hit in hits[1:]) + "."
    return {"answer": answer, "citations": citations, "grounded": True}
