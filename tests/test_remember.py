import base64
import json
from unittest.mock import MagicMock, patch

from shopai.memory.conversation_memory import ConversationMemory
from shopai.remember import remember
from shopai.tools.clarification_tools import RecallMemoriesTool


def _token(user_id="user-1"):
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode()).decode().rstrip("=")
    return f"h.{payload}.s"


TURNS = [
    {"sender": "user", "message": "I always avoid maroon. My religion asks for modest sleeves."},
    {"sender": "agent", "message": "Any colours you love?"},
    {"sender": "user", "message": "Navy for the wedding"},
]


def test_remember_sends_only_redacted_user_turns():
    with patch("shopai.remember.memory") as mem:
        assert remember(TURNS, _token(), "run-1") is True
    args = mem.conversation.add_to_conversation.call_args.args
    assert args[0] == "user-1" and args[1] == "run-1"
    sent = json.dumps(args[2])
    assert "avoid maroon" in sent and "Navy for the wedding" in sent
    assert "religion" not in sent and "Any colours you love" not in sent


def test_remember_does_nothing_for_a_guest():
    with patch("shopai.remember.memory") as mem:
        assert remember(TURNS, "", "run-1") is False
    mem.conversation.add_to_conversation.assert_not_called()


def test_remember_skips_a_run_that_is_all_sensitive():
    turns = [{"sender": "user", "message": "My skin tone is deep."}]
    with patch("shopai.remember.memory") as mem:
        assert remember(turns, _token(), "run-1") is False
    mem.conversation.add_to_conversation.assert_not_called()


def test_remember_swallows_a_mem0_failure():
    with patch("shopai.remember.memory") as mem:
        mem.conversation.add_to_conversation.side_effect = RuntimeError("Mem0 is not configured.")
        assert remember(TURNS, _token(), "run-1") is False


def test_recall_searches_across_the_shoppers_runs_not_one():
    client = MagicMock()
    client.search.return_value = {"results": [{"memory": "likes linen"}, {"memory": "wedding in Jaipur"}]}
    with patch("shopai.memory.conversation_memory._client", return_value=client):
        out = ConversationMemory().recall("user-1", "the wedding", k=1)
    client.search.assert_called_once_with("the wedding", filters={"user_id": "user-1"})
    assert out == ["likes linen"]


def test_recall_without_a_user_never_searches():
    client = MagicMock()
    with patch("shopai.memory.conversation_memory._client", return_value=client):
        assert ConversationMemory().recall("", "anything") == []
    client.search.assert_not_called()


def test_recall_tool_is_bound_to_the_tokens_user():
    with patch("shopai.tools.clarification_tools.memory") as mem:
        mem.conversation.recall.return_value = ["wedding in Jaipur"]
        out = json.loads(RecallMemoriesTool(access_token=_token("user-7"))._run(query="the wedding"))
    mem.conversation.recall.assert_called_once_with("user-7", "the wedding")
    assert out == {"memories": ["wedding in Jaipur"]}


def test_recall_tool_for_a_guest_is_empty_and_searches_nothing():
    with patch("shopai.tools.clarification_tools.memory") as mem:
        out = json.loads(RecallMemoriesTool(access_token="")._run(query="the wedding"))
    assert out == {"memories": []}
    mem.conversation.recall.assert_not_called()


def test_recall_tool_swallows_a_mem0_failure():
    with patch("shopai.tools.clarification_tools.memory") as mem:
        mem.conversation.recall.side_effect = RuntimeError("Mem0 is not configured.")
        out = json.loads(RecallMemoriesTool(access_token=_token())._run(query="x"))
    assert out == {"memories": []}
