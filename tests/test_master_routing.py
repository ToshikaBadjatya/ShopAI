from unittest.mock import MagicMock, patch

from shopai.crew import Shopai


def _run(prompt, user_text=None):
    crew = MagicMock()
    crew.kickoff.return_value = "{}"

    # Patch the instance, never the class. @CrewBase's metaclass walks class
    # attributes expecting descriptors during __call__, and a MagicMock raises
    # AttributeError: __get__ - so patch.object(Shopai, ...) fails before your
    # test body ever runs.
    shopai = Shopai()
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = user_text if user_text is not None else prompt
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
    _, crew = _run("wedding guest dress")
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["clarity_tier"] == "medium"
    assert "colors" in inputs["clarity_missing"]


def test_scoring_reads_the_accumulated_run_text_not_just_this_turn():
    """Turn two of a run is scored against everything the user has said."""
    result, _ = _run(
        "something in navy",
        user_text="wedding guest dress\nsomething in navy",
    )
    assert result["clarity"]["tier"] == "high"


def test_conversation_text_reaches_the_crew_inputs():
    """The master's task needs the accumulated text to hand to the
    clarification agent's tool via delegation - not just this turn's prompt."""
    _, crew = _run(
        "something in navy",
        user_text="wedding guest dress\nsomething in navy",
    )
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["conversation_text"] == "wedding guest dress\nsomething in navy"


def test_run_id_still_reaches_the_crew_inputs():
    """Regression guard: a fix that landed before this task added run_id to
    the inputs so the master can name which run it is on. Scoring must not
    displace it."""
    _, crew = _run("wedding guest dress")
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["run_id"]


def test_writes_the_user_turn_to_the_transcript():
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    shopai = Shopai()
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


def test_writes_the_agent_summary_turn_after_the_crew_runs():
    crew = MagicMock()
    crew.kickoff.return_value = "not json, just a question for the user"
    shopai = Shopai()
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = "help me with my style"
        shopai.run_master_recommendation(
            "help me with my style", {}, run_id="run-1", access_token="tok"
        )

    mem.conversation.append.assert_any_call(
        "run-1", "agent", "not json, just a question for the user", access_token="tok"
    )


def test_no_agent_turn_written_when_the_crew_returns_a_real_plan():
    """A plan-kind response carries no summary text to record - matches the
    old app.py guard of `if response.message`, which never fired for a real
    plan (outfits populated means message is blank)."""
    crew = MagicMock()
    crew.kickoff.return_value = '{"recommendations": [{"outfit_name": "Look 1", "products": []}]}'
    shopai = Shopai()
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
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.side_effect = Exception("JWT expired")
        result = shopai.run_master_recommendation(
            "black fitted midi dress for a cocktail party with gold jewellery",
            {},
            access_token="stale-tok",
        )

    assert result["clarity"]["tier"] == "high"
