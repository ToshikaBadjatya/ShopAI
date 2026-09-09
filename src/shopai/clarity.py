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


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z'-]*", text.lower()))


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
    present = [d for d, hits in matched.items() if hits]
    missing = [d for d in DIMENSION_TERMS if d not in present]
    score = sum(DIMENSION_WEIGHTS[d] for d in present)

    if score >= HIGH_THRESHOLD:
        tier = "high"
    elif score >= MEDIUM_THRESHOLD:
        tier = "medium"
    else:
        tier = "low"

    return {
        "tier": tier,
        "score": score,
        "max_score": MAX_SCORE,
        "present": present,
        "missing": missing,
        "matched": {d: hits for d, hits in matched.items() if hits},
    }
