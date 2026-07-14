# Arize AX Tracing for the ShopAI Crew — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Note:** This plan originally targeted Arize Phoenix Cloud (Tasks 1-4
> below were implemented and reviewed against that design). Task 5's
> manual verification found that `phoenix.otel.register()` defaults to a
> `localhost` collector unless `PHOENIX_COLLECTOR_ENDPOINT` is explicitly
> set to a Phoenix Cloud URL, and separately, the user's real credentials
> were in Arize AX's format. The project pivoted mid-Task-5 to target
> Arize AX instead. Tasks 1-4 below are left as historical record of what
> was built for Phoenix Cloud; the final "Pivot" section documents what
> superseded them. See the updated design spec:
> `docs/superpowers/specs/2026-07-14-phoenix-crewai-telemetry-design.md`.

**Goal:** Send OpenTelemetry traces from every CrewAI execution path (CLI entry points and the FastAPI server) to Arize AX.

**Architecture:** A `shopai.telemetry.setup_telemetry()` function wraps `arize.otel.register()`, gated on `ARIZE_API_KEY` and `ARIZE_SPACE_ID` both being present in the environment. It is called once at import time from `main.py` and once from `api/app.py`. Once registered, `openinference-instrumentation-crewai` auto-instruments CrewAI's `Agent`/`Task`/`Crew`/tool execution — no manual span code needed anywhere else in the codebase.

**Tech Stack:** Python 3.10+, crewai 1.14.5a2, `arize-otel`, `openinference-instrumentation-crewai`, `uv` for dependency management, `pytest` for tests.

## Global Constraints

- Target is Arize AX (Arize's hosted SaaS platform), not Phoenix Cloud and not a self-hosted Phoenix instance.
- Config comes from two env vars, both required: `ARIZE_API_KEY` and `ARIZE_SPACE_ID`.
- Missing either env var must never raise — the crew must run normally with tracing silently disabled, printing one warning line.
- Instrument all CLI entry points in `src/shopai/main.py` (`run`, `train`, `replay`, `test`, `run_with_trigger`) and the FastAPI server (`src/shopai/api/app.py`).
- No manual span/attribute code elsewhere — rely on OpenInference auto-instrumentation.

---

### Tasks 1-4 (historical — built for Phoenix Cloud, since superseded)

Tasks 1-4 originally added `arize-phoenix-otel` + `openinference-instrumentation-crewai`, implemented `shopai.telemetry.setup_telemetry()` around `phoenix.otel.register()` gated on `PHOENIX_API_KEY`, and wired it into `main.py` and `api/app.py`. Each was implemented and reviewed clean against the Phoenix Cloud design. See git history prior to the Pivot task below for that implementation; it has since been replaced.

---

### Pivot: Replace Phoenix Cloud with Arize AX

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (swap `arize-phoenix-otel` for `arize-otel`)
- Modify: `src/shopai/telemetry.py` (rewrite around `arize.otel.register()`)
- Modify: `tests/test_telemetry.py` (rewrite for `ARIZE_API_KEY`/`ARIZE_SPACE_ID`)
- Modify: `.env` (rename `PHOENIX_API_KEY` → `ARIZE_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT` → `ARIZE_SPACE_ID`)
- No change needed: `src/shopai/main.py`, `src/shopai/api/app.py` (both already just call `setup_telemetry()` at import time — the call sites don't change, only what's inside `telemetry.py`)

**Interfaces:**
- `setup_telemetry() -> None` signature unchanged; internals now call `arize.otel.register(project_name="shopai", auto_instrument=True)`.

- [x] **Step 1: Swap dependencies**
  ```bash
  uv add arize-otel
  ```
  Then remove `arize-phoenix-otel` from `pyproject.toml`'s `[project].dependencies` and run `uv sync`.

- [x] **Step 2: Rewrite `src/shopai/telemetry.py`**
  Read `ARIZE_API_KEY` and `ARIZE_SPACE_ID` from `os.environ`; if either is missing, print `"Arize telemetry disabled: ARIZE_API_KEY and ARIZE_SPACE_ID must both be set"` and return. Otherwise call `register(project_name="shopai", auto_instrument=True)` from `arize.otel` (it reads both env vars and the default Arize AX endpoint itself — no endpoint kwarg needed).

- [x] **Step 3: Rewrite `tests/test_telemetry.py`**
  Three tests: skip when `ARIZE_API_KEY` missing, skip when `ARIZE_SPACE_ID` missing, register called with `project_name="shopai", auto_instrument=True` when both are set.
  Run: `uv run pytest tests/test_telemetry.py -v` — expect 3 passed.

- [x] **Step 4: Rename `.env` credentials**
  Replace `PHOENIX_API_KEY=...` with `ARIZE_API_KEY=...` (same value) and `PHOENIX_COLLECTOR_ENDPOINT=...` with `ARIZE_SPACE_ID=...` (same value — it was already an Arize AX space-id token, not a URL).

- [x] **Step 5: Verify registration targets the real Arize AX endpoint**
  Run: `uv run python -c "import shopai.main"`
  Expected: banner prints `Collector Endpoint: otlp.arize.com` (not `localhost`), with `arize-space-id` and `api_key` present in Transport Headers.

- [x] **Step 6: Verify graceful no-op**
  Run with both `ARIZE_API_KEY` and `ARIZE_SPACE_ID` unset: same import should print only the warning, no traceback.

- [x] **Step 7: Run full test suite**
  `uv run pytest tests/ -v` — expect all passing.

- [ ] **Step 8: Manual end-to-end run** (deferred to user)
  Run `uv run shopai` with real credentials in `.env` and confirm spans for `planning_agent`, `recommendation_agent`, and `visualize_agent` (including tool calls `weather_by_location`, `outfit_product_scraper`, `outfit_visualizer`) appear in the Arize AX dashboard under the `shopai` project.

- [ ] **Step 9: Commit** (deferred — awaiting user go-ahead per session instruction not to commit automatically)
