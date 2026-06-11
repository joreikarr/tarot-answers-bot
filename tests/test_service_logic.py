from tarot_answer_bot.llm import DummyLLM
from tarot_answer_bot.prompts import facts_prompt, reading_prompt
from tarot_answer_bot.tarot import draw_three_cards


def test_facts_prompt_contains_payload():
    text = facts_prompt("Q", "A", "ctx", "add", ["f1"])
    assert "existing_facts" in text


def test_reading_prompt_contains_cards():
    cards = draw_three_cards()
    text = reading_prompt("Q", cards, "ctx", "add", ["fact"])
    assert "important_facts" in text


def test_dummy_llm_generates_text():
    llm = DummyLLM()
    text = llm.generate_reading("Что дальше?", draw_three_cards(), None, None, [])
    assert "Что дальше?" in text
