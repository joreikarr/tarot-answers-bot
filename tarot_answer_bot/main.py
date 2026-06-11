from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tarot_answer_bot.config import get_settings
from tarot_answer_bot.db import create_session_factory, init_db
from tarot_answer_bot.handlers import router
from tarot_answer_bot.llm import DummyLLM, GeminiClient
from tarot_answer_bot.services import TarotBotService
from tarot_answer_bot.voice import VoiceTranscriber


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    await init_db(settings.database_url)

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    session_factory = create_session_factory(settings.database_url)
    try:
        llm_client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    except Exception:
        llm_client = DummyLLM()

    service = TarotBotService(
        session_factory=session_factory,
        llm_client=llm_client,
        allow_reversed_cards=settings.allow_reversed_cards,
    )
    service.voice_transcriber = VoiceTranscriber(settings.voice_model_size)

    await dp.start_polling(bot, service=service)


if __name__ == "__main__":
    asyncio.run(main())
