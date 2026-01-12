from sakhi.apps.api.services.reflection_inquiry.answerer import validate_answer


def test_validate_answer_rejects_banned_terms_and_long_sentences():
    text = (
        "Good question. "
        "I mentioned this because it suggests an underlying distribution across days with alignment to evenings. "
        "As a result, you should act soon."
    )
    result = validate_answer(text)
    assert result["passed"] is False
    assert any("banned vocabulary" in reason for reason in result["fail_reasons"])


def test_validate_answer_allows_plain_friend_tone():
    text = (
        "Thanks for asking. "
        "I mentioned it because it showed up on more than one day, mostly at night. "
        "You can decide what to do with that."
    )
    result = validate_answer(text)
    assert result["passed"] is True
