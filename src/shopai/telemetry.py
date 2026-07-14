import os

from phoenix.otel import register


def setup_telemetry() -> None:
    """Register OpenTelemetry tracing to Phoenix Cloud, if configured.

    Reads PHOENIX_API_KEY (required) and PHOENIX_COLLECTOR_ENDPOINT
    (optional) from the environment. If PHOENIX_API_KEY is not set,
    tracing is skipped and a warning is printed instead of raising, so
    the crew keeps working without Phoenix configured.
    """
    api_key = os.environ.get("PHOENIX_API_KEY")
    if not api_key:
        print("Phoenix telemetry disabled: PHOENIX_API_KEY not set")
        return

    kwargs = {"project_name": "shopai", "auto_instrument": True}

    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if endpoint:
        kwargs["endpoint"] = endpoint

    register(**kwargs)
