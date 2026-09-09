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

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from shopai.clarity import DIMENSION_WEIGHTS, score_request

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
