import json
from unittest.mock import patch

from shopai.tools.clarification_tools import (
    GetConversationHistoryTool, GetUserProfileTool, LookupCategoryTermsTool,
    clarification_context_tools,
)


def test_lookup_reports_the_category_of_an_exact_word():
    out = json.loads(LookupCategoryTermsTool()._run("breezy sundress"))
    by_word = {w["word"]: w for w in out["words"]}
    assert "silhouette" in by_word["breezy"]["exact"]
    assert "outfit_type" in by_word["sundress"]["exact"]


def test_lookup_offers_close_matches_as_hints_only():
    out = json.loads(LookupCategoryTermsTool()._run("pastle"))
    word = out["words"][0]
    assert word["exact"] == []
    assert any(c["term"] == "pastel" for c in word["close"])


def test_cool_is_not_reported_as_a_colour():
    out = json.loads(LookupCategoryTermsTool()._run("cool"))
    assert out["words"][0]["exact"] == []


def test_history_returns_user_turns_only_for_the_bound_run():
    with patch("shopai.tools.clarification_tools.memory") as mem:
        mem.conversation.user_text.return_value = "I need a dress\nfor a wedding"
        out = GetConversationHistoryTool(run_id="r1", access_token="tok")._run()
    mem.conversation.user_text.assert_called_once_with("r1", access_token="tok")
    assert "for a wedding" in out


def test_history_without_a_token_is_empty_not_an_error():
    """Review Focus 4: a guest has no transcript."""
    out = json.loads(GetConversationHistoryTool(run_id="r1", access_token="")._run())
    assert out["user_text"] == ""


def test_history_read_failure_degrades_to_empty():
    with patch("shopai.tools.clarification_tools.memory") as mem:
        mem.conversation.user_text.side_effect = Exception("JWT expired")
        out = json.loads(GetConversationHistoryTool(run_id="r1", access_token="tok")._run())
    assert out["user_text"] == ""


def test_profile_returns_only_styling_preferences():
    row = {"user_id": "u1", "preferred_pieces": ["kurta"], "colors_that_work": ["sage"],
           "preferred_styles": ["minimal"], "details": {"phone": "123"}}
    with patch("shopai.tools.clarification_tools.memory") as mem:
        mem.user_info.read.return_value = row
        out = json.loads(GetUserProfileTool(access_token="tok")._run())
    assert out["preferred_pieces"] == ["kurta"]
    assert "user_id" not in out and "details" not in out


def test_profile_without_a_token_is_empty():
    assert json.loads(GetUserProfileTool(access_token="")._run()) == {}


def test_factory_returns_the_three_context_tools():
    names = {t.name for t in clarification_context_tools("r1", "tok")}
    assert names == {"lookup_category_terms", "get_conversation_history", "get_user_profile"}
