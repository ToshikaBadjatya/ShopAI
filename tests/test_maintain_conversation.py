from unittest.mock import MagicMock, patch

from shopai.crew import Shopai
from shopai.conversation_summary import KEEP_RECENT_TURNS


def _turns(n):
    """Alternating user/agent turns with ordered ids and timestamps."""
    return [
        {
            "id": f"id{i:02d}",
            "sender": "user" if i % 2 == 0 else "agent",
            "message": f"user said {i}" if i % 2 == 0 else f"agent said {i}",
            "created_at": f"t{i:02d}",
        }
        for i in range(n)
    ]


def _run(turns, *, summary_row=None, final=False, token="tok",
         summarize="folded summary", learned=True):
    """Run maintain_conversation against a fake transcript; return (result, mem, spies)."""
    shopai = Shopai()
    spies = MagicMock()
    shopai.run_summarize = spies.run_summarize
    shopai.run_summarize.return_value = summarize
    shopai.run_learner = spies.run_learner
    shopai.run_learner.return_value = learned

    def turns_since(run_id, since, *, access_token):
        return [t for t in turns if since is None or t["created_at"] > since]

    with patch("shopai.crew.memory") as mem, patch("shopai.crew.remember") as remember:
        mem.conversation.read_summary.return_value = summary_row or {}
        mem.conversation.turns_since.side_effect = turns_since
        result = shopai.maintain_conversation("run-1", token, final=final)
    spies.remember = remember
    return result, mem, spies


def _written(mem):
    """Every write_summary call merged into one dict of what was stored."""
    out = {}
    for call in mem.conversation.write_summary.call_args_list:
        out.update(call.kwargs)
    return out


def test_a_guest_is_skipped_and_nothing_is_touched():
    result, mem, spies = _run(_turns(12), token="")
    assert result == {"skipped": "guest"}
    mem.conversation.read_summary.assert_not_called()
    spies.run_summarize.assert_not_called()


def test_below_the_threshold_nothing_runs():
    result, mem, spies = _run(_turns(6))
    assert result == {"summarized": False, "learned": False}
    spies.run_summarize.assert_not_called()
    spies.run_learner.assert_not_called()
    mem.conversation.write_summary.assert_not_called()


def test_past_the_threshold_older_turns_are_folded_and_the_recent_ones_stay():
    turns = _turns(12)
    result, mem, spies = _run(turns)
    folded_text = spies.run_summarize.call_args.args[1]
    assert "user said 0" in folded_text and "agent said 7" in folded_text
    assert "user said 8" not in folded_text            # the 4 most recent stay verbatim
    last_folded = turns[:-KEEP_RECENT_TURNS][-1]["created_at"]
    assert _written(mem)["through_at"] == last_folded
    assert _written(mem)["summary"] == "folded summary"
    assert result["summarized"] is True


def test_the_learner_reads_the_verbatim_user_turns_it_is_about_to_fold():
    turns = _turns(12)
    result, mem, spies = _run(turns)
    learner_text = spies.run_learner.call_args.args[0]
    assert "user said 0" in learner_text and "user said 6" in learner_text
    assert "agent said" not in learner_text             # the shopper's words only
    assert "user said 10" not in learner_text           # recent turns are not folded yet
    assert result["learned"] is True
    assert _written(mem)["learned_through"] == turns[:-KEEP_RECENT_TURNS][-1]["created_at"]


def test_mem0_receives_the_same_folded_turns():
    turns = _turns(12)
    _, _, spies = _run(turns)
    remembered = spies.remember.call_args.args[0]
    assert [t["id"] for t in remembered] == [t["id"] for t in turns[:-KEEP_RECENT_TURNS]]


def test_a_failed_summary_does_not_advance_the_marker_so_it_retries():
    result, mem, _ = _run(_turns(12), summarize="")
    assert "through_at" not in _written(mem)
    assert result["summarized"] is False
    assert result["learned"] is True


def test_a_failed_learner_does_not_advance_its_marker_but_the_summary_still_lands():
    result, mem, _ = _run(_turns(12), learned=False)
    assert "learned_through" not in _written(mem)
    assert _written(mem)["summary"] == "folded summary"
    assert result["learned"] is False


def test_chat_end_learns_and_folds_everything_even_below_the_threshold():
    turns = _turns(5)
    result, mem, spies = _run(turns, final=True)
    assert "user said 4" in spies.run_learner.call_args.args[0]
    assert _written(mem)["through_at"] == turns[-1]["created_at"]
    assert _written(mem)["learned_through"] == turns[-1]["created_at"]
    assert result == {"summarized": True, "learned": True}


def test_already_folded_turns_are_not_summarised_again():
    turns = _turns(12)
    row = {"summary": "earlier summary", "through_at": "t05", "learned_through": "t05"}
    _, _, spies = _run(turns, summary_row=row, final=True)
    assert spies.run_summarize.call_args.args[0] == "earlier summary"
    assert "user said 4" not in spies.run_summarize.call_args.args[1]
    assert "user said 6" in spies.run_summarize.call_args.args[1]


def test_a_storage_failure_is_swallowed():
    shopai = Shopai()
    with patch("shopai.crew.memory") as mem:
        mem.conversation.read_summary.side_effect = Exception("JWT expired")
        assert shopai.maintain_conversation("run-1", "tok") == {"skipped": "error"}


def test_the_summariser_has_no_tools_and_the_learner_has_the_two_memory_tools():
    shopai = Shopai()
    assert shopai.summarizer_agent().tools == []
    assert {t.name for t in shopai.profile_learner_agent("tok", "I always avoid maroon").tools} == {
        "get_user_memory", "update_user_memory",
    }


def test_run_summarize_returns_the_text_and_empty_on_failure():
    shopai = Shopai()
    crew = MagicMock()
    crew.kickoff.return_value = "  navy wedding dress  "
    with patch("shopai.crew.Crew", return_value=crew):
        assert shopai.run_summarize("", "user said 1") == "navy wedding dress"
    crew.kickoff.side_effect = RuntimeError("model unreachable")
    with patch("shopai.crew.Crew", return_value=crew):
        assert shopai.run_summarize("", "user said 1") == ""


def test_run_learner_reports_success_and_failure():
    shopai = Shopai()
    crew = MagicMock()
    with patch("shopai.crew.Crew", return_value=crew):
        assert shopai.run_learner("I always avoid maroon", "tok") is True
    crew.kickoff.side_effect = RuntimeError("model unreachable")
    with patch("shopai.crew.Crew", return_value=crew):
        assert shopai.run_learner("I always avoid maroon", "tok") is False
