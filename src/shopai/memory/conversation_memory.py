"""Conversational memory, backed by the Mem0 Platform.

One `run_id` is one conversation for one `user_id`. Mem0 does the fact
extraction and vector search; this module adds the shape ShopAI actually
needs on top - summarizing a conversation, compacting it so it stays cheap to
carry, and getting the full detail back when compaction isn't enough.

Requires MEM0_API_KEY (from app.mem0.ai). Nothing here talks to Mem0 without
it, and the error says so rather than failing obscurely later.
"""

import os
from typing import Any, Optional, Union

from mem0 import MemoryClient
from supabase import Client, create_client

from shopai.llm import calculate_context_usage, default_llm
from shopai.memory.base import Memory
from shopai.memory.user_memory import user_id_from_token

Message = dict[str, str]
Messages = Union[str, Message, list[Message]]

# How many of the most recent memories compact() leaves untouched.
DEFAULT_KEEP_RECENT = 6

# Compact once the conversation fills this share of the model's context window.
# A percentage rather than a token count because MODEL is "auto" here - a
# gateway picks per call, so any hand-tuned token figure would be guesswork.
MAX_CONVERSATION_CONTEXT = 80

CONVERSATION_TABLE = "conversation"

SENDERS = {"user", "agent"}


def _client() -> MemoryClient:
    api_key = os.environ.get("MEM0_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "Mem0 is not configured. Set MEM0_API_KEY (from app.mem0.ai)."
        )
    return MemoryClient(api_key=api_key)


def _scope(user_id: str, run_id: str) -> dict:
    if not user_id or not run_id:
        raise ValueError("Conversation memory needs both a user_id and a run_id.")
    return {"user_id": user_id, "run_id": run_id}


