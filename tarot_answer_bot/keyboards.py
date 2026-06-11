from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def question_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, верно", callback_data="question:confirm"),
                InlineKeyboardButton(
                    text="Повторить извлечение", callback_data="question:retry"
                ),
            ],
            [
                InlineKeyboardButton(text="Исправить вручную", callback_data="question:edit"),
                InlineKeyboardButton(
                    text="Добавить контекст", callback_data="question:add_context"
                ),
            ],
        ]
    )


def client_missing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Выбрать существующего", callback_data="client:choose"),
                InlineKeyboardButton(text="Создать нового", callback_data="client:new"),
            ]
        ]
    )


def client_choices_keyboard(clients) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{client.id}. {client.name or client.display_name or 'Без имени'}",
                callback_data=f"client:pick:{client.id}",
            )
        ]
        for client in clients
    ]
    rows.append([InlineKeyboardButton(text="Создать нового", callback_data="client:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_reading_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Скопировать/получить текст", callback_data="reading:copy"
                ),
                InlineKeyboardButton(
                    text="Перегенерировать ответ", callback_data="reading:regenerate"
                ),
            ],
            [
                InlineKeyboardButton(text="Завершить", callback_data="reading:finish"),
                InlineKeyboardButton(
                    text="Добавить факт в контекст", callback_data="reading:add_fact"
                ),
            ],
        ]
    )
