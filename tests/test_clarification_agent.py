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


def test_clarification_agent_carries_the_missing_segments_tool():
    """It is not the manager, so - unlike the master - it can hold tools
    directly; no ledger-style task.tools workaround needed."""
    agent = Shopai().clarification_agent()
    assert {t.name for t in agent.tools} == {"find_missing_segments"}


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
