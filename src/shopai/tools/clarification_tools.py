"""What the Styling Clarifier asks about next, and when it should stop.

Wraps `shopai.clarity.score_request` rather than reinventing the check - one
clarity heuristic in the codebase, not two. Python already gates High
straight to the plan workflow before this tool is ever reached; this exists
for the Medium/Low path, where the question is "what is the one thing to ask
about now, and are we done yet?"

Returns prose, not JSON, on purpose. The agent holding this tool runs on a
small model whose only job is to turn one named gap into one question - it
should not also have to parse a payload and reformat it.
"""

import difflib
import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from shopai.clarity import DIMENSION_TERMS, DIMENSION_WEIGHTS, score_request
from shopai.memory import memory

# Heaviest dimensions first: closing these moves a request toward plannable
# in the fewest questions, so they are worth asking about before the rest.
GAP_PRIORITY: list[str] = sorted(
    DIMENSION_WEIGHTS, key=lambda dim: -DIMENSION_WEIGHTS[dim]
)


class FindMissingSegmentsInput(BaseModel):
    conversation_text: str = Field(
        ..., description="Everything the user has said in this run so far, verbatim."
    )


class FindMissingSegmentsTool(BaseTool):
    name: str = "find_missing_segments"
    description: str = (
        "Reads the conversation so far and answers two things: whether enough "
        "is known to plan an outfit, and if not, the single thing to ask about "
        "next. When enough is known it hands back the cumulative request to "
        "pass on. Call it before asking anything - it decides what is worth "
        "asking, so you only have to phrase it."
    )
    args_schema: Type[BaseModel] = FindMissingSegmentsInput

    def _run(self, conversation_text: str) -> str:
        result = score_request(conversation_text)

        if result["tier"] == "high":
            # High is 5 of 7, so a dimension can still be open here. Asking
            # anyway would be asking for its own sake - the request is already
            # plannable, which is the bar the rest of the system uses too.
            return (
                "COMPLETE - enough is known, ask nothing further.\n"
                f"Cumulative request: {conversation_text}"
            )

        missing = set(result["missing"])
        gap = next(dim for dim in GAP_PRIORITY if dim in missing)
        known = ", ".join(result["present"]) or "nothing yet"

        return (
            f"INCOMPLETE - one gap to close next: {gap}.\n"
            f"Already known: {known}.\n"
            f"Ask the user a single question about {gap}, in your own words."
        )


# ---------------------------------------------------------------------------
# Context tools for the Styling Clarifier agent
# ---------------------------------------------------------------------------

PROFILE_FIELDS = (
    "preferred_pieces", "colors_that_work", "colors_to_avoid",
    "preferred_styles", "preferred_fabrics", "color_season", "undertone",
)

_ALL_TERMS = sorted({t for terms in DIMENSION_TERMS.values() for t in terms})


def _categories_of(term: str) -> list[str]:
    return [dim for dim, terms in DIMENSION_TERMS.items() if term in terms]


class LookupInput(BaseModel):
    phrase: str = Field(..., description="Words from the shopper's message to look up.")


class LookupCategoryTermsTool(BaseTool):
    name: str = "lookup_category_terms"
    description: str = (
        "For each word in a phrase, says which of the five categories (event, "
        "outfit_type, colors, silhouette, accessories) it belongs to in ShopAI's "
        "word lists. 'close' lists near-spellings as hints only - a word absent "
        "from the lists can still name a category, so judge from the sentence."
    )
    args_schema: Type[BaseModel] = LookupInput

    def _run(self, phrase: str) -> str:
        words = []
        for word in dict.fromkeys(re.findall(r"[a-z][a-z'-]*", phrase.lower())):
            exact = _categories_of(word) or _categories_of(word.rstrip("s"))
            close = []
            if not exact and len(word) >= 4:
                for term in difflib.get_close_matches(word, _ALL_TERMS, n=3, cutoff=0.8):
                    close.extend({"term": term, "category": c} for c in _categories_of(term))
            words.append({"word": word, "exact": exact, "close": close})
        return json.dumps({"words": words})


class NoInput(BaseModel):
    """This tool takes no arguments."""


class GetConversationHistoryTool(BaseTool):
    name: str = "get_conversation_history"
    description: str = (
        "Everything the shopper has said in this conversation so far (their "
        "messages only, never yours). Read it before judging any category."
    )
    args_schema: Type[BaseModel] = NoInput
    run_id: str = ""
    access_token: str = ""

    def _run(self) -> str:
        if not self.access_token or not self.run_id:
            return json.dumps({"user_text": ""})
        try:
            text = memory.conversation.user_text(self.run_id, access_token=self.access_token)
        except Exception:
            text = ""
        return json.dumps({"user_text": text})


class GetUserProfileTool(BaseTool):
    name: str = "get_user_profile"
    description: str = (
        "The shopper's saved styling preferences. Use it only to make your "
        "question smarter ('you usually like X - still?'). Never treat a "
        "profile value as something they said today."
    )
    args_schema: Type[BaseModel] = NoInput
    access_token: str = ""

    def _run(self) -> str:
        if not self.access_token:
            return json.dumps({})
        try:
            row = memory.user_info.read(access_token=self.access_token)
        except Exception:
            row = {}
        return json.dumps({k: row[k] for k in PROFILE_FIELDS if row.get(k)})


def clarification_context_tools(run_id: str, access_token: str) -> list[BaseTool]:
    """The three read-only context tools, bound to one run and one shopper."""
    return [
        LookupCategoryTermsTool(),
        GetConversationHistoryTool(run_id=run_id, access_token=access_token),
        GetUserProfileTool(access_token=access_token),
    ]
