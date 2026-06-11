from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tarot_answer_bot.llm import DummyLLM, GeminiClient, QuestionExtraction
from tarot_answer_bot.models import Client, ClientFact, Reading
from tarot_answer_bot.tarot import TarotCard, draw_three_cards, serialize_cards


@dataclass(slots=True)
class DraftReading:
    reading_id: int
    client_id: int | None
    original_message: str
    transcribed_text: str | None
    extracted_question: str | None = None
    question_notes: str | None = None
    additional_context: str | None = None
    selected_cards: list[TarotCard] | None = None
    llm_answer: str | None = None


class TarotBotService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm_client: GeminiClient | DummyLLM,
        allow_reversed_cards: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm_client
        self._allow_reversed_cards = allow_reversed_cards
        self.voice_transcriber = None

    async def upsert_client_from_telegram(
        self,
        telegram_user_id: int | None,
        display_name: str | None,
    ) -> Client | None:
        if telegram_user_id is None and not display_name:
            return None
        async with self._session_factory() as session:
            client = None
            if telegram_user_id is not None:
                client = await session.scalar(
                    select(Client).where(Client.telegram_user_id == telegram_user_id)
                )
            if client is None and display_name:
                client = await session.scalar(
                    select(Client).where(Client.display_name == display_name).limit(1)
                )
            if client is None:
                client = Client(
                    telegram_user_id=telegram_user_id,
                    display_name=display_name,
                )
                session.add(client)
                await session.commit()
                await session.refresh(client)
                return client
            if telegram_user_id is not None and client.telegram_user_id != telegram_user_id:
                client.telegram_user_id = telegram_user_id
            if display_name and not client.display_name:
                client.display_name = display_name
            await session.commit()
            await session.refresh(client)
            return client

    async def find_clients(self, query_text: str, limit: int = 5) -> list[Client]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Client)
                .where(
                    (Client.name.ilike(f"%{query_text}%"))
                    | (Client.display_name.ilike(f"%{query_text}%"))
                )
                .order_by(Client.updated_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_client(self, client_id: int) -> Client | None:
        async with self._session_factory() as session:
            return await session.get(Client, client_id)

    async def create_client(
        self,
        telegram_user_id: int | None,
        display_name: str | None,
        name: str,
        age: int | None,
        general_context: str | None,
    ) -> Client:
        async with self._session_factory() as session:
            client = Client(
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                name=name,
                age=age,
                general_context=general_context,
            )
            session.add(client)
            await session.commit()
            await session.refresh(client)
            return client

    async def update_client_context(
        self,
        client_id: int,
        name: str | None = None,
        age: int | None = None,
        general_context: str | None = None,
    ) -> Client:
        async with self._session_factory() as session:
            client = await session.get(Client, client_id)
            if client is None:
                raise LookupError(f"Client {client_id} not found")
            if name is not None:
                client.name = name
            if age is not None:
                client.age = age
            if general_context is not None:
                client.general_context = general_context
            await session.commit()
            await session.refresh(client)
            return client

    async def create_reading(
        self,
        client_id: int,
        original_message: str,
        transcribed_text: str | None,
    ) -> Reading:
        async with self._session_factory() as session:
            reading = Reading(
                client_id=client_id,
                original_message=original_message,
                transcribed_text=transcribed_text,
            )
            session.add(reading)
            await session.commit()
            await session.refresh(reading)
            return reading

    async def update_reading(
        self,
        reading_id: int,
        *,
        question: str | None = None,
        question_notes: str | None = None,
        additional_context: str | None = None,
        selected_cards: list[TarotCard] | None = None,
        llm_answer: str | None = None,
    ) -> Reading:
        async with self._session_factory() as session:
            reading = await session.get(Reading, reading_id)
            if reading is None:
                raise LookupError(f"Reading {reading_id} not found")
            if question is not None:
                reading.extracted_question = question
            if question_notes is not None:
                reading.question_notes = question_notes
            if additional_context is not None:
                reading.additional_context = additional_context
            if selected_cards is not None:
                reading.selected_cards_json = json.dumps(
                    serialize_cards(selected_cards),
                    ensure_ascii=False,
                )
            if llm_answer is not None:
                reading.llm_answer = llm_answer
            await session.commit()
            await session.refresh(reading)
            return reading

    async def get_reading(self, reading_id: int) -> Reading | None:
        async with self._session_factory() as session:
            return await session.get(Reading, reading_id)

    async def get_recent_facts(self, client_id: int, limit: int = 20) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ClientFact.fact_text)
                .where(ClientFact.client_id == client_id)
                .order_by(ClientFact.created_at.desc())
                .limit(limit)
            )
            return [row[0] for row in result.all()]

    async def add_facts(
        self, client_id: int, facts: Iterable[str], source_reading_id: int | None
    ) -> list[ClientFact]:
        normalized = []
        seen = set()
        for fact in facts:
            item = " ".join(str(fact).split()).strip()
            if not item or item.lower() in seen:
                continue
            seen.add(item.lower())
            normalized.append(item)
        if not normalized:
            return []
        async with self._session_factory() as session:
            existing = await session.execute(
                select(ClientFact.fact_text).where(ClientFact.client_id == client_id)
            )
            existing_set = {row[0].strip().lower() for row in existing.all()}
            created = []
            for fact_text in normalized:
                if fact_text.lower() in existing_set:
                    continue
                fact = ClientFact(
                    client_id=client_id,
                    fact_text=fact_text,
                    source_reading_id=source_reading_id,
                )
                session.add(fact)
                created.append(fact)
            await session.commit()
            for fact in created:
                await session.refresh(fact)
            return created

    async def generate_reading(
        self,
        client_id: int,
        question: str,
        additional_context: str | None = None,
    ) -> tuple[list[TarotCard], str]:
        client = await self.get_client(client_id)
        if client is None:
            raise LookupError(f"Client {client_id} not found")
        facts = await self.get_recent_facts(client_id)
        cards = draw_three_cards(allow_reversed=self._allow_reversed_cards)
        answer = self._llm.generate_reading(
            question=question,
            cards=cards,
            client_context=client.general_context,
            additional_context=additional_context,
            important_facts=facts,
        )
        return cards, answer

    async def update_context_from_reading(self, reading_id: int) -> list[str]:
        reading = await self.get_reading(reading_id)
        if reading is None or reading.llm_answer is None or reading.extracted_question is None:
            return []
        client = await self.get_client(reading.client_id)
        if client is None:
            return []
        facts = self._llm.extract_facts(
            question=reading.extracted_question,
            answer_text=reading.llm_answer,
            current_context=client.general_context,
            additional_context=reading.additional_context,
            existing_facts=await self.get_recent_facts(client.id),
        )
        created = await self.add_facts(client.id, facts.facts, reading.id)
        return [fact.fact_text for fact in created]

    async def extract_question(self, message_text: str) -> QuestionExtraction:
        return self._llm.extract_question(message_text)
