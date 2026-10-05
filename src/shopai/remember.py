"""Hand a shopper's own words to Mem0, minus anything sensitive.

Mem0 extracts and de-duplicates free-form facts and lets a later chat recall
them. It is a third-party cloud, so only the shopper's turns go (never the
agent's), and every sentence naming a sensitive attribute is removed first.
Best-effort: a failure here must never cost anyone their answer.
"""

from shopai.memory import memory
from shopai.memory.user_memory import user_id_from_token
from shopai.profile_rules import redact_sensitive


def remember(turns: list[dict], access_token: str, run_id: str) -> bool:
    """True when something was sent to Mem0."""
    user_id = user_id_from_token(access_token) if access_token else ""
    if not user_id:
        return False

    text = redact_sensitive(
        "\n".join(t["message"] for t in turns if t.get("sender") == "user")
    )
    if not text.strip():
        return False

    try:
        memory.conversation.add_to_conversation(
            user_id, run_id, [{"role": "user", "content": text}]
        )
    except Exception:
        return False
    return True
