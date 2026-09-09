"""The tool catalog - what an agent can discover.

`TOOL_REGISTRY` is the one list of every tool ShopAI's agents can use, each
entry holding the class that runs it. It is the source of truth for live
objects: Mem0 (via `shopai.memory.tool`) only ever sees a name, description,
and when to use it, since a fact store has no sensible way to hold a Python
class.

    from shopai.tools.registry import tool_search, sync_tool_registry

    sync_tool_registry()  # once, so the catalog index matches the registry
    tool_search("what will the weather be like")  # -> [Tool(name="weather_by_location", ...)]
"""

from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel

from shopai.memory import memory
from shopai.tools.outfit_scraper_tool import OutfitScraperTool
from shopai.tools.outfit_visualization_tool import OutfitVisualizationTool
from shopai.tools.task_ledger_tools import (
    GetStatusTool,
    PlanTaskTool,
    StopTaskTool,
    UpdateTaskContextTool,
    UpdateTaskStatusTool,
)
from shopai.tools.validation_tools import (
    InappropriateFlagTool,
    IntentValidatorTool,
    RelevanceFinderTool,
)
from shopai.tools.weather_tool import WeatherByLocationTool


class Tool(BaseModel):
    """One entry in the catalog: what it's for and how to run it."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    when_to_use: str
    input_schema: Type[BaseModel]
    output_schema: Optional[Type[BaseModel]] = None
    handler: Type[BaseTool]


def _entry(handler: Type[BaseTool], when_to_use: str, output_schema: Optional[Type[BaseModel]] = None) -> Tool:
    """Read a tool's own name/description/args_schema rather than restating them.

    `when_to_use` has no equivalent on a crewai tool, so it is supplied here -
    it is what makes a query like "get the current weather" match a tool
    named `weather_by_location`.
    """
    instance = handler()
    return Tool(
        name=instance.name,
        description=instance.description,
        when_to_use=when_to_use,
        input_schema=instance.args_schema,
        output_schema=output_schema,
        handler=handler,
    )


TOOL_REGISTRY: list[Tool] = [
    _entry(
        WeatherByLocationTool,
        "The agent needs current weather conditions for a location, e.g. "
        "\"get the current weather\" or \"what's it like in Mumbai today\".",
    ),
    _entry(
        OutfitScraperTool,
        "The agent needs to find or scrape real products matching an outfit description.",
    ),
    _entry(
        OutfitVisualizationTool,
        "The agent needs to generate a visual image of a described outfit.",
    ),
    _entry(
        PlanTaskTool,
        "The master agent needs to create and assign a new step to a subagent.",
    ),
    _entry(
        UpdateTaskStatusTool,
        "A step's execution status needs to move to a new state.",
    ),
    _entry(
        UpdateTaskContextTool,
        "A step's stored context or guardrails need to be revised.",
    ),
    _entry(
        StopTaskTool,
        "An active step is no longer needed and should be cancelled.",
    ),
    _entry(
        GetStatusTool,
        "Checking where a run or a specific step currently stands.",
    ),
    _entry(
        IntentValidatorTool,
        "Validating whether a request's intent is in scope for ShopAI.",
    ),
    _entry(
        RelevanceFinderTool,
        "Checking whether a request is relevant to fashion or shopping.",
    ),
    _entry(
        InappropriateFlagTool,
        "Checking a request for inappropriate content that should be rejected.",
    ),
]


def tool_search(query: str, k: int = 5) -> list[Tool]:
    """The `k` tools whose descriptions best match `query`, as live objects.

    Args:
        query: A natural language description of what you're trying to
               accomplish or the problem you're trying to solve. Be specific
               about the task or error you're encountering for better results.
        k: Number of relevant tools to return (default: 5).

    Returns:
        The matching `Tool` entries, each carrying its handler and schemas
        ready to use - not just names or descriptions.
    """
    by_name = {tool.name: tool for tool in TOOL_REGISTRY}
    names = memory.tool.search(query, k=k)
    return [by_name[name] for name in names if name in by_name]


def sync_tool_registry() -> None:
    """Push the registry's names and descriptions into the catalog index.

    Clears the catalog first so this is safe to re-run whenever the registry
    changes rather than accumulating stale duplicates.
    """
    memory.tool.clear()
    for tool in TOOL_REGISTRY:
        memory.tool.register(tool.name, tool.description, tool.when_to_use)
