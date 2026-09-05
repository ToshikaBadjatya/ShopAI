"""Tool memory - the searchable catalog of tools ShopAI's agents can use.

Backed by the Mem0 Platform, same as conversation memory, but scoped to one
fixed catalog rather than per-user/run: the tool registry is shared by every
agent, not owned by anyone in particular.

Mem0 only ever holds what needs to be searched - each tool's name,
description, and when to use it. The registry (`shopai.tools.registry.
TOOL_REGISTRY`) is what holds the schemas and handler classes; this store
exists purely to turn a natural-language query into the names of the closest
tools.

Requires MEM0_API_KEY (from app.mem0.ai), same as conversation memory.
"""

import os
from typing import Any

from mem0 import MemoryClient

from shopai.memory.base import Memory

# One shared scope for the whole catalog - there is one toolbox, not one per
# user or run.
CATALOG_SCOPE = {"user_id": "_shopai_tool_catalog"}


def _client() -> MemoryClient:
    api_key = os.environ.get("MEM0_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "Mem0 is not configured. Set MEM0_API_KEY (from app.mem0.ai)."
        )
    return MemoryClient(api_key=api_key)


def _entries(result: Any) -> list[dict]:
    return result.get("results", result if isinstance(result, list) else [])


class ToolMemory(Memory):
    """The semantic index over ShopAI's tool catalog.

    Entries carry no payload beyond what Mem0 needs to match a query to a
    tool's name - resolving that name to the tool's actual schemas and
    handler is the registry's job, not this store's.
    """

    name = "tool"

    # ---------------------------------------------------------- ABC surface

    def read(self, key: str, **_: Any) -> dict:
        """One tool's catalog entry by name, or {} if it isn't registered."""
        for entry in _entries(_client().get_all(filters=CATALOG_SCOPE)):
            if entry.get("metadata", {}).get("name") == key:
                return entry
        return {}

    def write(self, key: str, values: dict, **_: Any) -> dict:
        """Add one tool to the catalog. `values` carries its description and when_to_use."""
        return self.register(key, values.get("description", ""), values.get("when_to_use", ""))

    def delete(self, key: str, **_: Any) -> bool:
        """Remove one tool from the catalog by name."""
        client = _client()
        removed = False
        for entry in _entries(client.get_all(filters=CATALOG_SCOPE)):
            if entry.get("metadata", {}).get("name") == key:
                client.delete(entry["id"])
                removed = True
        return removed

    # ------------------------------------------------------------ catalog

    def register(self, tool_name: str, description: str, when_to_use: str = "") -> dict:
        """Index one tool so it can be found by search.

        `when_to_use` is folded into the embedded text alongside the
        description - it is often what a query actually looks like ("get the
        current weather") rather than a description of what the tool does.
        """
        text = f"{tool_name}: {description}"
        if when_to_use:
            text += f" Use this when: {when_to_use}"

        return _client().add(
            text,
            metadata={
                "name": tool_name,
                "description": description,
                "when_to_use": when_to_use,
            },
            **CATALOG_SCOPE,
        )

    def search(self, query: str, k: int = 5) -> list[str]:
        """The names of the `k` tools whose descriptions best match `query`."""
        result = _client().search(query, filters=CATALOG_SCOPE, top_k=k)
        names: list[str] = []
        for entry in _entries(result):
            tool_name = entry.get("metadata", {}).get("name")
            if tool_name and tool_name not in names:
                names.append(tool_name)
        return names[:k]

    def clear(self) -> None:
        """Wipe the whole catalog - used before a fresh sync."""
        _client().delete_all(**CATALOG_SCOPE)
