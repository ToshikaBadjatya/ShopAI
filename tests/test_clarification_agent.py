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
