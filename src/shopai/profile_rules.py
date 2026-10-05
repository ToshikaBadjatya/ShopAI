"""The rules a profile write must pass, and how a write is merged.

Pure functions, no model and no database. The update tool enforces them in
code, so a model that misuses the tool is simply refused rather than trusted.

A fact is stored only when it is the shopper's own words (verbatim evidence),
about the shopper and not someone else, and - for preferences - stated as
something lasting rather than a one-off want for today's outfit.
"""

import re
from typing import Any, Optional

from shopai.clarification import _normal, evidence_in_text
from shopai.memory.user_memory import LIST_FIELDS, TEXT_FIELDS

MAX_VALUE_CHARS = 200

COLOR_LISTS = ("colors_that_work", "colors_to_avoid")

FIRST_PERSON = {"i", "i'm", "im", "i've", "ive", "my", "me", "mine", "myself"}

# Someone else in the sentence means the fact may not be about the shopper.
THIRD_PARTY = {
    "cousin", "friend", "sister", "brother", "mom", "mother", "dad", "father",
    "husband", "wife", "daughter", "son", "boyfriend", "girlfriend", "partner",
    "colleague", "boss", "he", "she", "his", "her", "hers", "him", "they", "their",
}

# A preference worth keeping says it is lasting; "for this wedding I want red" is not.
LASTING_WORDS = {
    "always", "usually", "never", "avoid", "love", "hate", "prefer", "favourite",
    "favorite", "dislike", "cant",
}
LASTING_PHRASES = ("don't like", "do not like", "can't stand", "cannot stand")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?;\n]+", text) if s.strip()]


def _sentence_with(evidence: str, user_text: str) -> Optional[str]:
    needle = _normal(evidence)
    for sentence in _sentences(user_text):
        if f" {needle} " in f" {_normal(sentence)} ":
            return sentence
    return None


def normalize_value(field: str, value: Any) -> Any:
    """The value in the shape the column wants, or None when it is unusable."""
    if field in TEXT_FIELDS:
        if not isinstance(value, str):
            return None
        value = value.strip()
        return value if 0 < len(value) <= MAX_VALUE_CHARS else None

    if field in LIST_FIELDS:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            return None
        cleaned = [v.strip() for v in value if v.strip()]
        if not cleaned or any(len(v) > MAX_VALUE_CHARS for v in cleaned):
            return None
        return cleaned

    return None


def check_fact(field: str, value: Any, evidence: str, user_text: str) -> tuple[bool, str]:
    """Is this fact allowed to be written? (ok, reason when refused)."""
    if field not in TEXT_FIELDS + LIST_FIELDS:
        return False, f"'{field}' is not a profile field."
    if normalize_value(field, value) is None:
        return False, f"The value for '{field}' is empty or the wrong shape."
    if not evidence_in_text(evidence, user_text):
        return False, "The evidence is not the shopper's own words."

    sentence = _sentence_with(evidence, user_text)
    if sentence is None:
        return False, "The evidence spans more than one sentence."

    words = set(_normal(sentence).split())
    if words & THIRD_PARTY:
        return False, "The sentence is about someone else."
    if not words & FIRST_PERSON:
        return False, "The sentence is not about the shopper (no I / my)."

    if field in LIST_FIELDS:
        lowered = sentence.lower()
        if not (words & LASTING_WORDS) and not any(p in lowered for p in LASTING_PHRASES):
            return False, "A preference must be stated as lasting (always, never, avoid, love...)."

    return True, ""


def merge_fact(row: dict, field: str, value: Any) -> dict:
    """The columns to write for one accepted fact.

    Text fields replace. List fields merge without case duplicates. Adding a
    colour to one colour list removes it from the other: the latest statement
    wins, so a colour is never both liked and avoided.
    """
    if field in TEXT_FIELDS:
        return {field: value}

    existing = list(row.get(field) or [])
    seen = {v.lower() for v in existing}
    merged = existing + [v for v in dict.fromkeys(value) if v.lower() not in seen]
    update = {field: merged}

    if field in COLOR_LISTS:
        other = COLOR_LISTS[1 - COLOR_LISTS.index(field)]
        other_current = list(row.get(other) or [])
        added = {v.lower() for v in value}
        other_kept = [v for v in other_current if v.lower() not in added]
        if other_kept != other_current:
            update[other] = other_kept

    return update
