"""Read and update the shopper's profile, one generic pair of tools.

`update_user_memory` takes a field name from the `user_memory` columns, a
value, and the shopper's exact words as evidence. Every write passes
`shopai.profile_rules.check_fact` inside the tool, so a model that misuses it is
refused rather than trusted. The tools are bound to a token (and, for updates,
to the verbatim turns the learner was shown); the model never names a user.
"""

import json
from typing import Literal, Optional, Type, Union

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from shopai.memory import memory
from shopai.memory.user_memory import LIST_FIELDS, TEXT_FIELDS
from shopai.profile_rules import check_fact, merge_fact, normalize_value

PROFILE_FIELDS = TEXT_FIELDS + LIST_FIELDS
FieldName = Literal[PROFILE_FIELDS]  # type: ignore[valid-type]


def _fail(reason: str) -> str:
    """A refused call is information for the agent, not a crash."""
    return json.dumps({"ok": False, "error": reason})


class UpdateUserMemoryInput(BaseModel):
    field: FieldName = Field(..., description="Which profile field to update.")
    value: Union[str, list[str]] = Field(
        ..., description="A string for single-value fields, a list of strings for preference lists."
    )
    evidence: str = Field(
        ..., description="The shopper's exact words, copied from what they said, that show this."
    )


class UpdateUserMemoryTool(BaseTool):
    name: str = "update_user_memory"
    description: str = (
        "Save one lasting fact the shopper stated about themselves (height, body "
        "type, skin tone, undertone, colour season, contrast, background, or "
        "colours/fabrics/pieces/styles they always like or avoid). Pass their exact "
        "words as evidence. A fact that is not theirs, not lasting, or not in their "
        "words is refused."
    )
    args_schema: Type[BaseModel] = UpdateUserMemoryInput
    access_token: str = ""
    user_text: str = ""

    def _run(self, field: str, value: Union[str, list[str]], evidence: str) -> str:
        if not self.access_token:
            return _fail("No signed-in shopper, so nothing can be saved.")

        ok, reason = check_fact(field, value, evidence, self.user_text)
        if not ok:
            return _fail(reason)

        try:
            row = memory.user_info.read(access_token=self.access_token)
            update = merge_fact(row, field, normalize_value(field, value))
            memory.user_info.write(values=update, access_token=self.access_token)
        except Exception:
            return _fail("The profile could not be saved right now.")

        return json.dumps({"ok": True, "field": field, "stored": update[field]})


class GetUserMemoryInput(BaseModel):
    field: Optional[FieldName] = Field(
        None, description="One field to read. Leave out to read everything saved."
    )


class GetUserMemoryTool(BaseTool):
    name: str = "get_user_memory"
    description: str = (
        "The shopper's saved profile from the user_memory table. Use it only to "
        "make a question smarter ('you usually like linen - still?'); a saved "
        "value is never something they said today."
    )
    args_schema: Type[BaseModel] = GetUserMemoryInput
    access_token: str = ""

    def _run(self, field: Optional[str] = None) -> str:
        if not self.access_token:
            return json.dumps({})
        try:
            row = memory.user_info.read(access_token=self.access_token)
        except Exception:
            return json.dumps({})
        wanted = (field,) if field else PROFILE_FIELDS
        return json.dumps({k: row[k] for k in wanted if row.get(k)})


def user_memory_tools(access_token: str, user_text: str) -> list[BaseTool]:
    """Read and update tools for one shopper and the verbatim words they said."""
    return [
        GetUserMemoryTool(access_token=access_token),
        UpdateUserMemoryTool(access_token=access_token, user_text=user_text),
    ]
