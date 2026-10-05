from shopai.tools.clarification_tools import GAP_PRIORITY, FindMissingSegmentsTool


def _run(text: str) -> str:
    return FindMissingSegmentsTool()._run(text)


def _gap_line(text: str) -> str:
    """The first line names the gap. The lines after it name what is already
    known, which mentions dimensions too - so assertions about the gap have to
    look here, not at the whole output."""
    return _run(text).splitlines()[0]


def test_returns_plain_text_not_json():
    """A 31B model relaying one string is far more reliable than the same
    model parsing a JSON blob and then reformatting it."""
    out = _run("help me with my style")
    assert not out.strip().startswith("{")


def test_names_one_gap_at_a_time_not_the_whole_missing_list():
    """Three dimensions are missing here; the agent should be pointed at one."""
    line = _gap_line("wedding guest dress")
    named = [dim for dim in GAP_PRIORITY if dim in line]
    assert named == ["colors"], f"expected only the next gap named, got {named}"


def test_the_heaviest_missing_dimension_comes_first():
    """Event and outfit type are double-weighted, so closing them moves a
    request toward plannable in the fewest questions."""
    line = _gap_line("something in navy")
    assert "event" in line
    assert "colors" not in line


def test_asks_about_event_first_when_nothing_is_known():
    out = _run("help me with my style")
    assert "INCOMPLETE" in out
    assert "event" in out
    assert "nothing yet" in out


def test_reports_what_is_already_known():
    out = _run("wedding guest dress")
    assert "event" in out.split("Already known:")[1]
    assert "outfit_type" in out.split("Already known:")[1]


def test_complete_once_high_tier_is_reached():
    """The same bar the rest of the system uses for plannable - not a second,
    stricter definition of 'enough'."""
    text = "black fitted midi dress for a cocktail party with gold jewellery"
    out = _run(text)

    assert "COMPLETE" in out
    assert "INCOMPLETE" not in out


def test_the_cumulative_request_is_the_accumulated_conversation():
    """Rebuilding from matched keywords alone would drop nuance like 'for my
    cousin's sangeet' in favour of the bare word 'sangeet'."""
    text = (
        "navy fitted saree for my cousin's sangeet with gold jewellery and "
        "matching heels"
    )
    out = _run(text)

    assert "COMPLETE" in out
    assert text in out


def test_high_tier_still_leaves_a_dimension_unasked():
    """High is 5 of 7, so a request can be plannable with a gap still open -
    the tool must stop asking anyway rather than chase all five."""
    text = "navy saree for my cousin's sangeet"
    out = _run(text)

    assert "COMPLETE" in out


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
