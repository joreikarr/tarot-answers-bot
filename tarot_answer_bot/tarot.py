from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True, slots=True)
class TarotCard:
    name: str
    name_ru: str
    arcana: str
    is_reversed: bool = False


MAJOR_ARCANA = [
    ("The Fool", "Шут"),
    ("The Magician", "Маг"),
    ("The High Priestess", "Верховная Жрица"),
    ("The Empress", "Императрица"),
    ("The Emperor", "Император"),
    ("The Hierophant", "Иерофант"),
    ("The Lovers", "Влюблённые"),
    ("The Chariot", "Колесница"),
    ("Strength", "Сила"),
    ("The Hermit", "Отшельник"),
    ("Wheel of Fortune", "Колесо Фортуны"),
    ("Justice", "Справедливость"),
    ("The Hanged Man", "Повешенный"),
    ("Death", "Смерть"),
    ("Temperance", "Умеренность"),
    ("The Devil", "Дьявол"),
    ("The Tower", "Башня"),
    ("The Star", "Звезда"),
    ("The Moon", "Луна"),
    ("The Sun", "Солнце"),
    ("Judgement", "Суд"),
    ("The World", "Мир"),
]

SUITS = [
    ("Wands", "Жезлы"),
    ("Cups", "Кубки"),
    ("Swords", "Мечи"),
    ("Pentacles", "Пентакли"),
]

RANKS = [
    ("Ace", "Туз"),
    ("Two", "Двойка"),
    ("Three", "Тройка"),
    ("Four", "Четвёрка"),
    ("Five", "Пятёрка"),
    ("Six", "Шестёрка"),
    ("Seven", "Семёрка"),
    ("Eight", "Восьмёрка"),
    ("Nine", "Девятка"),
    ("Ten", "Десятка"),
    ("Page", "Паж"),
    ("Knight", "Рыцарь"),
    ("Queen", "Королева"),
    ("King", "Король"),
]


def build_deck(allow_reversed: bool = False) -> list[TarotCard]:
    deck: list[TarotCard] = [
        TarotCard(name=name, name_ru=name_ru, arcana="major") for name, name_ru in MAJOR_ARCANA
    ]
    for suit_name, suit_name_ru in SUITS:
        for rank_name, rank_name_ru in RANKS:
            deck.append(
                TarotCard(
                    name=f"{rank_name} of {suit_name}",
                    name_ru=f"{rank_name_ru} {suit_name_ru}",
                    arcana="minor",
                )
            )
    if allow_reversed:
        return [TarotCard(card.name, card.name_ru, card.arcana, is_reversed=False) for card in deck]
    return deck


def draw_three_cards(
    allow_reversed: bool = False, rng: Random | None = None
) -> list[TarotCard]:
    deck = build_deck(allow_reversed=allow_reversed)
    generator = rng or Random()
    drawn = generator.sample(deck, 3)
    if allow_reversed:
        return [
            TarotCard(
                card.name,
                card.name_ru,
                card.arcana,
                is_reversed=generator.choice([True, False]),
            )
            for card in drawn
        ]
    return drawn


def serialize_cards(cards: list[TarotCard]) -> list[dict[str, object]]:
    return [
        {
            "name": card.name,
            "name_ru": card.name_ru,
            "arcana": card.arcana,
            "is_reversed": card.is_reversed,
        }
        for card in cards
    ]
