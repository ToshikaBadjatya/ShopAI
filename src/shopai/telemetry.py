import os

from arize.otel import register


def setup_telemetry() -> None:
    """Register OpenTelemetry tracing to Arize AX, if configured.

    Reads ARIZE_API_KEY and ARIZE_SPACE_ID (both required) from the
    environment. If either is not set, tracing is skipped and a warning is
    printed instead of raising, so the crew keeps working without Arize
    configured.
    """
    api_key = os.environ.get("ARIZE_API_KEY")
    space_id = os.environ.get("ARIZE_SPACE_ID")
    if not api_key or not space_id:
        print("Arize telemetry disabled: ARIZE_API_KEY and ARIZE_SPACE_ID must both be set")
        return

    register(project_name="shopai", auto_instrument=True)
