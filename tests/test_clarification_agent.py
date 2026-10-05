from unittest.mock import patch

from shopai.crew import Shopai


def test_clarification_agent_is_configured():
    agent = Shopai().clarification_agent()
    assert agent.role
    assert agent.goal


def test_clarification_agent_joins_the_recommendation_crew():
    crew = Shopai().recommendation_crew("run-1")
    roles = [a.role for a in crew.agents]
    assert any("clarif" in role.lower() for role in roles)


def test_clarification_agent_does_not_delegate():
    """It asks the user; it has no one to hand work to."""
    agent = Shopai().clarification_agent()
    assert agent.allow_delegation is False


def test_clarification_agent_shares_the_default_model_while_unpinned():
    """CLARIFICATION_MODEL is empty because this gateway only serves its own
    "auto" routing - naming any model returns no usable provider key. Falling
    back to the default keeps the clarification path working."""
    from shopai.crew import CLARIFICATION_MODEL

    assert CLARIFICATION_MODEL == ""
    shopai = Shopai()
    assert shopai.clarification_agent().llm is shopai.recommendation_agent().llm


def test_setting_the_constant_pins_the_agent_to_that_model():
    """The plumbing stays ready, so flipping to a pinned model is one line
    once the gateway can serve one."""
    with patch("shopai.crew.CLARIFICATION_MODEL", "gemma-4-31b-it"):
        agent = Shopai().clarification_agent()

    assert "gemma-4-31b-it" in agent.llm.model


from unittest.mock import MagicMock, patch

from shopai.clarification import CategoryFinding, ClarificationAssessment


def _crew_returning(pydantic):
    crew = MagicMock()
    crew.kickoff.return_value = MagicMock(pydantic=pydantic)
    return crew


def test_agent_carries_the_three_context_tools():
    agent = Shopai().clarification_agent("run-1", "tok")
    assert {t.name for t in agent.tools} == {
        "lookup_category_terms", "get_conversation_history", "get_user_profile",
    }


def test_a_high_keyword_result_skips_the_agent_entirely():
    shopai = Shopai()
    with patch("shopai.crew.Crew") as crew_cls:
        result = shopai.run_clarification(
            "black fitted midi dress for a cocktail party with gold jewellery",
            "black fitted midi dress for a cocktail party with gold jewellery",
        )
    crew_cls.assert_not_called()
    assert result["tier"] == "high" and result["source"] == "keyword"


def test_the_agent_can_rescue_a_request_the_word_list_misses():
    text = "something for my cousin's mehndi in a kurta set, mint tones"
    assessment = ClarificationAssessment(findings=[
        CategoryFinding(category="event", status="stated", evidence="cousin's mehndi"),
        CategoryFinding(category="outfit_type", status="stated", evidence="kurta set"),
        CategoryFinding(category="colors", status="stated", evidence="mint tones"),
    ])
    shopai = Shopai()
    with patch("shopai.crew.Crew", return_value=_crew_returning(assessment)):
        result = shopai.run_clarification(text, text)
    assert result["source"] == "agent" and result["tier"] == "high"


def test_agent_failure_falls_back_to_the_keyword_scorer():
    """Review Focus 3."""
    shopai = Shopai()
    crew = MagicMock()
    crew.kickoff.side_effect = RuntimeError("model unreachable")
    with patch("shopai.crew.Crew", return_value=crew):
        result = shopai.run_clarification("Want a cool outfit", "Want a cool outfit")
    assert result["source"] == "fallback" and result["question"]


def test_missing_structured_output_falls_back():
    shopai = Shopai()
    with patch("shopai.crew.Crew", return_value=_crew_returning(None)):
        result = shopai.run_clarification("Want a cool outfit", "Want a cool outfit")
    assert result["source"] == "fallback"
