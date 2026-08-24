"""Shared LLM wiring.

Every agent talks to one OpenAI-compatible gateway, configured through the
environment so no key or host is baked into the source.
"""

import os
from functools import lru_cache

from crewai import LLM

DEFAULT_BASE_URL = "http://localhost:3001/v1"
DEFAULT_MODEL = "auto"


def _gateway_model(model: str) -> str:
    """The gateway wants its own bare ids - drop an openai/ prefix if one was set."""
    return model.removeprefix("openai/")


@lru_cache(maxsize=1)
def default_llm() -> LLM:
    """The LLM every agent uses. Cached so one client is shared per process."""
    return LLM(
        # provider pins the OpenAI-compatible client, so any gateway model id works
        # without CrewAI trying to resolve it against its own provider registry.
        provider="openai",
        model=_gateway_model(os.environ.get("MODEL", DEFAULT_MODEL)),
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("LLM_API_KEY", ""),
    )
