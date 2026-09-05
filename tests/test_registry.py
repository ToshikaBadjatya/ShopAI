from unittest.mock import patch

from shopai.tools.registry import TOOL_REGISTRY, Tool, sync_tool_registry, tool_search
from shopai.tools.weather_tool import WeatherByLocationInput, WeatherByLocationTool


def test_registry_has_one_entry_per_tool():
    names = [tool.name for tool in TOOL_REGISTRY]
    assert len(names) == len(set(names)), "duplicate tool names in the registry"
    assert "weather_by_location" in names
    assert "outfit_product_scraper" in names
    assert "plan_task" in names


def test_entry_reads_schema_and_description_from_the_tool_itself():
    weather = next(t for t in TOOL_REGISTRY if t.name == "weather_by_location")

    assert weather.input_schema is WeatherByLocationInput
    assert weather.description == WeatherByLocationTool().description
    assert weather.handler is WeatherByLocationTool
    assert "weather" in weather.when_to_use.lower()


def test_every_entry_declares_when_to_use():
    assert all(tool.when_to_use for tool in TOOL_REGISTRY)


def test_agent_query_for_current_weather_resolves_to_the_weather_tool():
    """The scenario the toolbox exists for: a plain-language query about the
    weather should come back with the weather tool, ready to call - not just
    its name."""
    with patch("shopai.tools.registry.memory") as mock_memory:
        mock_memory.tool.search.return_value = ["weather_by_location"]
        results = tool_search("get the current weather")

    assert len(results) == 1
    weather = results[0]
    assert weather.name == "weather_by_location"
    assert weather.handler is WeatherByLocationTool
    assert weather.input_schema is WeatherByLocationInput

    # It's a live, callable tool - not a description of one.
    tool_instance = weather.handler()
    assert callable(tool_instance.run)


def test_tool_search_resolves_names_to_live_registry_entries():
    with patch("shopai.tools.registry.memory") as mock_memory:
        mock_memory.tool.search.return_value = ["weather_by_location", "outfit_product_scraper"]
        results = tool_search("what should I wear in the rain", k=2)

    mock_memory.tool.search.assert_called_once_with("what should I wear in the rain", k=2)
    assert [tool.name for tool in results] == ["weather_by_location", "outfit_product_scraper"]
    assert all(isinstance(tool, Tool) for tool in results)
    # Live objects, not just names or descriptions.
    assert results[0].handler is WeatherByLocationTool


def test_tool_search_ignores_names_no_longer_in_the_registry():
    with patch("shopai.tools.registry.memory") as mock_memory:
        mock_memory.tool.search.return_value = ["weather_by_location", "a_removed_tool"]
        results = tool_search("weather")

    assert [tool.name for tool in results] == ["weather_by_location"]


def test_sync_clears_then_registers_every_tool():
    with patch("shopai.tools.registry.memory") as mock_memory:
        sync_tool_registry()

    mock_memory.tool.clear.assert_called_once()
    assert mock_memory.tool.register.call_count == len(TOOL_REGISTRY)
    weather = next(t for t in TOOL_REGISTRY if t.name == "weather_by_location")
    mock_memory.tool.register.assert_any_call(weather.name, weather.description, weather.when_to_use)
