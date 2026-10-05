"""When to fold a conversation into a summary, and what the crew is handed.

Pure rules, no model and no database, so the thresholds are testable. The
summary is context for prompts, never evidence: scoring and fact checks keep
reading the shopper's verbatim turns.
"""

# Fold once the turns since the last summary pass either bar.
SUMMARIZE_AFTER_TURNS = 8
SUMMARIZE_AFTER_CHARS = 3000

# The newest turns are left verbatim - they are cheap and still the freshest.
KEEP_RECENT_TURNS = 4


def should_summarize(turns: list[dict]) -> bool:
    """`turns` are the ones after the last summary, oldest first."""
    if not turns:
        return False
    return (
        len(turns) > SUMMARIZE_AFTER_TURNS
        or sum(len(t.get("message", "")) for t in turns) > SUMMARIZE_AFTER_CHARS
    )


def split_for_fold(turns: list[dict]) -> tuple[list[dict], list[dict]]:
    """(turns to fold into the summary, turns kept verbatim)."""
    if len(turns) <= KEEP_RECENT_TURNS:
        return [], list(turns)
    return turns[:-KEEP_RECENT_TURNS], turns[-KEEP_RECENT_TURNS:]


def request_context(summary: str, turns: list[dict]) -> str:
    """The shopper's request so far, on one line: the summary, then their recent words.

    Only the shopper's turns count; the agent's own questions would read as
    things the shopper said.
    """
    words = " ".join(
        " ".join(t["message"].split()) for t in turns if t.get("sender") == "user"
    ).strip()
    return " ".join(part for part in (summary.strip(), words) if part)
