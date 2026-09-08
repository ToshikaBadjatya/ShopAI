# Clarity Scoring and Workflow Routing for the Recommendation Master

## Purpose

Give the Recommendation Master a way to tell a well-specified request from a
vague one, and route each to a workflow that suits it.

Today every in-scope request takes the same path, and a request too vague to
plan with is refused outright by the guardrail — the user is told "I cannot
understand your request" and the conversation ends. That is the wrong answer
for someone who genuinely wants help but does not yet know what to ask for.

After this change, a request is scored on how clearly it specifies five
styling dimensions and routed to one of three workflows:

| Score  | Workflow             | What it does                                     |
|--------|----------------------|--------------------------------------------------|
| High   | Plan                 | The existing recommendation → review → visualize |
| Medium | Scope Clarification  | Narrows a request that has a goal but few specifics |
| Low    | Personal Style       | Discovers the user's style from scratch           |

## Scope

In scope:

- A deterministic clarity score over five dimensions.
- One new clarification agent, and master-agent routing between three workflows.
- A SQL conversation table holding the turn-by-turn transcript.
- Context-usage-triggered compaction of conversation memory.
- Multi-turn continuation of a run, so a vague request can climb Low → Medium → High.

Out of scope:

- Changing what the High/Plan workflow itself does. It runs exactly as it does today.
- Persisting the Personal Style flow's findings into `user_memory`. The flow may
  write there later; scoring never reads it (see Decisions).
- Any client/Android work beyond the two API field additions below.

## Decisions

Each of these was chosen deliberately; the rejected alternative is noted
because the reasoning matters more than the choice.

1. **The guardrail routes rather than rejects.** `validate_request` keeps
   refusing `not_allowed` and `out_of_scope`, but its `needs_clarification`
   branch stops being a rejection. That verdict becomes an input to scoring.
   Without this, the Low tier is unreachable — the guardrail already rejects
   precisely the requests the Personal Style flow exists to serve.

2. **Scoring is weighted and deterministic.** Keyword vocabularies, no LLM, no
   network — matching every existing validation tool, which the module docstring
   describes as "deliberately deterministic … so the agent spends its own
   reasoning on the judgement call rather than on lookups." It is free, instant,
   and testable without a model.

3. **The master agent routes, not Python.** The score and its evidence are
   passed into the master's prompt; it decides what runs and records the choice
   in the task ledger it already has. This keeps one delegation pattern across
   all workflows. The cost is that routing is non-deterministic — an agent
   handed a score can ignore it (see Risks).

   With a single clarification agent, routing is really two decisions, not one:
   *which* path (plan vs. clarify), and for the clarify path, *which tier* the
   agent is told it is serving. The second is the easier one to get wrong,
   because both tiers reach the same agent and nothing structural distinguishes
   them — only the context handed over.

4. **Scoring reads the request text only.** Not `user_memory`. A returning user
   with a rich profile is scored on what they actually said this run. Within a
   run the scored text still grows, because it is every user turn so far
   concatenated — that is how a run climbs tiers.

5. **No separate transcript store.** `ConversationMemory` owns both sides: the
   SQL turns and the Mem0 summary. A second store class for the same concept
   would split one responsibility across two files.

## Vocabulary split

`validation_tools.py` is 376 lines doing four jobs: vocabularies, tools, a
runtime registry, and the verdict function. The term sets are now needed by a
second caller, so they move to a new `src/shopai/vocabulary.py`, which
`validation_tools.py` imports — its public names stay importable exactly as
they are today.

Two new sets are added there:

- **`GARMENT_TERMS`** — actual pieces: dress, saree, kurta, blazer, jeans,
  heels, lehenga. Carved out of the current `FASHION_TERMS`.
- **`ACCESSORY_TERMS`** — bag, clutch, tote, jewellery, watch, belt, scarf,
  sunglasses, dupatta.

This split is load-bearing, not tidying. `FASHION_TERMS` currently contains
`style`, `styling`, `fashion`, `wardrobe`, `shop`, `budget` and `price`
alongside real garments. If the outfit-type dimension read from it, *"help me
with my style"* — the canonical Personal Style request — would match `style`
and score Medium, entering the wrong workflow.

## The clarity score

New module `src/shopai/clarity.py`. Pure, deterministic, no I/O.

