# Arize AX Tracing for the ShopAI CrewAI Crew

> **Note:** This spec originally targeted Arize Phoenix Cloud. During manual
> verification (Task 5) we found `phoenix.otel.register()` defaults to a
> `localhost` collector endpoint unless `PHOENIX_COLLECTOR_ENDPOINT` is
> explicitly set to a Phoenix Cloud URL — so the original zero-config
> assumption for Phoenix Cloud was wrong. Separately, the user's actual
> credentials were in Arize AX's format (a Space ID token), not a Phoenix
> Cloud collector URL. The project pivoted to target Arize AX directly,
> which auto-defaults to the correct `otlp.arize.com` collector with no
> endpoint configuration needed. This document has been updated to reflect
> that pivot.

## Purpose

Add observability for the `Shopai` crew's agent/task/tool execution by
sending OpenTelemetry traces to Arize AX. This lets us inspect LLM calls,
tool invocations, and task hand-offs (planning → recommendation →
visualize) for debugging and evaluation.

## Scope

- Instrument every way the crew can run: the CLI entry points in
  `src/shopai/main.py` (`run`, `train`, `replay`, `test`,
  `run_with_trigger`) and the FastAPI server (`run_api` / `api/app.py`).
- Target: Arize AX (Arize's hosted SaaS platform, arize.com), not
  self-hosted Phoenix and not Phoenix Cloud.
- Out of scope: custom span attributes, manual instrumentation of
  individual tools, dashboards/alerts configuration in Arize AX itself.

## Dependencies

Add to `pyproject.toml`:

- `arize-otel` — thin wrapper around OpenTelemetry SDK setup (`register()`)
  that targets Arize AX's collector endpoint (`otlp.arize.com`) by default.
- `openinference-instrumentation-crewai` — OpenInference auto-instrumentor
  that patches CrewAI's `Agent`/`Task`/`Crew`/tool execution to emit spans
  automatically once installed and activated.

`arize-phoenix-otel` (used in the original Phoenix Cloud version of this
spec) has been removed — it is no longer needed.

## Configuration

Two environment variables, read from `.env` (already loaded automatically
via `python-dotenv`, a transitive dependency of `crewai`):

- `ARIZE_API_KEY` (required) — Arize AX API key.
- `ARIZE_SPACE_ID` (required) — Arize AX space identifier.

Both must be set together for tracing to activate. If either is missing,
telemetry setup is skipped with a printed warning; the crew still runs
normally. Unlike the original Phoenix Cloud design, no collector-endpoint
override is needed: `arize.otel.register()` defaults to Arize AX's real
collector (`otlp.arize.com`) automatically.

## `src/shopai/telemetry.py`

A single function:

```python
def setup_telemetry() -> None:
    """Register OpenTelemetry tracing to Arize AX, if configured."""
```

Behavior:
1. Read `ARIZE_API_KEY` and `ARIZE_SPACE_ID` from `os.environ`. If either
   is missing, print a short warning (`"Arize telemetry disabled:
   ARIZE_API_KEY and ARIZE_SPACE_ID must both be set"`) and return without
   raising.
2. If both are present, call `arize.otel.register(project_name="shopai",
   auto_instrument=True)`. `register()` reads `ARIZE_API_KEY` and
   `ARIZE_SPACE_ID` from the environment itself, and defaults the
   collector endpoint to Arize AX's hosted collector — no explicit
   endpoint argument is needed. `auto_instrument=True` activates
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
- `src/shopai/api/app.py`: call `setup_telemetry()` at module import time,
  before `app = FastAPI(...)`, so tracing is active before the first
  request is handled by `run_api()`.

## Error handling

- Missing credentials: soft no-op with a warning, not an exception — the
  crew must keep working without Arize AX configured (e.g. running tests,
  or a contributor without Arize AX access).
- No other failure modes are expected to need explicit handling;
  `arize.otel.register()` and the OpenInference instrumentor are expected
  to raise only on genuine misconfiguration (e.g. a malformed space ID),
  which should surface normally rather than being swallowed.

## Testing

- Manual verification: run `shopai` (or `run_crew`) locally with
  `ARIZE_API_KEY` and `ARIZE_SPACE_ID` set, confirm traces appear in the
  Arize AX UI under the `shopai` project, showing spans for each agent's
  task execution and tool calls (weather lookup, outfit scraper, outfit
  visualizer).
- Manual verification without credentials set: confirm the crew still
  runs to completion and only prints the warning.
- Verified during implementation: `import shopai.main` with both env vars
  set prints a registration banner confirming `Collector Endpoint:
  otlp.arize.com` (not `localhost`) and populated `arize-space-id`/`api_key`
  headers; with either env var unset, only the warning prints and the
  import completes cleanly with no traceback.
