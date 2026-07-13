# Phoenix Cloud Tracing for the ShopAI CrewAI Crew

## Purpose

Add observability for the `Shopai` crew's agent/task/tool execution by
sending OpenTelemetry traces to Arize Phoenix Cloud. This lets us inspect
LLM calls, tool invocations, and task hand-offs (planning → recommendation →
visualize) for debugging and evaluation.

## Scope

- Instrument every way the crew can run: the CLI entry points in
  `src/shopai/main.py` (`run`, `train`, `replay`, `test`,
  `run_with_trigger`) and the FastAPI server (`run_api` / `api/app.py`).
- Target: Phoenix Cloud (hosted by Arize), not a self-hosted Phoenix
  instance.
- Out of scope: custom span attributes, manual instrumentation of
  individual tools, dashboards/alerts configuration in Phoenix itself.

## Dependencies

Add to `pyproject.toml`:

- `arize-phoenix-otel` — thin wrapper around OpenTelemetry SDK setup
  (`register()`) that targets Phoenix's collector endpoint.
- `openinference-instrumentation-crewai` — OpenInference auto-instrumentor
  that patches CrewAI's `Agent`/`Task`/`Crew`/tool execution to emit spans
  automatically once installed and activated.

## Configuration

Two environment variables, read from `.env` (already loaded automatically
via `python-dotenv`, a transitive dependency of `crewai`):

- `PHOENIX_API_KEY` (required) — Arize Phoenix Cloud API key. If unset,
  telemetry setup is skipped with a printed warning; the crew still runs
  normally.
- `PHOENIX_COLLECTOR_ENDPOINT` (optional) — overrides the default Phoenix
  Cloud collector endpoint, for flexibility if the endpoint changes or a
  different Phoenix Cloud space is used.

## New module: `src/shopai/telemetry.py`

A single function:

```python
def setup_telemetry() -> None:
    """Register OpenTelemetry tracing to Phoenix Cloud, if configured."""
```

Behavior:
1. Read `PHOENIX_API_KEY` from `os.environ`. If missing, print a short
   warning (`"Phoenix telemetry disabled: PHOENIX_API_KEY not set"`) and
   return without raising.
2. If present, call `phoenix.otel.register(project_name="shopai",
   auto_instrument=True, ...)`, passing `endpoint` only if
   `PHOENIX_COLLECTOR_ENDPOINT` is set (otherwise let the library default
   to Phoenix Cloud's endpoint). `auto_instrument=True` activates
   OpenInference auto-instrumentation for any supported library detected
   in the environment, including CrewAI (via
   `openinference-instrumentation-crewai`).
3. The function is idempotent enough to be safe if called more than once
   in the same process (register() itself just re-sets the global tracer
   provider); no explicit guard is required.

## Call sites

- `src/shopai/main.py`: call `setup_telemetry()` once at module import
  time (top of the file, after the `warnings.filterwarnings` line),
  before `Shopai` is used. This covers all CLI entry points since they
  all live in this module.
- `src/shopai/api/app.py`: call `setup_telemetry()` at module import time
  (or in a FastAPI startup hook, whichever fits the existing app
  structure) so tracing is active before the first request is handled by
  `run_api()`.

## Error handling

- Missing API key: soft no-op with a warning, not an exception — the crew
  must keep working without Phoenix configured (e.g. running tests, or a
  contributor without Phoenix Cloud access).
- No other failure modes are expected to need explicit handling;
  `phoenix.otel.register()` and the OpenInference instrumentor are
  expected to raise only on genuine misconfiguration (e.g. malformed
  endpoint URL), which should surface normally rather than being
  swallowed.

## Testing

- Manual verification: run `shopai` (or `run_crew`) locally with
  `PHOENIX_API_KEY` set, confirm traces appear in the Phoenix Cloud UI
  under the `shopai` project, showing spans for each agent's task
  execution and tool calls (weather lookup, outfit scraper, outfit
  visualizer).
- Manual verification without `PHOENIX_API_KEY` set: confirm the crew
  still runs to completion and only prints the warning.
