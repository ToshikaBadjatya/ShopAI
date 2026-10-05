import base64
import json
from unittest.mock import MagicMock, patch

from shopai.memory.conversation_memory import ConversationMemory


def _token(user_id="user-1"):
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode()).decode().rstrip("=")
    return f"h.{payload}.s"


def _client(rows):
    """One mock that every query-builder call returns, so any chain order works."""
    chain = MagicMock()
    for name in ("select", "eq", "gt", "order", "upsert"):
        getattr(chain, name).return_value = chain
    chain.execute.return_value.data = rows
    client = MagicMock()
    client.table.return_value = chain
    return client, chain


def _patched(client):
    return patch("shopai.memory.conversation_memory.create_client", return_value=client)


def test_read_summary_returns_the_row_for_the_run():
    client, chain = _client([{"run_id": "r1", "summary": "dress, navy", "through_at": "t1"}])
    with _patched(client):
        row = ConversationMemory().read_summary("r1", access_token=_token())
    client.table.assert_called_with("conversation_summary")
    chain.eq.assert_called_with("run_id", "r1")
    assert row["summary"] == "dress, navy"


def test_read_summary_is_empty_when_the_run_has_none():
    client, _ = _client([])
    with _patched(client):
        assert ConversationMemory().read_summary("r1", access_token=_token()) == {}


def test_write_summary_upserts_only_the_fields_given_for_this_user():
    client, chain = _client([{"run_id": "r1"}])
    with _patched(client):
        ConversationMemory().write_summary(
            "r1", summary="dress, navy", through_at="t5", access_token=_token("user-9")
        )
    row = chain.upsert.call_args[0][0]
    assert row == {"run_id": "r1", "user_id": "user-9", "summary": "dress, navy", "through_at": "t5"}
    assert chain.upsert.call_args.kwargs["on_conflict"] == "run_id"


def test_turns_since_without_a_marker_returns_everything_in_order():
    client, chain = _client([{"message": "a"}, {"message": "b"}])
    with _patched(client):
        rows = ConversationMemory().turns_since("r1", None, access_token=_token())
    chain.gt.assert_not_called()
    chain.order.assert_called_with("created_at")
    assert [r["message"] for r in rows] == ["a", "b"]


def test_turns_since_a_marker_only_asks_for_later_turns():
    client, chain = _client([{"message": "c"}])
    with _patched(client):
        ConversationMemory().turns_since("r1", "2026-10-06T10:00:00Z", access_token=_token())
    chain.gt.assert_called_once_with("created_at", "2026-10-06T10:00:00Z")
