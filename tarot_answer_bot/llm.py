from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tarot_answer_bot.prompts import (
    extract_json_object,
    extract_question_prompt,
    facts_prompt,
    reading_prompt,
)
from tarot_answer_bot.tarot import TarotCard

try:
    from google import genai
except Exception:  # pragma: no cover - import fallback for environments without the package
    genai = None


@dataclass(slots=True)
class QuestionExtraction:
    question: str
    confidence: float
    notes: str | None = None


@dataclass(slots=True)
class FactsExtraction:
    facts: list[str]


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        if genai is None:
            raise RuntimeError("google-genai package is not installed")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def _generate_text(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text:
            return text
        parts = getattr(response, "candidates", [])
        if parts:
            candidate = parts[0]
            content = getattr(candidate, "content", None)
            if content and getattr(content, "parts", None):
                return "".join(part.text or "" for part in content.parts)
        raise RuntimeError("Gemini response did not contain text")

    def extract_question(self, message_text: str) -> QuestionExtraction:
        raw = self._generate_text(extract_question_prompt(message_text))
        data = extract_json_object(raw)
        return QuestionExtraction(
            question=str(data.get("question", "")).strip(),
            confidence=float(data.get("confidence", 0.0)),
            notes=(str(data["notes"]).strip() if data.get("notes") else None),
        )

    def extract_facts(
        self,
        question: str,
        answer_text: str,
        current_context: str | None,
        additional_context: str | None,
        existing_facts: list[str],
    ) -> FactsExtraction:
        raw = self._generate_text(
            facts_prompt(question, answer_text, current_context, additional_context, existing_facts)
        )
        data = extract_json_object(raw)
        facts = [str(item).strip() for item in data.get("facts", []) if str(item).strip()]
        return FactsExtraction(facts=facts)

    def generate_reading(
        self,
        question: str,
        cards: list[TarotCard],
        client_context: str | None,
        additional_context: str | None,
        important_facts: list[str],
    ) -> str:
        return self._generate_text(
            reading_prompt(question, cards, client_context, additional_context, important_facts)
        )


class DummyLLM:
    def extract_question(self, message_text: str) -> QuestionExtraction:
        question = message_text.strip()
        if "?" not in question:
            question = question.splitlines()[0].strip()
        return QuestionExtraction(question=question, confidence=0.5, notes="fallback")

    def extract_facts(
        self,
        question: str,
        answer_text: str,
        current_context: str | None,
        additional_context: str | None,
        existing_facts: list[str],
    ) -> FactsExtraction:
        del question, answer_text, current_context, additional_context, existing_facts
        return FactsExtraction(facts=[])

    def generate_reading(
        self,
        question: str,
        cards: list[TarotCard],
        client_context: str | None,
        additional_context: str | None,
        important_facts: list[str],
    ) -> str:
        card_names = ", ".join(card.name_ru for card in cards)
        context_bits = [bit for bit in [client_context, additional_context] if bit]
        facts_bits = "; ".join(important_facts)
        return (
            f"Вопрос: {question}\n"
            f"Карты: {card_names}\n"
            f"Контекст: {' | '.join(context_bits) if context_bits else 'нет'}\n"
            f"Факты: {facts_bits or 'нет'}\n"
            "Ответ: путь не закрыт, но потребует честного разговора и терпения."
        )
