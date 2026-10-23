"""What the shopper sees while the master works.

CrewAI hands the crew's step callback an AgentAction (the agent is about to
use a tool) or an AgentFinish (an agent is done). This turns those into one
friendly line. A step with nothing worth saying returns None, and the line on
screen stays as it was.

Tool names are matched loosely: they are display names ("Delegate work to
coworker", "outfit_product_scraper") that differ across CrewAI versions and
our own registry, so a substring is safer than an exact key.
"""

import json
from typing import Any, Optional

# Phase lines, said by run_master_recommendation at its own seams.
STARTING = "Getting started..."
CLARIFYING = "Working out what you're after..."
PLANNING = "Planning your looks..."
REVIEWING = "Reviewing the picks..."
FINISHING = "Putting it together..."

# Friendly names for the crew's agents, keyed by a word in their role.
_AGENTS = {
    "review": "the reviewer",
    "visual": "the stylist sketching your outfit",
    "recommend": "the product finder",
    "clarif": "the clarifier",
}


def _agent_name(role: str) -> str:
    lowered = role.lower()
    for key, name in _AGENTS.items():
        if key in lowered:
            return name
    return "a teammate"


def _tool_input(step: Any) -> dict:
    raw = getattr(step, "tool_input", "") or ""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def progress_text(step: Any) -> Optional[str]:
    """One line for one CrewAI step, or None when there is nothing to say."""
    tool = (getattr(step, "tool", "") or "").lower()
    if not tool:
        return None

    args = _tool_input(step)

    if "delegate" in tool or "ask question" in tool:
        coworker = str(args.get("coworker", ""))
        return f"Handing off to {_agent_name(coworker)}..."
    if "scraper" in tool or "product" in tool:
        piece = str(args.get("outfit_piece") or "").strip()
        if piece:
            return f"Searching stores for {piece[:60]}..."
        return "Searching Amazon, Flipkart, Myntra and Meesho..."
    if "visual" in tool or "image" in tool:
        return "Sketching the outfit..."
    if "task" in tool or "status" in tool:
        return "Updating the plan..."
    if "conversation" in tool or "history" in tool:
        return "Reading back what you said..."
    if "profile" in tool:
        return "Checking your saved style..."
    if "category" in tool or "terms" in tool:
        return "Checking the details you gave..."
    return None
