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


def test_run_id_still_reaches_the_crew_inputs():
    """Regression guard: a fix that landed before this task added run_id to
    the inputs so the master can name which run it is on. Scoring must not
    displace it."""
    _, crew = _run("wedding guest dress")
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["run_id"]


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
