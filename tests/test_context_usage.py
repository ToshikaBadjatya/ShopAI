from shopai.llm import MODEL_TOKEN_LIMITS, calculate_context_usage


def test_estimates_four_characters_per_token():
    result = calculate_context_usage("x" * 4000, model="gpt-4o")
    assert result["tokens"] == 1000


def test_percent_is_relative_to_the_model_window():
    result = calculate_context_usage("x" * 4000, model="gpt-4o")
    assert result["max"] == MODEL_TOKEN_LIMITS["gpt-4o"]
    assert result["percent"] == round((1000 / 128000) * 100, 1)


def test_unknown_model_falls_back_to_128k():
    """MODEL is 'auto' in this project - a gateway picks per call."""
    result = calculate_context_usage("x" * 4000, model="auto")
    assert result["max"] == 128000


def test_empty_context_is_zero_percent():
    assert calculate_context_usage("")["percent"] == 0.0
