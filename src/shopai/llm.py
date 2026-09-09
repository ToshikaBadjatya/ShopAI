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
    """The LLM every agent uses unless it asks for its own. Cached so one
    client is shared per process."""
    return llm_for(os.environ.get("MODEL", DEFAULT_MODEL))


@lru_cache(maxsize=8)
def llm_for(model: str) -> LLM:
    """An LLM pinned to one gateway model, for an agent whose work suits a
    different one than the crew's default.

    Cached per model id, so two agents naming the same model share a client
    rather than opening one each.
    """
    return LLM(
        # provider pins the OpenAI-compatible client, so any gateway model id works
        # without CrewAI trying to resolve it against its own provider registry.
        provider="openai",
        model=_gateway_model(model),
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("LLM_API_KEY", ""),
    )


# Context windows for models we might be pointed at. Anything absent falls
# through to the default below, which is what happens in practice: MODEL is
# "auto" here, so a gateway chooses per call and we cannot know the window.
MODEL_TOKEN_LIMITS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
}

DEFAULT_TOKEN_LIMIT = 128000


def calculate_context_usage(context: str, model: str = "gpt-5-mini") -> dict:
    """Calculate context window usage as percentage."""
    estimated_tokens = len(context) // 4  # ~4 chars per token
    max_tokens = MODEL_TOKEN_LIMITS.get(model, DEFAULT_TOKEN_LIMIT)
    percentage = (estimated_tokens / max_tokens) * 100
    return {"tokens": estimated_tokens, "max": max_tokens, "percent": round(percentage, 1)}
