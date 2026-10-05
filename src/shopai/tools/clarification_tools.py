"""Read-only context tools for the Styling Clarifier agent.

The clarifier judges which of five categories a shopper stated; these tools
give it the context to do that - a word-list lookup, the conversation so far,
and saved preferences. They only read. Whether a category counts is decided
afterwards, in Python, by `shopai.clarification.verify_assessment`.

Tools that touch a shopper's data are bound to a run and a token when they
are built, never asked for at call time: a model that has to invent an
identifier eventually invents the wrong one.
"""

import difflib
import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from shopai.clarity import DIMENSION_TERMS
from shopai.memory import memory
from shopai.tools.user_memory_tools import GetUserMemoryTool

# ---------------------------------------------------------------------------
# Context tools for the Styling Clarifier agent
# ---------------------------------------------------------------------------

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


def clarification_context_tools(run_id: str, access_token: str) -> list[BaseTool]:
    """The three read-only context tools, bound to one run and one shopper."""
    return [
        LookupCategoryTermsTool(),
        GetConversationHistoryTool(run_id=run_id, access_token=access_token),
        GetUserMemoryTool(access_token=access_token),
    ]
