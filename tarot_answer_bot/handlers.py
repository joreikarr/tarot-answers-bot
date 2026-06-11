from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tarot_answer_bot.keyboards import (
    client_missing_keyboard,
    client_choices_keyboard,
    post_reading_keyboard,
    question_confirmation_keyboard,
)
from tarot_answer_bot.services import TarotBotService
from tarot_answer_bot.states import TarotFlow


router = Router()


def _message_text(message: Message) -> str:
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    return ""


def _client_label(client) -> str:
    parts = [str(client.id)]
    if client.name:
        parts.append(client.name)
    elif client.display_name:
        parts.append(client.display_name)
    return " | ".join(parts)


async def _transcribe_voice(message: Message, service: TarotBotService) -> str:
    transcriber = getattr(service, "voice_transcriber", None)
    if transcriber is None:
        raise RuntimeError("Voice transcription is not configured")
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await message.bot.download(message.voice, destination=tmp_path)
        return transcriber.transcribe(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TarotFlow.waiting_for_message)
    await message.answer(
        "Отправь мне текст или голос клиента, "
        "и я вытащу вопрос, как будто у меня есть мозг и доступ к Gemini."
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TarotFlow.waiting_for_message)
    await message.answer("Процесс сброшен. Можешь прислать новое сообщение.")


async def _extract_client_reference(message: Message, service: TarotBotService):
    forward_origin = getattr(message, "forward_origin", None)
    telegram_user_id = None
    display_name = None
    if forward_origin and getattr(forward_origin, "user", None):
        user = forward_origin.user
        telegram_user_id = user.id
        display_name = " ".join(filter(None, [user.first_name, user.last_name])) or user.username
    client = await service.upsert_client_from_telegram(telegram_user_id, display_name)
    return client


@router.message(StateFilter(TarotFlow.waiting_for_message), F.text | F.voice)
async def intake_message(message: Message, state: FSMContext, service: TarotBotService) -> None:
    source_text = _message_text(message)
    transcribed_text = None
    if message.voice:
        transcribed_text = await _transcribe_voice(message, service)
        source_text = transcribed_text
    client = await _extract_client_reference(message, service)
    if client is None:
        await state.update_data(
            source_text=_message_text(message),
            transcribed_text=transcribed_text,
        )
        await state.set_state(TarotFlow.waiting_for_client_choice)
        await message.answer("Кто заказчик?", reply_markup=client_missing_keyboard())
        return

    reading = await service.create_reading(
        client_id=client.id,
        original_message=_message_text(message),
        transcribed_text=transcribed_text,
    )
    extraction = await service.extract_question(source_text)
    await service.update_reading(
        reading.id,
        question=extraction.question,
        question_notes=extraction.notes,
    )
    await state.update_data(
        reading_id=reading.id,
        client_id=client.id,
        source_text=source_text,
        transcribed_text=transcribed_text,
        extracted_question=extraction.question,
        question_notes=extraction.notes,
    )
    await state.set_state(TarotFlow.waiting_for_question_confirmation)
    await message.answer(
        f"Я выделил вопрос: {extraction.question}\nВсё верно?",
        reply_markup=question_confirmation_keyboard(),
    )


