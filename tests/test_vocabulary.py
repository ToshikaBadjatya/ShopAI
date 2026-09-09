from shopai.vocabulary import (
    ACCESSORY_TERMS,
    COLOR_TERMS,
    EVENT_TERMS,
    FASHION_TERMS,
    GARMENT_TERMS,
    OCCASION_TERMS,
    SILHOUETTE_TERMS,
)


def test_garment_terms_are_actual_pieces():
    assert {"dress", "saree", "blazer", "jeans", "heels"} <= GARMENT_TERMS


def test_garment_terms_exclude_meta_shopping_words():
    """The trap this split exists for: 'help me with my style' must not read
    as an outfit type."""
    for meta in ("style", "styling", "fashion", "wardrobe", "shop", "budget", "price"):
        assert meta not in GARMENT_TERMS


def test_generic_containers_are_not_garments():
    """'I need an outfit' names no outfit type."""
    assert "outfit" not in GARMENT_TERMS
    assert "look" not in GARMENT_TERMS


def test_accessory_terms_cover_the_usual_suspects():
    assert {"bag", "clutch", "jewellery", "watch", "belt", "scarf"} <= ACCESSORY_TERMS


def test_fashion_terms_remains_a_superset():
    """Relevance detection still needs the broad set."""
    assert GARMENT_TERMS <= FASHION_TERMS
    assert ACCESSORY_TERMS <= FASHION_TERMS
    assert COLOR_TERMS <= FASHION_TERMS
    assert SILHOUETTE_TERMS <= FASHION_TERMS
    assert "style" in FASHION_TERMS


def test_occasion_terms_still_built_from_events_and_vibes():
    assert EVENT_TERMS <= OCCASION_TERMS
    assert "office" in OCCASION_TERMS