| Dimension   | Weight | Vocabulary          |
|-------------|--------|---------------------|
| event       | 2      | `EVENT_TERMS`       |
| outfit type | 2      | `GARMENT_TERMS`     |
| colors      | 1      | `COLOR_TERMS`       |
| silhouette  | 1      | `SILHOUETTE_TERMS`  |
| accessories | 1      | `ACCESSORY_TERMS`   |

A dimension scores its full weight when the text contains at least one of its
terms, and zero otherwise. Event and outfit type carry double because the
existing guardrail already treats that pair as the blocking one — a request
missing both is not plannable regardless of how much colour detail it carries.

Total is 7. Thresholds:

- **High** — 5 or more
- **Medium** — 2 to 4
- **Low** — 0 or 1

Worked examples:

| Request | Dimensions hit | Total | Tier |
|---|---|---|---|
| "black fitted midi dress for a cocktail party with gold jewellery" | all five | 7 | High |
| "navy saree for my cousin's sangeet" | event, outfit type, colors | 5 | High |
| "wedding guest dress" | event, outfit type | 4 | Medium |
| "something nice for Diwali" | event | 2 | Medium |
| "I want something in pastels" | colors | 1 | Low |
| "help me with my style" | none | 0 | Low |

The function returns the tier alongside its evidence — which dimensions were
present, which were missing, and the matched terms — because the master agent
needs the evidence to ask a sensible follow-up, not just the label.

## Conversation storage

### The turns table

New migration `supabase/migrations/0002_conversation.sql`:

| Column       | Type          | Notes                                      |
|--------------|---------------|--------------------------------------------|
| `id`         | uuid          | primary key, `gen_random_uuid()`           |
| `run_id`     | uuid          | groups the turns of one conversation       |
| `user_id`    | uuid          | references `auth.users(id)` on delete cascade |
| `sender`     | text          | check constraint: `'user'` or `'agent'`    |
| `message`    | text          | the turn, verbatim                         |
| `created_at` | timestamptz   | default `now()`                            |

Indexed on `(run_id, created_at)` — every read is "this run's turns, in order".

Row level security mirrors `user_memory` exactly: four policies confining
select/insert/update/delete to `auth.uid() = user_id`. The server holds no
privileged key, so a caller without a token reaches nothing.

### What ConversationMemory becomes

`ConversationMemory` gains the SQL side alongside its existing Mem0 side:

- `append(user_id, run_id, sender, message)` — record one turn.
- `history(run_id)` — the run's turns, oldest first.
- `user_text(run_id)` — every user turn concatenated. This is what the clarity
  score reads.

Its Mem0 side keeps doing what it does now, reframed to its actual job: holding
the *summary*, not the transcript. The raw turns are the SQL table's
responsibility.

A useful consequence: because scoring reads the SQL turns, compaction can never
degrade the clarity score. Compaction shrinks what is carried into the model's
context; it does not touch the record being scored.

## Context-triggered compaction

`MODEL_TOKEN_LIMITS` and `calculate_context_usage()` go in `src/shopai/llm.py`,
where the model wiring already lives — they are facts about models, not about
conversations:

```python
def calculate_context_usage(context: str, model: str = "gpt-5-mini") -> dict:
    """Calculate context window usage as percentage."""
    estimated_tokens = len(context) // 4  # ~4 chars per token
    max_tokens = MODEL_TOKEN_LIMITS.get(model, 128000)
    percentage = (estimated_tokens / max_tokens) * 100
    return {"tokens": estimated_tokens, "max": max_tokens, "percent": round(percentage, 1)}
```

`MAX_CONVERSATION_CONTEXT` lives in `conversation_memory.py` — it is that
store's policy, not a property of any model. It is a **percentage**: compaction
fires once `calculate_context_usage(...)["percent"]` reaches it. A percentage
rather than an absolute token count because `MODEL` is currently `auto` — a
gateway picks the model per call, so the limits lookup falls through to the
128000 default and any hand-tuned token figure would be guesswork.

**What gets measured is the Mem0 memories, joined — not the SQL turns.** This
matters: compaction shrinks the Mem0 side and never deletes a SQL row, so
measuring the transcript would mean the figure only ever grows. The trigger
would cross its threshold once and then fire on every subsequent turn forever,
re-summarising an already-summarised conversation. Measuring what compaction
actually shrinks makes the reading drop after a fold, which is what lets the
trigger settle.

