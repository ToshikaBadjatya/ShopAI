import pytest

from shopai.clarity import score_request


@pytest.mark.parametrize("text,expected_tier", [
    ("black fitted midi dress for a cocktail party with gold jewellery", "high"),
    ("navy saree for my cousin's sangeet", "high"),
    ("wedding guest dress", "medium"),
    ("something nice for Diwali", "medium"),
    ("I want something in pastels", "low"),
    ("help me with my style", "low"),
    ("", "low"),
])
def test_tiers(text, expected_tier):
    assert score_request(text)["tier"] == expected_tier


def test_style_does_not_count_as_an_outfit_type():
    """The FASHION_TERMS trap: 'style' is a meta word, not a garment."""
    result = score_request("help me with my style")
    assert "outfit_type" in result["missing"]
    assert result["score"] == 0


def test_event_and_outfit_type_are_weighted_double():
    event_only = score_request("for a wedding")
    color_only = score_request("in navy")
    assert event_only["score"] == 2
    assert color_only["score"] == 1


def test_returns_evidence_not_just_a_label():
    """The clarification agent needs to know what's missing to ask about it."""
    result = score_request("wedding guest dress")
    assert set(result["present"]) == {"event", "outfit_type"}
    assert set(result["missing"]) == {"colors", "silhouette", "accessories"}
    assert "wedding" in result["matched"]["event"]


def test_a_full_request_scores_the_maximum():
    result = score_request(
        "black fitted midi dress for a cocktail party with gold jewellery"
    )
    assert result["score"] == 7
    assert result["missing"] == []
