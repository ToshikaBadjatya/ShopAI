"""The master is a CrewAI manager, and CrewAI refuses a manager with tools.

The ledger rides on the master's task instead. These tests pin that down,
because the failure mode is silent in the wrong direction: a crew that builds
fine but hands the master no ledger looks healthy until an agent tries to plan
a step and has nothing to plan it with.
"""

from shopai.crew import Shopai

LEDGER_TOOL_NAMES = {
    "plan_task",
    "update_task_status",
    "update_task_context",
    "stop_task",
    "get_status",
}


def test_manager_agent_carries_no_tools_of_its_own():
    """CrewAI clears then rejects a manager_agent holding tools."""
    assert Shopai().recommendation_master_agent().tools == []


def test_building_the_crew_no_longer_raises():
    """The regression: every request failed with 'Manager agent should not
    have tools' because the master held the ledger directly."""
    crew = Shopai().recommendation_crew("run-1")
    crew._create_manager_agent()

    assert crew.manager_agent is not None
    assert crew.manager_agent.tools == []


def test_the_ledger_rides_on_the_masters_task():
    crew = Shopai().recommendation_crew("run-1")
    master_task = crew.tasks[0]

    assert {t.name for t in master_task.tools} == LEDGER_TOOL_NAMES


def test_ledger_tools_are_bound_to_the_run():
    """Bound at build time, never asked for at call time - a model that has to
    invent an identifier eventually invents the wrong one."""
    crew = Shopai().recommendation_crew("run-abc")

    assert all(t.run_id == "run-abc" for t in crew.tasks[0].tools)


def test_no_run_id_means_no_ledger_rather_than_a_shared_one():
    crew = Shopai().recommendation_crew()

    assert crew.tasks[0].tools == []


def test_the_master_receives_ledger_and_delegation_tools_together():
    """The point of the whole arrangement.

    CrewAI resolves `task.tools or agent.tools`, then merges the delegation
    tools into it. Both sets survive because their names do not collide.
    """
    crew = Shopai().recommendation_crew("run-1")
    crew._create_manager_agent()
    master_task = crew.tasks[0]

    resolved = crew._prepare_tools(
        crew.manager_agent,
        master_task,
        master_task.tools,
    )
    names = {t.name for t in resolved}

    assert LEDGER_TOOL_NAMES <= names, f"ledger tools lost, got {names}"
    assert len(names) > len(LEDGER_TOOL_NAMES), "delegation tools were not merged in"
