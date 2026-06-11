from tarot_answer_bot.prompts import extract_json_object


def test_extract_json_object_handles_plain_json():
    data = extract_json_object('{"question":"Что дальше?","confidence":0.9,"notes":"ok"}')
    assert data["question"] == "Что дальше?"
    assert data["confidence"] == 0.9
