# ShopAI — project guide for Claude

ShopAI is an AI outfit-planning and shopping assistant ("Sia"). A **CrewAI** multi-agent backend (FastAPI) serves an **Android** (Kotlin/Compose) app. Memory lives in Supabase and Mem0; traces go to Arize. CrewAI conventions are in [AGENTS.md](../AGENTS.md) — follow those, and check the installed version before writing CrewAI code.

## Where to go

| I want to... | Go to |
|---|---|
| Change what an agent is or does (role/goal/backstory) | [src/shopai/config/agents.yaml](../src/shopai/config/agents.yaml) |
| Change a task's description / expected output | [src/shopai/config/tasks.yaml](../src/shopai/config/tasks.yaml) |
| Wire agents/tasks/crews, parse crew output | [src/shopai/crew.py](../src/shopai/crew.py) (`Shopai` class; master/clarification/review agents are deliberately **not** `@agent`-decorated) |
| Add/change an HTTP endpoint | [src/shopai/api/app.py](../src/shopai/api/app.py) — `POST /outfit/plan/regular`, `POST /outfit/plan/occasional`, `DELETE /task/{run_id}`. `api/dummy_app.py` is retired, reference only |
| Change the LLM / model / gateway | [src/shopai/llm.py](../src/shopai/llm.py) — reads `LLM_BASE_URL`, `LLM_API_KEY`, `MODEL` from env |
| Change guardrail word lists or clarity scoring | [vocabulary.py](../src/shopai/vocabulary.py), [clarity.py](../src/shopai/clarity.py) (deterministic, no model) |
| Change prompt templates | [src/shopai/prompts.py](../src/shopai/prompts.py) |
| Change tracing | [src/shopai/telemetry.py](../src/shopai/telemetry.py) (Arize) |
| Change memory | [src/shopai/memory/](../src/shopai/memory/) — user (Supabase), conversation + tool (Mem0), task ledger |
| Change DB schema | [supabase/migrations/](../supabase/migrations/) (apply by pasting into the Supabase SQL editor) |
| Change the Android app | [src/shopai/mobile/](../src/shopai/mobile/) — `screens/`, `viewmodel/`, `data/api/`, `reusables/`, `ui/theme/` |
| Run / smoke-test the server (incl. on local Ollama) | `/run-shopai` skill → [.claude/skills/run-shopai/](skills/run-shopai/SKILL.md) |

## Agents → tasks → tools

| Agent | Job | Tools |
|---|---|---|
| `planning_agent` | Shopping plan from the request | `WeatherByLocationTool` |
| `recommendation_agent` | Find products per outfit piece | `OutfitScraperTool` |
| `visualize_agent` | Render the outfit image | `OutfitVisualizationTool` |
| `marketplace_agent` | **Stub** — role is still `TODO`, no tools | — |
| `recommendation_master_agent` | Hierarchical manager; plans against the task ledger | task-ledger tools (per `run_id`) |
| `review_recommendation_agent` | Reviews the master's output (approve / substitute) | — |
| `clarification_agent` | Pre-step (not in the crew): judges which of event / outfit_type / colors / silhouette / accessories the shopper stated, then asks one question | `lookup_category_terms`, `get_conversation_history`, `get_user_profile` |

Request flow: guardrail (`run_validation`) → keyword clarity score → `run_clarification` (high skips the agent; otherwise the agent judges and Python verifies its quoted evidence, falling back to the keyword score on failure) → not ready: the question is returned as `kind: "message"` and the crew never starts; ready: hierarchical crew (master + review) → API response `kind` = `plan` / `message` / `permission` / `error`.

## Tools — where they come from

