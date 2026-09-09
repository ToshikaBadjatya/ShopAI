from unittest.mock import MagicMock, patch

import pytest

from shopai.memory.conversation_memory import ConversationMemory


def _mock_supabase(rows):
    client = MagicMock()
    chain = client.table.return_value
    chain.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows
    chain.insert.return_value.execute.return_value.data = rows
    return client


def test_append_writes_a_row_scoped_to_the_user_and_run():
    client = _mock_supabase([{"id": "1"}])
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        ConversationMemory().append(
            "run-1", "user", "wedding guest dress", access_token="tok"
        )

    client.table.assert_called_with("conversation")
    inserted = client.table.return_value.insert.call_args[0][0]
    assert inserted["run_id"] == "run-1"
    assert inserted["sender"] == "user"
    assert inserted["message"] == "wedding guest dress"


def test_append_rejects_an_unknown_sender():
    """The column has a check constraint; fail before the round trip."""
    with pytest.raises(ValueError, match="sender"):
        ConversationMemory().append("run-1", "robot", "hi", access_token="tok")


def test_history_returns_turns_oldest_first():
    rows = [
        {"sender": "user", "message": "wedding guest dress"},
        {"sender": "agent", "message": "What colours do you like?"},
    ]
    client = _mock_supabase(rows)
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        turns = ConversationMemory().history("run-1", access_token="tok")

    assert [t["message"] for t in turns] == [
        "wedding guest dress",
        "What colours do you like?",
    ]


def test_user_text_joins_only_the_user_turns():
    """This is what clarity scoring reads - the agent's questions must not
    inflate the score with words the user never said."""
    rows = [
        {"sender": "user", "message": "wedding guest dress"},
        {"sender": "agent", "message": "Any colours in mind? Navy? Emerald?"},
        {"sender": "user", "message": "something in navy"},
    ]
    client = _mock_supabase(rows)
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        text = ConversationMemory().user_text("run-1", access_token="tok")

    assert text == "wedding guest dress\nsomething in navy"
    assert "Emerald" not in text


def test_requires_an_access_token():
    with pytest.raises(RuntimeError, match="access token"):
        ConversationMemory().history("run-1", access_token="")
