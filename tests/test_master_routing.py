from unittest.mock import MagicMock, patch

from shopai.clarity import score_request
from shopai.crew import Shopai

HIGH = "black fitted midi dress for a cocktail party with gold jewellery"


def _keyword_only(prompt, user_text, run_id="", access_token=""):
    """The clarification step without a model: the keyword verdict plus a fixed question."""
    return {**score_request(user_text), "question": "What's the occasion?", "source": "keyword"}


def _run(prompt, user_text=None):
    crew = MagicMock()
    crew.kickoff.return_value = "{}"

    # Patch the instance, never the class. @CrewBase's metaclass walks class
    # attributes expecting descriptors during __call__, and a MagicMock raises
    # AttributeError: __get__ - so patch.object(Shopai, ...) fails before your
    # test body ever runs.
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = user_text if user_text is not None else prompt
        mem.conversation.read_summary.return_value = {}
        result = shopai.run_master_recommendation(prompt, {}, access_token="tok")
    return result, crew


def test_a_specific_request_scores_high():
    result, _ = _run("black fitted midi dress for a cocktail party with gold jewellery")
    assert result["clarity"]["tier"] == "high"


def test_a_vague_request_scores_low():
    result, _ = _run("help me with my style")
    assert result["clarity"]["tier"] == "low"


def test_the_tier_reaches_the_crew_inputs():
    """The master cannot route on a score it was never handed."""
    _, crew = _run(HIGH)
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["clarity_tier"] == "high"
    assert inputs["clarity_missing"] == "none"


def test_a_vague_request_returns_the_question_without_starting_the_crew():
    result, crew = _run("help me with my style")
    crew.kickoff.assert_not_called()
    assert result["summary"] == "What's the occasion?"
    assert result["recommendations"] == []


def test_a_medium_request_also_asks_instead_of_running_the_crew():
    result, crew = _run("wedding guest dress")
    crew.kickoff.assert_not_called()
    assert result["clarity"]["tier"] == "medium"


def test_scoring_reads_the_accumulated_run_text_not_just_this_turn():
    """Turn two of a run is scored against everything the user has said."""
    result, _ = _run(
        "something in navy",
        user_text="wedding guest dress\nsomething in navy",
    )
    assert result["clarity"]["tier"] == "high"


def test_the_crew_plans_from_everything_the_shopper_said_not_the_last_message():
    """Regression: turn 2 used to reach the crew as just 'in navy, show me options'."""
    _, crew = _run(
        "in navy, show me options",
        user_text="I need a dress\nfor a wedding\nin navy, show me options",
    )
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["shopping_request"] == "I need a dress for a wedding in navy, show me options"


def test_a_summary_stands_in_for_the_turns_it_folded():
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = "I need a dress\nfor a wedding\nin navy\nmake it cheaper"
        mem.conversation.read_summary.return_value = {
            "summary": "navy wedding dress, avoid maroon", "through_at": "t5",
        }
        mem.conversation.turns_since.return_value = [
            {"sender": "user", "message": "make it cheaper", "created_at": "t9"},
            {"sender": "agent", "message": "Sure.", "created_at": "t10"},
        ]
        shopai.run_master_recommendation("make it cheaper", {}, run_id="run-1", access_token="tok")
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["shopping_request"] == "navy wedding dress, avoid maroon make it cheaper"


def test_a_guest_is_planned_from_the_one_message_they_sent_and_nothing_is_read():
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        shopai.run_master_recommendation(HIGH, {}, run_id="run-1")      # no access_token
    assert crew.kickoff.call_args.kwargs["inputs"]["shopping_request"] == HIGH
    mem.conversation.read_summary.assert_not_called()
    mem.conversation.user_text.assert_not_called()


def test_the_brief_lists_what_was_verified():
    _, crew = _run(HIGH)
    brief = crew.kickoff.call_args.kwargs["inputs"]["request_brief"]
    assert "outfit_type: dress" in brief and "colors: black" in brief


def test_the_brief_says_so_when_nothing_specific_was_found():
    from shopai.crew import _brief
    assert _brief({}) == "nothing specific"