| Tool | File | External source |
|---|---|---|
| Weather | [tools/weather_tool.py](../src/shopai/tools/weather_tool.py) | Open-Meteo (no key). Docs: [tools/api_reference/weather_api.md](../src/shopai/tools/api_reference/weather_api.md) |
| Outfit scraper | [tools/outfit_scraper_tool.py](../src/shopai/tools/outfit_scraper_tool.py) | Scrapes Amazon, Flipkart, Myntra, Meesho |
| Visualization | [tools/outfit_visualization_tool.py](../src/shopai/tools/outfit_visualization_tool.py) | Hugging Face image model (`IMAGE_MODEL`, default FLUX.1-schnell; needs `HF_TOKEN`). Images land in `src/shopai/output/` |
| Task ledger | [tools/task_ledger_tools.py](../src/shopai/tools/task_ledger_tools.py) | Task memory |
| Validation | [tools/validation_tools.py](../src/shopai/tools/validation_tools.py) | Deterministic intent/relevance/inappropriate checks |
| Clarification context | [tools/clarification_tools.py](../src/shopai/tools/clarification_tools.py) | Read-only: word-list lookup (`clarity.py`), conversation history (Mem0/Supabase), saved profile (Supabase). Verification logic lives in [clarification.py](../src/shopai/clarification.py) |

New tool: add a `BaseTool` in `tools/`, register it in [tools/registry.py](../src/shopai/tools/registry.py) (`TOOL_REGISTRY` is the single catalog; Mem0 only sees name/description/when-to-use), then give it to an agent in `crew.py`. Check `crewai_tools` for a built-in before writing a custom one.

## Knowledge (extra context sources)

| Path | What it is | Status |
|---|---|---|
| [knowledge/user_preference.txt](../knowledge/user_preference.txt) | Sample user facts (placeholder persona) | **Not wired in** — no Python code references `knowledge/` |
| [knowledge/system_design.png](../knowledge/system_design.png) | System architecture diagram | Reference image only |
| [tools/api_reference/](../src/shopai/tools/api_reference/) | API docs for tools | Reference for humans/agents |

To feed an agent extra knowledge, use CrewAI `knowledge_sources` (see AGENTS.md → Knowledge System). Real per-user memory comes from Supabase/Mem0, not this folder.

## Evals

| Item | Where |
|---|---|
| Schema (`GoldenExample`, `EvalResult`, `EvalCategory`, Arize row shape) | [src/shopai/evals/schema.py](../src/shopai/evals/schema.py) |
| Golden cases (31, JSONL, one failure mode each) | [src/shopai/evals/golden_examples.jsonl](../src/shopai/evals/golden_examples.jsonl) |

Golden examples mirror the `inputs` dict that `run_master_recommendation` builds, so they can go straight into `kickoff()`. Categories follow the failure-mode taxonomy (validator, clarification, master_recommendation, recommendation, visualization, marketplace, plus planned wardrobe / social_media / shopping_experience_learning). `implemented: false` means the owning code doesn't exist yet. No runner or Arize upload exists yet. Unit tests are in [tests/](../tests/) (`uv run pytest -q`).

## Design references

| Need | Where |
|---|---|
| Product spec, personas, JTBD, AI UX, safety/HITL, metrics, agent designs | [README.md](../README.md) and the Notion spec linked at its bottom |
| System architecture | [knowledge/system_design.png](../knowledge/system_design.png), README → "System Architecture" |
| Why a feature works the way it does | [docs/superpowers/specs/](../docs/superpowers/specs/) (design) and [docs/superpowers/plans/](../docs/superpowers/plans/) (implementation plans): Phoenix/CrewAI telemetry, master-agent clarity routing |
| Android UI tokens | [ui/theme/](../src/shopai/mobile/app/src/main/java/com/shopai/android/ui/theme/) — brand red `#C8102E`, background `#F5F5F7`. No Figma link in the repo |

## Run & gotchas

- Env: copy `.env.example` → `.env`. Env vars set in the shell **override** `.env`.
- Local Ollama: `LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama MODEL=Qwen3:latest uv run run_api`. Qwen3 8B is slow (~9 min for a real prompt) and often returns no structured plan.
- A greeting like "hi" is answered by the guardrail instantly (`out_of_scope`) — it proves routing, not the model.
- Android emulator: `API_BASE_URL` in `src/shopai/mobile/local.properties` must be `http://10.0.2.2:8000/` (`localhost` is the emulator itself). It is baked in at build time — rebuild with `./gradlew installDebug`. Physical phone: `localhost` + `adb reverse tcp:8000 tcp:8000`. The app's read timeout is 120 s.
- A not-ready request costs one extra LLM call (~25-45 s on Qwen3 8B); a high keyword score skips it. If the agent fails, `source: "fallback"` in the clarity result means the keyword scorer answered.
- Never commit `.env` or `local.properties`.
