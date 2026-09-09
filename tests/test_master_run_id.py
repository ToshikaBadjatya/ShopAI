"""The master should know which run it is on.

Its ledger tools are bound to the run at build time and take no run id, so
this is for the agent's own reference - reporting where it is, not deciding
where to write. The two must not be confused: a master that thinks it chooses
the run could choose the wrong one.
"""

from unittest.mock import MagicMock, patch

from shopai.crew import Shopai


def _kickoff_inputs(run_id=None):
    crew = MagicMock()
    crew.kickoff.return_value = "{}"

    # Patch the instance, not the class: @CrewBase's metaclass walks class
    # attributes expecting descriptors, and a MagicMock has no __get__.
    shopai = Shopai()
    with patch.object(shopai, "recommendation_crew", return_value=crew):
        result = shopai.run_master_recommendation("navy saree", {}, run_id=run_id)
    return crew.kickoff.call_args.kwargs["inputs"], result


def test_run_id_reaches_the_crew_inputs():
    inputs, _ = _kickoff_inputs(run_id="run-abc")
    assert inputs["run_id"] == "run-abc"


def test_a_generated_run_id_is_the_one_the_agent_sees():
    """The caller gets the run id back; the agent must be told the same one."""
    inputs, result = _kickoff_inputs()
    assert inputs["run_id"] == result["run_id"]


def test_the_master_task_description_mentions_the_run():
    """An input the template never references would reach nothing."""
    description = Shopai().tasks_config["master_recommendation_task"]["description"]
    assert "{run_id}" in description


def test_ledger_tools_still_take_no_run_id():
    """Seeing the run id must not become passing it - the tools are bound at
    build time precisely so the model cannot name a run."""
    crew = Shopai().recommendation_crew("run-abc")
    for tool in crew.tasks[0].tools:
        assert "run_id" not in tool.args_schema.model_fields
