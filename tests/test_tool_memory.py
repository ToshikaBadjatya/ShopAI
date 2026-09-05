from unittest.mock import MagicMock, patch

import pytest

from shopai.memory.tool_memory import CATALOG_SCOPE, ToolMemory


def test_client_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("MEM0_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MEM0_API_KEY"):
        ToolMemory().register("weather_by_location", "Looks up the weather.")


def test_register_indexes_name_description_and_when_to_use(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        ToolMemory().register(
            "weather_by_location",
            "Looks up the weather.",
            "The agent needs current weather conditions, e.g. \"get the current weather\".",
        )

    mock_client.add.assert_called_once_with(
        "weather_by_location: Looks up the weather. Use this when: "
        "The agent needs current weather conditions, e.g. \"get the current weather\".",
        metadata={
            "name": "weather_by_location",
            "description": "Looks up the weather.",
            "when_to_use": "The agent needs current weather conditions, e.g. \"get the current weather\".",
        },
        **CATALOG_SCOPE,
    )


def test_register_without_when_to_use_omits_it_from_the_text(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        ToolMemory().register("weather_by_location", "Looks up the weather.")

    mock_client.add.assert_called_once_with(
        "weather_by_location: Looks up the weather.",
        metadata={
            "name": "weather_by_location",
            "description": "Looks up the weather.",
            "when_to_use": "",
        },
        **CATALOG_SCOPE,
    )


def test_search_returns_matching_names_in_order(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {"metadata": {"name": "weather_by_location"}},
            {"metadata": {"name": "outfit_product_scraper"}},
        ]
    }

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        names = ToolMemory().search("what should I wear in the rain", k=2)

    assert names == ["weather_by_location", "outfit_product_scraper"]
    mock_client.search.assert_called_once_with(
        "what should I wear in the rain", filters=CATALOG_SCOPE, top_k=2
    )


def test_search_drops_duplicate_names(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {"metadata": {"name": "weather_by_location"}},
            {"metadata": {"name": "weather_by_location"}},
        ]
    }

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        names = ToolMemory().search("weather")

    assert names == ["weather_by_location"]


def test_delete_removes_matching_entries_only(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.get_all.return_value = {
        "results": [
            {"id": "1", "metadata": {"name": "weather_by_location"}},
            {"id": "2", "metadata": {"name": "outfit_product_scraper"}},
        ]
    }

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        removed = ToolMemory().delete("weather_by_location")

    assert removed is True
    mock_client.delete.assert_called_once_with("1")


def test_delete_returns_false_when_not_found(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.get_all.return_value = {"results": []}

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        removed = ToolMemory().delete("nonexistent")

    assert removed is False
    mock_client.delete.assert_not_called()


def test_clear_wipes_the_catalog_scope(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_client = MagicMock()

    with patch("shopai.memory.tool_memory.MemoryClient", return_value=mock_client):
        ToolMemory().clear()

    mock_client.delete_all.assert_called_once_with(**CATALOG_SCOPE)
