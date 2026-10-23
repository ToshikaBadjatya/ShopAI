from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from crewai.tools import BaseTool

from shopai import progress
from shopai.clarity import score_request
from shopai.crew import Shopai, step_hook
from shopai.progress import progress_text
from shopai.runs import RunCancelled

HIGH = "black fitted midi dress for a cocktail party with gold jewellery"


class _LoopingLLM(BaseLLM):
    """Always asks for the same tool, so the agent never finishes on its own."""

    calls: int = 0

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None):
        self.calls += 1
        return 'Thought: keep looking\nAction: noop\nAction Input: {"x": "y"}'

    def supports_function_calling(self) -> bool:
        return False


class _Noop(BaseTool):
    name: str = "noop"
    description: str = "Does nothing."

    def _run(self, x: str = "") -> str:
        return "nothing"


def test_a_stop_raised_from_the_step_callback_ends_a_real_kickoff():
    """The whole stop design rests on this: CrewAI retries an agent on any
    Exception, so RunCancelled must get through as a BaseException - after one
    model call, not after the retry budget."""
    llm = _LoopingLLM(model="stub")
    agent = Agent(role="r", goal="g", backstory="b", llm=llm, tools=[_Noop()], max_iter=10)
    task = Task(description="d", expected_output="o", agent=agent)
    crew = Crew(
        agents=[agent], tasks=[task], process=Process.sequential,
        step_callback=step_hook(lambda _: None, lambda: True),
    )

    with pytest.raises(RunCancelled):
        crew.kickoff()
    assert llm.calls == 1


def test_the_step_hook_reports_a_friendly_line():
    lines = []
    hook = step_hook(lines.append, lambda: False)
    hook(SimpleNamespace(tool="outfit_product_scraper", tool_input='{"outfit_piece": "navy kurta"}'))
    assert lines == ["Searching stores for navy kurta..."]


@pytest.mark.parametrize("tool, expected", [
    ("outfit_visualizer", "Sketching the outfit..."),
    ("plan_task", "Updating the plan..."),
    ("get_status", "Updating the plan..."),
    ("get_user_profile", "Checking your saved style..."),
    ("Delegate work to coworker", "Handing off to a teammate..."),
])
def test_progress_text_maps_tools(tool, expected):
    assert progress_text(SimpleNamespace(tool=tool, tool_input="{}")) == expected


def test_delegation_names_the_coworker():
    step = SimpleNamespace(
        tool="Delegate work to coworker",
        tool_input='{"coworker": "Review Recommendation Agent", "task": "check"}',
    )
    assert progress_text(step) == "Handing off to the reviewer..."


def test_an_agent_finish_says_nothing():
    assert progress_text(SimpleNamespace(output="done")) is None


def _keyword_only(prompt, user_text, run_id="", access_token="", step_callback=None):
    return {**score_request(user_text), "question": "What's the occasion?", "source": "keyword"}


def _run(prompt, should_stop=None):
    crew = MagicMock()
    crew.kickoff.return_value = "{}"
    lines = []
    shopai = Shopai()
    shopai.run_clarification = _keyword_only
    with patch.object(shopai, "recommendation_crew", return_value=crew) as build, \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = prompt
        result = shopai.run_master_recommendation(
            prompt, {}, access_token="tok", on_progress=lines.append, should_stop=should_stop,
        )
    return result, lines, build


def test_the_master_reports_its_phases():
    _, lines, _ = _run(HIGH)
    assert lines == [progress.CLARIFYING, progress.PLANNING, progress.FINISHING]


def test_a_vague_request_stops_reporting_at_the_question():
    _, lines, build = _run("help me with my style")
    assert lines == [progress.CLARIFYING]
    build.assert_not_called()


def test_the_crew_gets_the_step_and_task_callbacks():
    _, _, build = _run(HIGH)
    assert build.call_args.kwargs["step_callback"] is not None
    assert build.call_args.kwargs["task_callback"] is not None


def test_a_stop_before_the_crew_never_starts_it():
    with pytest.raises(RunCancelled):
        _run(HIGH, should_stop=lambda: True)


def test_a_stop_is_not_swallowed_by_the_clarifier_fallback():
    """run_clarification falls back on any Exception - a stop must not be one."""
    shopai = Shopai()

    def cancelled(*_, **__):
        raise RunCancelled()

    with patch.object(shopai, "clarification_agent", side_effect=cancelled):
        with pytest.raises(RunCancelled):
            shopai.run_clarification("Want a cool outfit", "Want a cool outfit")
