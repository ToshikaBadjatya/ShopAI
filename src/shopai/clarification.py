"""Verify the Styling Clarifier's findings before anything routes on them.

The agent reads the shopper's words and says which of five categories they
stated. It is trusted for judgement (is "breezy" a silhouette?) but not for
facts: a category counts only when the agent's quoted evidence appears in the
shopper's own words, and the tier is computed here from the verified findings.
No CrewAI import, so this tests without a model.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from shopai.clarity import (
    DIMENSION_WEIGHTS,
    MAX_SCORE,
    asks_explicitly,
    asks_for_choice,
    tier_for_score,
)

Category = Literal["event", "outfit_type", "colors", "silhouette", "accessories"]

# Heaviest first, so the fallback question closes the biggest gap.
GAP_ORDER = sorted(DIMENSION_WEIGHTS, key=lambda d: -DIMENSION_WEIGHTS[d])

QUESTION_FOR_GAP = {
    "event": "What's the occasion?",
    "outfit_type": "What kind of pieces are you after?",
    "colors": "Any colours you love, or want to avoid?",
    "silhouette": "How do you like it to fit - relaxed, fitted, flowy?",
    "accessories": "Want accessories to go with it?",
}


class CategoryFinding(BaseModel):
    category: Category
    status: Literal["stated", "missing"]
    value: str = Field("", description="What the shopper chose, in a word or two.")
    evidence: str = Field("", description="The shopper's own words, copied exactly, that show it.")


class ClarificationAssessment(BaseModel):
    findings: list[CategoryFinding]
    question: str = Field("", description="One plain-language question about the heaviest missing category.")
    question_category: Optional[Category] = Field(
        None, description="The category the question asks about; it must be one still missing."
    )
    suggestion: str = Field("", description="Optional hint from the profile, e.g. 'you usually like linen'.")


# Words that name nothing. "I need an outfit" specifies no outfit type - the
# keyword scorer excludes them for the same reason - so evidence made only of
# these cannot show a category.
GENERIC_WORDS = {
    "outfit", "outfits", "look", "looks", "clothes", "clothing", "something",
    "anything", "wear", "style", "stuff", "thing", "things",
    "a", "an", "the", "to", "for", "some", "new", "nice", "good", "cool", "want", "need",
    "i", "me", "my", "mine", "we", "us", "you", "it", "is", "am", "are", "be", "do", "have",
    "can", "would", "like", "please", "and", "or", "of", "in", "on", "with", "show", "give", "find",
}


def _normal(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9'-]+", text.lower()))


def evidence_in_text(evidence: str, user_text: str) -> bool:
    """Is `evidence` the shopper's own words, naming something?

    True when it appears in `user_text` on whole-word boundaries and is not
    made only of words that name nothing ("outfit", "I want"). Shared by the
    clarifier's verification and the profile-write rules.
    """
    needle = _normal(evidence)
    if not set(needle.split()) - GENERIC_WORDS:
        return False
    return f" {needle} " in f" {_normal(user_text)} "


def verify_assessment(
    assessment: ClarificationAssessment, user_text: str, keyword: Optional[dict] = None
) -> dict:
    """Count only what the shopper's own words support.

    `keyword` is the keyword scorer's result for the same text. Its hits are in
    the shopper's words by construction, so they are kept even when the agent
    misses them - an agent that forgets "wedding guest dress" must not make the
    shopper say it again.
    """
    matched: dict[str, list[str]] = {}
    spans_used: set[str] = set()
    dropped = False
    for finding in assessment.findings:
        if finding.category in matched or finding.status != "stated":
            continue
        needle = _normal(finding.evidence)
        if (
            needle in spans_used                              # one span, one category
            or not evidence_in_text(finding.evidence, user_text)  # not their words, or names nothing
        ):
            dropped = True
            continue
        spans_used.add(needle)
        matched[finding.category] = [finding.value or finding.evidence]

    if keyword:
        for category in keyword["present"]:
            matched.setdefault(category, keyword["matched"].get(category, [category]))

    present = [d for d in DIMENSION_WEIGHTS if d in matched]
    missing = [d for d in DIMENSION_WEIGHTS if d not in matched]
    score = sum(DIMENSION_WEIGHTS[d] for d in present)
    tier = tier_for_score(score)

    explicit = asks_explicitly(user_text)
    promoted = explicit and tier == "medium"
    if promoted:
        tier = "high"

    question = ""
    if tier != "high":
        gap = next(d for d in GAP_ORDER if d in missing)
        asked = assessment.question.strip()
        # The agent's wording is used only when its question targets something
        # still missing and none of its findings were rejected; a question built
        # on a rejected finding, or one that re-asks a known category, is not.
        trusted = asked and not dropped and assessment.question_category in missing
        question = asked if trusted else QUESTION_FOR_GAP[gap]

    return {
        "tier": tier,
        "score": score,
        "max_score": MAX_SCORE,
        "present": present,
        "missing": missing,
        "matched": matched,
        "explicit_request": explicit,
        "promoted": promoted,
        "wants_choice": asks_for_choice(user_text),
        "question": question,
        "source": "agent",
    }


def fallback_result(keyword: dict) -> dict:
    """The keyword scorer's verdict plus a templated question, for when the agent fails."""
    question = ""
    if keyword["tier"] != "high":
        gap = next(d for d in GAP_ORDER if d in keyword["missing"])
        question = QUESTION_FOR_GAP[gap]
    return {**keyword, "question": question, "source": "fallback"}
