from unittest.mock import MagicMock, patch

from shopai.memory.conversation_memory import MAX_CONVERSATION_CONTEXT, ConversationMemory


def _memories(count, size):
    return [{"id": str(i), "memory": "x" * size} for i in range(count)]


def test_below_the_threshold_nothing_is_compacted():
    memory = ConversationMemory()
    with patch.object(memory, "expand_conversation") as expand:
        expand.return_value = {"memories": _memories(50, 10)}
        result = memory.compact("user-1", "run-1")

    assert result["compacted"] is False
    assert "context" in result["reason"].lower()


def test_crossing_the_threshold_triggers_compaction():
    """Enough text to exceed MAX_CONVERSATION_CONTEXT percent of 128000 tokens."""
    chars_for_full_window = 128000 * 4
    oversized = int(chars_for_full_window * (MAX_CONVERSATION_CONTEXT / 100)) + 4000

    memory = ConversationMemory()
    client = MagicMock()
    with patch.object(memory, "expand_conversation") as expand, \
         patch("shopai.memory.conversation_memory._client", return_value=client), \
         patch("shopai.memory.conversation_memory.default_llm") as llm:
        expand.return_value = {"memories": _memories(20, oversized // 20)}
        llm.return_value.call.return_value = "A dense summary."
        result = memory.compact("user-1", "run-1")

    assert result["compacted"] is True
    assert result["summary"] == "A dense summary."
    assert client.delete.called


def test_compaction_keeps_the_most_recent_turns_verbatim():
    chars_for_full_window = 128000 * 4
    oversized = int(chars_for_full_window * (MAX_CONVERSATION_CONTEXT / 100)) + 4000

    memory = ConversationMemory()
    with patch.object(memory, "expand_conversation") as expand, \
         patch("shopai.memory.conversation_memory._client", return_value=MagicMock()), \
         patch("shopai.memory.conversation_memory.default_llm") as llm:
        expand.return_value = {"memories": _memories(20, oversized // 20)}
        llm.return_value.call.return_value = "A dense summary."
        result = memory.compact("user-1", "run-1", keep_recent=6)

    assert result["kept_count"] == 6
    assert result["folded_count"] == 14


def test_threshold_is_a_percentage():
    assert 0 < MAX_CONVERSATION_CONTEXT <= 100
