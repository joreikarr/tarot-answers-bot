from __future__ import annotations

import json
from typing import Any

from tarot_answer_bot.tarot import TarotCard


def extract_question_prompt(message_text: str) -> str:
    return (
        "You are an assistant that extracts the main tarot question from a client message.\n"
        "Return only valid JSON with keys question, confidence, notes.\n"
        "Question should be short, in the same language as the message when possible.\n"
        f"Message:\n{message_text}\n"
    )


def facts_prompt(
    question: str,
    answer_text: str,
    current_context: str | None,
    additional_context: str | None,
    existing_facts: list[str],
) -> str:
    payload = {
        "question": question,
        "answer": answer_text,
        "current_context": current_context or "",
        "additional_context": additional_context or "",
        "existing_facts": existing_facts,
    }
    return (
        "Extract only stable client facts from the reading.\n"
        "Return valid JSON with keys facts (array of strings).\n"
        "Do not copy full texts or fleeting emotional reactions.\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def reading_prompt(
    question: str,
    cards: list[TarotCard],
    client_context: str | None,
    additional_context: str | None,
    important_facts: list[str],
) -> str:
    cards_payload = [
        {
            "name": card.name,
            "name_ru": card.name_ru,
            "arcana": card.arcana,
            "is_reversed": card.is_reversed,
        }
        for card in cards
    ]
    payload = {
        "question": question,
        "cards": cards_payload,
        "client_context": client_context or "",
        "additional_context": additional_context or "",
        "important_facts": important_facts,
    }
    return (
        "Generate a tarot reading in a warm, mystical style.\n"
        "Be practical, emotionally aware, and do not claim certainty.\n"
        "Return plain text, no markdown list required.\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def clean_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        stripped = stripped[start : end + 1]
    return stripped


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = clean_json_text(text)
    return json.loads(cleaned)
