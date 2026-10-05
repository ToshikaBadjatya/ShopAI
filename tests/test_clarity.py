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


def test_a_vibe_with_no_named_event_still_counts_as_an_occasion():
    """Regression: 'plan an outfit . Vibe: Corporate Chic' scored 0 (Low) and
    got routed as if there were no request at all, because the event
    dimension checked EVENT_TERMS only - vibes like 'corporate' and 'chic'
    live in a separate set and were invisible to it."""
    result = score_request("plan an outfit . Vibe: Corporate Chic")
    assert "event" in result["present"]
    assert result["tier"] != "low"


# ---------------------------------------------------------------------------
# Wider vocabulary: seasons, airy fits and soft colours name something real.
# ---------------------------------------------------------------------------

BREEZY_PASTEL = (
    "A breezy summer outfit with light pastel tones. "
    "Show recommendation and help me choose"
)


@pytest.mark.parametrize("word,dimension", [
    ("summer", "event"),
    ("breezy", "silhouette"),
    ("sundress", "outfit_type"),
    ("romper", "outfit_type"),
    ("shorts", "outfit_type"),
    ("sunhat", "accessories"),
    ("anklet", "accessories"),
    ("champagne", "colors"),
    ("sage", "colors"),
])
def test_new_vocabulary_is_recognised(word, dimension):
    assert dimension in score_request(f"something {word}")["present"]


def test_plural_forms_match_their_singular_terms():
    assert "outfit_type" in score_request("two sundresses")["present"]
    assert "accessories" in score_request("some anklets")["present"]


def test_the_breezy_pastel_request_is_no_longer_low():
    result = score_request(BREEZY_PASTEL)
    assert {"event", "silhouette", "colors"} <= set(result["present"])
    assert result["tier"] != "low"


# ---------------------------------------------------------------------------
# Explicit requests: a user who asks for results should get them.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "show me recommendations",
    "please recommend something",
    "suggest a few options",
    "give me some ideas",
    "find me an outfit",
    "what should I wear",
    "help me choose",
    "help me pick between them",
    "Show recommnedation and help me choose",  # typo-tolerant on the stem
])
def test_explicit_requests_are_detected(text):
    assert score_request(text)["explicit_request"] is True


@pytest.mark.parametrize("text", [
    "wedding guest dress",
    "I want something in pastels",
    "help me with my style",
    "",
])
def test_plain_descriptions_are_not_explicit(text):
    assert score_request(text)["explicit_request"] is False


def test_explicit_ask_promotes_medium_to_high():
    plain = score_request("wedding guest dress")
    asked = score_request("wedding guest dress, show me options")
    assert plain["tier"] == "medium"
    assert asked["tier"] == "high"
    assert asked["promoted"] is True
    assert asked["score"] == plain["score"]  # the score stays honest


def test_explicit_ask_cannot_invent_a_request_from_nothing():
    """Asking for results does not turn an empty or near-empty request into a plan."""
    assert score_request("show me recommendations")["tier"] == "low"
    assert score_request("recommend something in pastels")["tier"] == "low"


def test_a_high_score_is_not_marked_promoted():
    result = score_request(
        "black fitted midi dress for a cocktail party, show me options"
    )
    assert result["tier"] == "high"
    assert result["promoted"] is False


def test_breezy_pastel_request_goes_straight_to_a_plan():
    result = score_request(BREEZY_PASTEL)
    assert result["explicit_request"] is True
    assert result["tier"] == "high"


def test_wants_choice_is_flagged_separately():
    assert score_request(BREEZY_PASTEL)["wants_choice"] is True
    assert score_request("show me options for a wedding dress")["wants_choice"] is False


# ---------------------------------------------------------------------------
# "cool" and "warm" name a colour only when they describe tones.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Want a cool outfit",
    "something warm and cool looking",
    "a cool dress",
])
def test_slang_cool_is_not_a_colour(text):
    assert "colors" not in score_request(text)["present"]


@pytest.mark.parametrize("text", [
    "cool tones please",
    "something in warm shades",
    "a cool-toned palette",
    "warm colours for autumn",
])
def test_cool_and_warm_count_when_describing_tones(text):
    assert "colors" in score_request(text)["present"]


from shopai.clarity import asks_explicitly, asks_for_choice, tier_for_score


@pytest.mark.parametrize("score,tier", [(0, "low"), (1, "low"), (2, "medium"), (4, "medium"), (5, "high"), (7, "high")])
def test_tier_for_score(score, tier):
    assert tier_for_score(score) == tier


def test_public_ask_helpers_match_score_request():
    assert asks_explicitly("show me options") is True
    assert asks_explicitly("wedding guest dress") is False
    assert asks_for_choice("help me choose") is True
    assert asks_for_choice("show me options") is False