def _supabase(access_token: str) -> Client:
    """A client acting as the user - RLS decides what it can reach."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
        )
    if not access_token:
        raise RuntimeError("An access token is required: conversations are per-user.")

    client = create_client(url, key)
    client.postgrest.auth(access_token)
    return client


class ConversationMemory(Memory):
    """Mem0-backed memory for one conversation at a time.

    The ABC's read/write/delete work in terms of `key` = run_id and take
    `user_id` as a required keyword, since a conversation only means anything
    scoped to whoever is having it.
    """

    name = "conversation"

    # ---------------------------------------------------------- ABC surface

    def read(self, key: str, *, user_id: str = "", **_: Any) -> dict:
        """Full detail for a conversation. An alias for expand_conversation."""
        return self.expand_conversation(user_id=user_id, run_id=key)

    def write(self, key: str, values: dict, *, user_id: str = "", **_: Any) -> dict:
        """`values` is {"messages": ..., "metadata": ...}. An alias for add_to_conversation."""
        return self.add_to_conversation(
            user_id=user_id,
            run_id=key,
            messages=values.get("messages", []),
            metadata=values.get("metadata"),
        )

    def delete(self, key: str, *, user_id: str = "", **_: Any) -> bool:
        return self.delete_conversation(user_id=user_id, run_id=key)

    # --------------------------------------------------------- add / delete

    def add_to_conversation(
        self, user_id: str, run_id: str, messages: Messages, metadata: Optional[dict] = None
    ) -> dict:
        """Add a turn (or turns) to a conversation.

        `messages` is whatever Mem0 accepts: a plain string, one
        {"role","content"} dict, or a list of them - typically the latest
        user/assistant exchange.

        Returns Mem0's response, which includes the memories it chose to
        extract - not every message becomes a stored memory.
        """
        scope = _scope(user_id, run_id)
        return _client().add(messages, **scope, metadata=metadata)

    def delete_conversation(self, user_id: str, run_id: str) -> bool:
        """Forget an entire conversation. True whether or not it existed."""
        scope = _scope(user_id, run_id)
        _client().delete_all(**scope)
        return True

    # -------------------------------------------------------- read variants

    def expand_conversation(self, user_id: str, run_id: str, query: str = "") -> dict:
        """The full, uncompacted memory for a conversation.

        With `query`, returns the memories most relevant to it (a search).
        Without one, returns everything stored for the conversation, oldest
        first - what compact() would otherwise be hiding behind a summary.
        """
        scope = _scope(user_id, run_id)
        if query:
            result = _client().search(query, filters=scope)
            memories = result.get("results", result if isinstance(result, list) else [])
        else:
            result = _client().get_all(filters=scope)
            memories = result.get("results", result if isinstance(result, list) else [])
            memories = sorted(memories, key=lambda m: m.get("created_at") or "")

        return {"run_id": run_id, "user_id": user_id, "count": len(memories), "memories": memories}

    def summarize_conversation(self, user_id: str, run_id: str) -> dict:
        """A short prose summary of everything remembered for a conversation.

        Read-only - storage is untouched. Use compact() when the goal is to
        shrink what is stored, not just describe it.
        """
        detail = self.expand_conversation(user_id, run_id)
        memories = detail["memories"]

        if not memories:
            return {"run_id": run_id, "user_id": user_id, "summary": "", "memory_count": 0}

        facts = "\n".join(f"- {m.get('memory', m.get('text', ''))}" for m in memories)
        prompt = (
            "Summarize what is known about this conversation in 2-4 sentences. "
            "Be concrete - mention preferences, sizing, occasions, or decisions "
            "by name rather than describing that they exist.\n\n"
            f"Remembered facts:\n{facts}"
        )
        summary = default_llm().call(prompt).strip()

        return {
            "run_id": run_id,
            "user_id": user_id,
            "summary": summary,
            "memory_count": len(memories),
        }

    # ------------------------------------------------------------- compact

    def compact(self, user_id: str, run_id: str, keep_recent: int = DEFAULT_KEEP_RECENT) -> dict:
        """Fold older memories into one dense summary, keep the rest as-is.

        Fires when the conversation fills MAX_CONVERSATION_CONTEXT percent of
        the model's context window - not at a fixed number of turns, since what
        matters is how much room is left, not how many times someone spoke.

        The most recent `keep_recent` memories are left untouched - they are
        cheap and still likely relevant. Everything older is condensed into a
        single memory tagged `compacted: true` and the originals it replaced
        are deleted, the same trade a long-running chat makes: older detail
        for a cheaper, still-useful context.
        """
        detail = self.expand_conversation(user_id, run_id)
        memories = detail["memories"]

        # Measured over the memories, not the SQL turns: compaction shrinks
        # this set and never deletes a transcript row, so measuring the
        # transcript would climb forever and re-fire on every turn.
        joined = "\n".join(m.get("memory", m.get("text", "")) for m in memories)
        usage = calculate_context_usage(joined)

        if usage["percent"] < MAX_CONVERSATION_CONTEXT or len(memories) <= keep_recent:
            return {
                "run_id": run_id,
                "user_id": user_id,
                "compacted": False,
                "reason": (
                    f"Context usage {usage['percent']}% is below the "
                    f"{MAX_CONVERSATION_CONTEXT}% threshold."
                ),
                "memory_count": len(memories),
                "context_percent": usage["percent"],
            }

        to_fold, to_keep = memories[:-keep_recent], memories[-keep_recent:]
        facts = "\n".join(f"- {m.get('memory', m.get('text', ''))}" for m in to_fold)
        prompt = (
            "Condense these remembered facts into the smallest set of dense, "
            "still-useful statements. Merge duplicates and drop anything "
            "superseded by a later fact. One statement per line.\n\n"
            f"{facts}"
        )
        condensed_text = default_llm().call(prompt).strip()

        client = _client()
        for memory in to_fold:
            memory_id = memory.get("id")
            if memory_id:
                client.delete(memory_id)

        added = client.add(
            condensed_text,
            user_id=user_id,
            run_id=run_id,
            metadata={"compacted": True, "folded_count": len(to_fold)},
        )

        return {
            "run_id": run_id,
            "user_id": user_id,
            "compacted": True,
            "context_percent": usage["percent"],
            "folded_count": len(to_fold),
            "kept_count": len(to_keep),
            "summary": condensed_text,
            "added": added,
        }

    # ------------------------------------------------------- the transcript
    #
    # Mem0 above holds the summary; these hold what was actually said. Scoring
    # reads the turns rather than the summary, so compaction can never change
    # a run's clarity score.

    def append(self, run_id: str, sender: str, message: str, *, access_token: str) -> dict:
        """Record one turn."""
        if sender not in SENDERS:
            raise ValueError(f"Unknown sender '{sender}'. Use one of: {', '.join(sorted(SENDERS))}.")

        user_id = user_id_from_token(access_token)
        result = (
            _supabase(access_token)
            .table(CONVERSATION_TABLE)
            .insert({
                "run_id": run_id,
                "user_id": user_id,
                "sender": sender,
                "message": message,
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    def history(self, run_id: str, *, access_token: str) -> list[dict]:
        """Every turn in this run, oldest first."""
        result = (
            _supabase(access_token)
            .table(CONVERSATION_TABLE)
            .select("*")
            .eq("run_id", run_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def user_text(self, run_id: str, *, access_token: str) -> str:
        """Every user turn joined - what clarity scoring reads.

        The agent's own turns are excluded deliberately: a question listing
        colour options would otherwise score as the user having named colours.
        """
        turns = self.history(run_id, access_token=access_token)
        return "\n".join(t["message"] for t in turns if t.get("sender") == "user")
