"""How clearly did the user say what they want?

Five dimensions, keyword-matched. Deterministic on purpose - it costs nothing,
runs in microseconds, and is testable without a model, which matters because
the score decides which of three workflows a request enters.

Event and outfit type carry double weight: the guardrail already treats that
pair as the blocking one, since a request missing both is not plannable however
much colour detail it carries.
"""

import re

from shopai.vocabulary import (
    ACCESSORY_TERMS,
    COLOR_TERMS,
    GARMENT_TERMS,
    OCCASION_TERMS,
    SILHOUETTE_TERMS,
)

DIMENSION_TERMS = {
    # OCCASION_TERMS, not EVENT_TERMS: vocabulary.py already defines an
    # occasion as "an event, or a vibe specific enough to dress for" (a
    # wedding, or "corporate chic"). Using EVENT_TERMS alone made a vibe-only
    # request invisible to this dimension - scored 0 and routed as if there
    # were no request at all, when there plainly was one.
    "event": OCCASION_TERMS,
    "outfit_type": GARMENT_TERMS,
    "colors": COLOR_TERMS,
    "silhouette": SILHOUETTE_TERMS,
    "accessories": ACCESSORY_TERMS,
}

DIMENSION_WEIGHTS = {
    "event": 2,
    "outfit_type": 2,
    "colors": 1,
    "silhouette": 1,
    "accessories": 1,
}

MAX_SCORE = sum(DIMENSION_WEIGHTS.values())  # 7

HIGH_THRESHOLD = 5
MEDIUM_THRESHOLD = 2


# A user who asks for results ("show me", "recommend", "help me choose") has
# told us they want a plan now. Patterns are stems and phrases, so a typo in
# the tail of a word ("recommnedation") still lands.
EXPLICIT_PATTERNS = [
    r"\bshow me\b",
    r"\bshow\b.*\b(?:recom\w*|options?|outfits?|looks?|picks?|ideas?)\b",
    r"\brecom\w*",
    r"\bsuggest\w*",
    r"\bgive me\b",
    r"\bfind me\b",
    r"\bwhat should i (?:wear|buy|get)\b",
    r"\bhelp me (?:choose|pick|decide|select|find)\b",
    r"\boptions\b",
    r"\bideas\b",
]

# The narrower ask: they want a pick made for them, not just a list.
CHOICE_PATTERNS = [
    r"\bhelp me (?:choose|pick|decide|select)\b",
    r"\bwhich (?:one|should)\b",
    r"\bbest (?:one|option|pick)\b",
    r"\bdecide\b",
]


def _words(text: str) -> set[str]:
    """Lower-cased words, each also under its singular so 'sundresses' and
    'anklets' meet the singular entries in the word lists."""
    words = set(re.findall(r"[a-z][a-z'-]*", text.lower()))
    for word in list(words):
        if word.endswith("es") and len(word) > 4:
            words.add(word[:-2])
        if word.endswith("s") and len(word) > 3:
            words.add(word[:-1])
    return words


# "cool" / "warm" are colour words only when they describe tones.
TEMPERATURE_TONES = re.compile(
    r"\b(?:cool|warm)(?:[ -]toned?|[ -]tones|[ -]shades?|[ -]colou?rs?|[ -]palette|[ -]undertones?)\b"
)


def _asks(patterns: list[str], text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def tier_for_score(score: int) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def asks_explicitly(text: str) -> bool:
    return _asks(EXPLICIT_PATTERNS, text)


def asks_for_choice(text: str) -> bool:
    return _asks(CHOICE_PATTERNS, text)


def score_request(text: str) -> dict:
    """Rate a request's clarity and say what it was rated on.

    The evidence matters as much as the tier: the clarification agent asks
    about `missing`, so a bare label would not be enough to act on.
    """
    words = _words(text)

    matched = {
        dimension: sorted(words & terms)
        for dimension, terms in DIMENSION_TERMS.items()
    }
    if TEMPERATURE_TONES.search(text.lower()):
        matched["colors"] = sorted(set(matched["colors"]) | {"warm/cool tones"})
    present = [d for d, hits in matched.items() if hits]
    missing = [d for d in DIMENSION_TERMS if d not in present]
    score = sum(DIMENSION_WEIGHTS[d] for d in present)

    tier = tier_for_score(score)

    # An explicit ask turns "medium" into a go-ahead, so someone who said
    # "show me options" is not made to answer another question first. It never
    # lifts "low": asking for results does not turn an empty request into one,
    # and the score itself stays as measured.
    explicit = asks_explicitly(text)
    promoted = explicit and tier == "medium"
    if promoted:
        tier = "high"

    return {
        "tier": tier,
        "score": score,
        "max_score": MAX_SCORE,
        "present": present,
        "missing": missing,
        "matched": {d: hits for d, hits in matched.items() if hits},
        "explicit_request": explicit,
        "promoted": promoted,
        "wants_choice": asks_for_choice(text),
    }