def test_the_dead_conversation_text_input_is_gone():
    _, crew = _run(HIGH)
    assert "conversation_text" not in crew.kickoff.call_args.kwargs["inputs"]


def test_the_master_task_actually_uses_the_brief():
    description = Shopai().tasks_config["master_recommendation_task"]["description"]
    assert "{request_brief}" in description


def test_run_id_still_reaches_the_crew_inputs():
    """Regression guard: a fix that landed before this task added run_id to
    the inputs so the master can name which run it is on. Scoring must not
    displace it."""
    _, crew = _run(HIGH)
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["run_id"]


def test_writes_the_user_turn_to_the_transcript():
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = "wedding guest dress"
        shopai.run_master_recommendation(
            "wedding guest dress", {}, run_id="run-1", access_token="tok"
        )

    mem.conversation.append.assert_any_call("run-1", "user", "wedding guest dress", access_token="tok")


def test_the_user_turn_is_written_before_scoring_reads_it():
    """Scoring must see this message, not just prior turns - the write has to
    happen before the read that feeds score_request()."""
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    call_order = []
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.append.side_effect = lambda *a, **k: call_order.append("append")
        mem.conversation.user_text.side_effect = (
            lambda *a, **k: call_order.append("user_text") or "wedding guest dress"
        )
        shopai.run_master_recommendation(
            "wedding guest dress", {}, run_id="run-1", access_token="tok"
        )

    assert call_order[0] == "append"
    assert "user_text" in call_order


def test_a_question_is_recorded_as_the_agent_turn_without_running_the_crew():
    crew = MagicMock()
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = "help me with my style"
        shopai.run_master_recommendation(
            "help me with my style", {}, run_id="run-1", access_token="tok"
        )

    crew.kickoff.assert_not_called()
    mem.conversation.append.assert_any_call(
        "run-1", "agent", "What's the occasion?", access_token="tok"
    )


def test_writes_the_agent_summary_turn_after_the_crew_runs():
    crew = MagicMock()
    crew.kickoff.return_value = "not json, just prose for the user"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = HIGH
        shopai.run_master_recommendation(HIGH, {}, run_id="run-1", access_token="tok")

    mem.conversation.append.assert_any_call(
        "run-1", "agent", "not json, just prose for the user", access_token="tok"
    )


def test_no_agent_turn_written_when_the_crew_returns_a_real_plan():
    """A plan-kind response carries no summary text to record - matches the
    old app.py guard of `if response.message`, which never fired for a real
    plan (outfits populated means message is blank)."""
    crew = MagicMock()
    crew.kickoff.return_value = '{"recommendations": [{"outfit_name": "Look 1", "products": []}]}'
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = (
            "black fitted midi dress for a cocktail party with gold jewellery"
        )
        shopai.run_master_recommendation(
            "black fitted midi dress for a cocktail party with gold jewellery",
            {}, run_id="run-1", access_token="tok",
        )

    agent_calls = [c for c in mem.conversation.append.call_args_list if c.args[1] == "agent"]
    assert agent_calls == []


def test_transcript_writes_are_best_effort():
    """A write failure (e.g. an expired token) must not fail the whole request -
    conversation.append is infrastructure for scoring and history, not the
    thing the caller asked for."""
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.append.side_effect = Exception("JWT expired")
        mem.conversation.user_text.return_value = "help me with my style"
        result = shopai.run_master_recommendation(
            "help me with my style", {}, run_id="run-1", access_token="tok"
        )

    assert result["run_id"] == "run-1"


def test_no_transcript_write_without_an_access_token():
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        shopai.run_master_recommendation("help me with my style", {}, run_id="run-1")

    mem.conversation.append.assert_not_called()


def test_a_transcript_read_failure_falls_back_to_this_message_alone():
    """Regression: a Supabase access token is short-lived (~1h) and the app
    does not refresh it, so an expired token on the transcript read is
    routine. It must degrade to scoring this message alone, not fail the
    whole request."""
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.side_effect = Exception("JWT expired")
        result = shopai.run_master_recommendation(
            "black fitted midi dress for a cocktail party with gold jewellery",
            {},
            access_token="stale-tok",
        )

    assert result["clarity"]["tier"] == "high"
