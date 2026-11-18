"""Provider-neutral AI tutor with a deterministic demo provider."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

import httpx

from .rag import answer_question


@dataclass(frozen=True)
class TutorRequest:
    question: str
    attempt: str = ""
    lesson_id: str | None = None
    hint_level: int = 1


class TutorProvider(Protocol):
    name: str

    def answer(self, request: TutorRequest) -> dict[str, object]: ...


class DemoTutorProvider:
    name = "demo"

    def answer(self, request: TutorRequest) -> dict[str, object]:
        retrieval = answer_question(request.question, 3)
        citations = retrieval["citations"]
        if not request.attempt.strip():
            text = "Сначала напишите свою попытку в двух-трёх предложениях. Что вы уже проверили и где именно возникло затруднение?"
            mode = "leading_question"
        elif request.hint_level <= 1:
            text = "Сравните условие задачи с определением из урока. Какой вход, какой ожидаемый выход и какой признак ошибки вы можете назвать?"
            mode = "hint"
        else:
            text = "Разберите ответ по шагам и проверьте форму данных, знак градиента или выбранную метрику. Готовое решение не показываю, пока не проверена ваша попытка."
            mode = "remediation"
        return {"provider": self.name, "mode": mode, "answer": text, "citations": citations, "grounded": bool(retrieval["grounded"]), "prompt_version": "demo-tutor-v1"}


class OpenAICompatibleTutorProvider:
    name = "openai_compatible"

    def answer(self, request: TutorRequest) -> dict[str, object]:
        retrieval = answer_question(request.question, 4)
        citations = retrieval["citations"]
        api_key = os.getenv("AI_API_KEY", "")
        if not api_key:
            return DemoTutorProvider().answer(request)
        base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("AI_MODEL", "gpt-4o-mini")
        context = "\n".join(f"{item['citation']} {item['snippet']}" for item in citations)
        system = "Ты AI-тьютор курса. Сначала учитывай попытку ученика, давай наводящую подсказку, цитируй контекст и не выдавай готовое решение без попытки. Отвечай на русском языке."
        user = f"Вопрос: {request.question}\nПопытка ученика: {request.attempt or 'нет'}\nКонтекст курса:\n{context}"
        try:
            response = httpx.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json={"model": model, "temperature": 0.2, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=20)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return {"provider": self.name, "mode": "provider", "answer": content, "citations": citations, "grounded": bool(retrieval["grounded"]), "prompt_version": "provider-tutor-v1"}
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            return DemoTutorProvider().answer(request)


PROVIDERS: dict[str, TutorProvider] = {"demo": DemoTutorProvider(), "openai_compatible": OpenAICompatibleTutorProvider()}


def ask_tutor(request: TutorRequest, provider_name: str = "demo") -> dict[str, object]:
    provider = PROVIDERS.get(provider_name, PROVIDERS["demo"])
    return provider.answer(request)