This replaces the current trigger. `compact()` today fires on a fixed count
(`len(memories) > DEFAULT_KEEP_RECENT`); it will fire on measured usage
instead. What compaction *does* is unchanged: older turns fold into one dense
summary, the most recent turns stay verbatim, and the folded originals are
deleted. Recent detail is the most useful and the cheapest to keep.

## Routing and the clarification agent

`run_master_recommendation` scores `conversation.user_text(run_id)` and passes
the tier and its evidence into the crew inputs. The master agent's task
description states the mapping explicitly and instructs it to record the chosen
path in the task ledger.

**One** new agent joins `agents.yaml`, with role, goal and backstory in the
style of the existing entries, and its task config in `tasks.yaml`:

- **`clarification_agent`** — serves both the Medium and Low tiers. The tier it
  is handed decides how it works, not which agent runs:
  - **Medium (Scope Clarification)** — the request has a discernible goal but
    too few specifics. It asks about the missing dimensions the score
    identified, one useful question at a time.
  - **Low (Personal Style)** — there is no discernible goal yet. It discovers
    how the user likes to dress, rather than interrogating them about a request
    they have not really made.

It joins the hierarchical crew, so the master delegates to it exactly as it
delegates to recommendation, review and visualize.

The two tiers stay distinct as *workflows* — they ask different things and
mean different things — but they are one agent doing both jobs, so the tier
and the missing dimensions must reach it as task context. Its backstory has to
carry both missions without blurring them: narrowing a request it already has
is a different job from finding out who someone is.

## Turn lifecycle

Every call to `/outfit/plan/*`:

1. Append the user's message to the conversation table.
2. Run the guardrail. `not_allowed` and `out_of_scope` still return an error
   envelope and stop here.
3. Score the run's accumulated user text.
4. Run the master crew with the tier and evidence in its inputs.
5. Append the agent's reply to the conversation table.
6. Compact if context usage has crossed `MAX_CONVERSATION_CONTEXT`.

## API changes

- `PlanRequest` gains `runId: Optional[str]`. Absent means a new run; present
  continues one, which is what makes a run climb tiers across turns.
- `PlanResponse` returns `runId`, so the client can send it back.
- High yields `kind="plan"` as today. Medium and Low yield `kind="message"`
  carrying the question — a shape the response model already supports.

## Testing

- **Scoring** — table-driven over the worked examples above plus the
  `FASHION_TERMS` trap (*"help me with my style"* must score Low, not Medium).
  No LLM, no network.
- **Vocabulary split** — `validation_tools`' existing public names still import
  and `validate_request` behaves identically for safety and scope cases.
- **Guardrail** — a vague but safe request now passes instead of returning
  `needs_clarification`.
- **Conversation store** — `append`/`history`/`user_text` against a mocked
  Supabase client, in the style of the existing memory tests.
- **Compaction trigger** — `calculate_context_usage` maths, and that compaction
  fires at the threshold rather than at a turn count.
- **Routing inputs** — the master crew receives the tier the score produced.

## Risks

- **Non-deterministic routing.** Decision 3 puts the branch inside an agent, so
  a run can take the wrong workflow despite a correct score. The ledger record
  makes this visible after the fact. If it proves unreliable, moving the branch
  into Python is a contained change — the score and the three workflows stay
  as they are.
- **Medium and Low can blur.** One agent serves both, so nothing structural
  keeps them apart — only the tier passed as context and a backstory carrying
  two missions. The failure mode is quiet: a Low user gets interrogated about a
  request they never made, or a Medium user is taken back through style
  discovery they did not need. The ledger should record the tier the agent was
  handed, so this is auditable rather than invisible.
- **`MEM0_API_KEY` is not configured.** It is absent from `.env`, so
  `ConversationMemory`'s Mem0 side raises today. The SQL side and scoring do not
  depend on it, so the tiers and routing work without it, but summarisation will
  not run until the key is set.
- **Token estimation is approximate.** `len(context) // 4` is a heuristic, and
  with `MODEL=auto` the window is a 128000 assumption. Both are deliberate:
  the threshold is a trigger for compaction, not a hard limit anything enforces.