@router.callback_query(F.data == "question:retry")
async def retry_question(
    callback: CallbackQuery,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    source_text = data.get("source_text", "")
    extraction = await service.extract_question(source_text)
    await state.update_data(extracted_question=extraction.question, question_notes=extraction.notes)
    reading_id = data.get("reading_id")
    if reading_id:
        await service.update_reading(
            reading_id,
            question=extraction.question,
            question_notes=extraction.notes,
        )
    await callback.message.answer(
        f"Я снова выделил: {extraction.question}\nВсё верно?"
    )
    await callback.answer()


@router.callback_query(F.data == "question:edit")
async def edit_question(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TarotFlow.waiting_for_question_edit)
    await callback.message.answer("Отправь исправленный вопрос одним сообщением.")
    await callback.answer()


@router.message(StateFilter(TarotFlow.waiting_for_question_edit), F.text)
async def accept_question_edit(
    message: Message,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    reading_id = data.get("reading_id")
    question = message.text.strip()
    if reading_id:
        await service.update_reading(reading_id, question=question)
    await state.update_data(extracted_question=question)
    await state.set_state(TarotFlow.waiting_for_question_confirmation)
    await message.answer(
        f"Принял. Теперь вопрос: {question}\nВсё верно?",
        reply_markup=question_confirmation_keyboard(),
    )


@router.callback_query(F.data == "question:add_context")
async def ask_for_context(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TarotFlow.waiting_for_additional_context)
    await callback.message.answer(
        "Отправь дополнительный контекст к этому вопросу одним сообщением."
    )
    await callback.answer()


@router.message(StateFilter(TarotFlow.waiting_for_additional_context), F.text | F.voice)
async def capture_additional_context(
    message: Message,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    context_text = message.text or message.caption or ""
    if message.voice:
        context_text = await _transcribe_voice(message, service)
    reading_id = data.get("reading_id")
    if reading_id:
        await service.update_reading(reading_id, additional_context=context_text)
    await state.update_data(additional_context=context_text)
    await state.set_state(TarotFlow.waiting_for_question_confirmation)
    await message.answer(
        "Контекст сохранён. Подтверди вопрос ещё раз или "
        "продолжим после подтверждения."
    )


@router.callback_query(F.data == "question:confirm")
async def confirm_question(
    callback: CallbackQuery,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    client_id = data.get("client_id")
    reading_id = data.get("reading_id")
    question = data.get("extracted_question")
    if client_id is None or reading_id is None or not question:
        await callback.answer("Нет активного черновика", show_alert=True)
        return
    client = await service.get_client(client_id)
    if client is None:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    if client.name is None or client.age is None or client.general_context is None:
        await state.set_state(TarotFlow.waiting_for_new_client_name)
        await callback.message.answer("Создаём нового клиента. Как его зовут?")
        await callback.answer()
        return
    await _generate_reading(callback.message, state, service)
    await callback.answer()


@router.callback_query(F.data == "client:choose")
async def choose_existing_client(
    callback: CallbackQuery,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    source_text = data.get("source_text", "")
    clients = await service.find_clients(source_text)
    if not clients:
        await callback.message.answer("Пока нет подходящих клиентов. Создай нового.")
        await callback.answer()
        return
    await state.set_state(TarotFlow.waiting_for_client_choice)
    await state.update_data(client_candidates=[client.id for client in clients])
    await callback.message.answer(
        "Выбери клиента:",
        reply_markup=client_choices_keyboard(clients),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("client:pick:"))
async def resolve_client_choice(
    callback: CallbackQuery,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    client_ids = data.get("client_candidates") or []
    client_id = int(callback.data.rsplit(":", 1)[-1])
    if client_id not in client_ids:
        await callback.answer("Такого клиента нет в списке", show_alert=True)
        return
    reading_source = data.get("source_text", "")
    reading = await service.create_reading(
        client_id=client_id,
        original_message=reading_source,
        transcribed_text=data.get("transcribed_text"),
    )
    extraction = await service.extract_question(reading_source)
    await service.update_reading(
        reading.id,
        question=extraction.question,
        question_notes=extraction.notes,
    )
    await state.update_data(
        reading_id=reading.id,
        client_id=client_id,
        extracted_question=extraction.question,
    )
    await state.set_state(TarotFlow.waiting_for_question_confirmation)
    await callback.message.answer(
        f"Я выделил вопрос: {extraction.question}\nВсё верно?",
        reply_markup=question_confirmation_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "client:new")
async def create_new_client(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TarotFlow.waiting_for_new_client_name)
    await callback.message.answer("Как зовут клиента?")
    await callback.answer()


@router.message(StateFilter(TarotFlow.waiting_for_new_client_name), F.text)
async def capture_new_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data(new_client_name=message.text.strip())
    await state.set_state(TarotFlow.waiting_for_new_client_age)
    await message.answer("Сколько лет клиенту?")


@router.message(StateFilter(TarotFlow.waiting_for_new_client_age), F.text)
async def capture_new_client_age(message: Message, state: FSMContext) -> None:
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("Нужен возраст числом.")
        return
    await state.update_data(new_client_age=age)
    await state.set_state(TarotFlow.waiting_for_new_client_context)
    await message.answer("Дай общий контекст клиента одним сообщением.")


@router.message(StateFilter(TarotFlow.waiting_for_new_client_context), F.text | F.voice)
async def capture_new_client_context(
    message: Message,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    context_text = message.text or message.caption or ""
    if message.voice:
        context_text = await _transcribe_voice(message, service)
    client = await service.create_client(
        telegram_user_id=None,
        display_name=None,
        name=data.get("new_client_name", ""),
        age=data.get("new_client_age"),
        general_context=context_text,
    )
    reading = await service.create_reading(
        client_id=client.id,
        original_message=data.get("source_text", ""),
        transcribed_text=data.get("transcribed_text"),
    )
    extraction = await service.extract_question(data.get("source_text", ""))
    await service.update_reading(
        reading.id,
        question=extraction.question,
        question_notes=extraction.notes,
    )
    await state.update_data(
        reading_id=reading.id,
        client_id=client.id,
        extracted_question=extraction.question,
    )
    await state.set_state(TarotFlow.waiting_for_question_confirmation)
    await message.answer(
        f"Я выделил вопрос: {extraction.question}\nВсё верно?",
        reply_markup=question_confirmation_keyboard(),
    )


async def _generate_reading(
    message: Message | None,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    data = await state.get_data()
    reading_id = data.get("reading_id")
    client_id = data.get("client_id")
    question = data.get("extracted_question")
    additional_context = data.get("additional_context")
    if reading_id is None or client_id is None or not question:
        if message:
            await message.answer("Не хватает данных для гадания.")
        return
    await state.set_state(TarotFlow.generating_reading)
    cards, answer = await service.generate_reading(client_id, question, additional_context)
    await service.update_reading(
        reading_id,
        additional_context=additional_context,
        selected_cards=cards,
        llm_answer=answer,
    )
    await state.update_data(
        selected_cards=json.dumps([card.name for card in cards], ensure_ascii=False),
        llm_answer=answer,
    )
    await state.set_state(TarotFlow.waiting_after_generation)
    if message:
        await message.answer(answer, reply_markup=post_reading_keyboard())


@router.callback_query(F.data == "reading:regenerate")
async def regenerate_reading(
    callback: CallbackQuery,
    state: FSMContext,
    service: TarotBotService,
) -> None:
    await _generate_reading(callback.message, state, service)
    await callback.answer()


@router.callback_query(F.data == "reading:add_fact")
async def add_facts(callback: CallbackQuery, state: FSMContext, service: TarotBotService) -> None:
    data = await state.get_data()
    reading_id = data.get("reading_id")
    if reading_id is None:
        await callback.answer("Нет гадания", show_alert=True)
        return
    facts = await service.update_context_from_reading(reading_id)
    if not facts:
        await callback.message.answer("Новых устойчивых фактов не нашёл.")
    else:
        await callback.message.answer(
            "Контекст обновлён:\n" + "\n".join(f"- {fact}" for fact in facts)
        )
    await callback.answer()


@router.callback_query(F.data == "reading:finish")
async def finish_reading(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TarotFlow.waiting_for_message)
    await callback.message.answer("Гадание завершено. Жду новое сообщение.")
    await callback.answer()


@router.callback_query(F.data == "reading:copy")
async def copy_reading(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    answer = data.get("llm_answer")
    if not answer:
        await callback.answer("Нет текста ответа", show_alert=True)
        return
    try:
        await callback.message.answer(answer)
    except TelegramBadRequest:
        await callback.message.answer("Не смог отправить текст, но он есть в боте.")
    await callback.answer()
