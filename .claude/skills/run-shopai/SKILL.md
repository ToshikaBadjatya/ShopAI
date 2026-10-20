---
name: run-shopai
description: Run, start, build, test or smoke-test the ShopAI FastAPI server (CrewAI outfit planner), including pointing it at a locally installed Ollama model (Qwen3) instead of the LLM gateway.
---

ShopAI is a CrewAI multi-agent outfit planner served by FastAPI/uvicorn on port 8000. It is driven with `curl`; the harness is `smoke.sh` in this directory. Paths below are relative to the repo root.

## Prerequisites

- `uv` and the project venv (`uv sync`).
- Ollama running on `:11434` with a tool-capable model. Verified with `Qwen3:latest` (8.2B):

```bash
curl -s localhost:11434/api/tags
```

## Run (agent path)

```bash
.claude/skills/run-shopai/smoke.sh          # start server if needed, check /docs + out-of-scope guard (seconds)
.claude/skills/run-shopai/smoke.sh full     # also sends a real shopping prompt (~9 min on Qwen3 8B)
.claude/skills/run-shopai/smoke.sh stop     # stop it
```

The script launches the server with env overrides, so `.env` is untouched:

```bash
LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama MODEL=Qwen3:latest uv run run_api
```

Endpoints (Swagger at http://localhost:8000/docs): `POST /outfit/plan/regular`, `POST /outfit/plan/occasional`, `DELETE /task/{run_id}`. Body: `{"prompt": "...", "userToken": null, "runId": null}`.

## Run (human path)

`uv run run_api` with the `.env` values: `LLM_BASE_URL` there points at a gateway on `localhost:3001`, which must be running. Ctrl-C to stop.

## Test

```bash
uv run pytest -q
```

Currently 96 pass, 2 fail (`tests/test_clarification_agent.py` imports `CLARIFICATION_MODEL` from `shopai.crew`, which no longer exists). Pre-existing, unrelated to Ollama.

## Gotchas

- **Env overrides beat `.env`.** `llm.py` reads `LLM_BASE_URL`, `LLM_API_KEY`, `MODEL`; shell values win, so no edit to `.env` is needed. Ollama ignores the key but it must be non-empty.
- **Greetings never reach the LLM.** "hi, who are you?" returns `errorKind: out_of_scope` in ~0.07s, so it proves routing, not the model. Use a shopping prompt to exercise Qwen3.
- **Qwen3 is slow.** A real prompt took ~549s, so use `curl -m 600` and `run_in_background`.
- **Qwen3 output is unreliable.** The real prompt returned `kind: "message"` with the reviewer agent's raw text, `outfits: []` and `errorKind: system_down` instead of a structured plan. Ollama's context was 4096 (`ollama ps`); the agents likely need more. This is a model-quality issue, not a connection failure.
- **`reload=True`.** The server runs two processes (reloader + worker), so `lsof -iTCP:8000` shows two PIDs.
- Startup logs show Arize/OpenTelemetry "Overriding of current TracerProvider" warnings; harmless.

## Troubleshooting

- `Ollama not reachable on :11434` -> `ollama serve`.
- `server did not start; see /tmp/shopai-server.log` -> read that log; a port 8000 clash shows there.
