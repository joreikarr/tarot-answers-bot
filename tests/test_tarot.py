from random import Random

from tarot_answer_bot.tarot import build_deck, draw_three_cards, serialize_cards


def test_deck_has_78_cards():
    deck = build_deck()
    assert len(deck) == 78


def test_draw_three_cards_are_unique():
    cards = draw_three_cards(rng=Random(1))
    assert len(cards) == 3
    assert len({card.name for card in cards}) == 3


def test_serialize_cards_matches_shape():
    cards = draw_three_cards(rng=Random(2))
    payload = serialize_cards(cards)
    assert len(payload) == 3
    assert set(payload[0]) == {"name", "name_ru", "arcana", "is_reversed"}
