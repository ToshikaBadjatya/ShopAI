"""Verify the Styling Clarifier's findings before anything routes on them.

The agent reads the shopper's words and says which of five categories they
stated. It is trusted for judgement (is "breezy" a silhouette?) but not for
facts: a category counts only when the agent's quoted evidence appears in the
shopper's own words, and the tier is computed here from the verified findings.
No CrewAI import, so this tests without a model.
"""

import re
from typing import Literal

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
    suggestion: str = Field("", description="Optional hint from the profile, e.g. 'you usually like linen'.")


def _normal(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9'-]+", text.lower()))


def verify_assessment(assessment: ClarificationAssessment, user_text: str) -> dict:
    haystack = f" {_normal(user_text)} "
    matched: dict[str, list[str]] = {}
    for finding in assessment.findings:
        if finding.category in matched or finding.status != "stated":
            continue
        needle = _normal(finding.evidence)
        if needle and f" {needle} " in haystack:
            matched[finding.category] = [finding.value or finding.evidence]

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
        question = assessment.question.strip() or QUESTION_FOR_GAP[gap]

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
