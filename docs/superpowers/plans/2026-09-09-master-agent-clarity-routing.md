# Clarity Scoring and Workflow Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score every incoming request on how clearly it specifies five styling dimensions, and route High/Medium/Low to three different workflows instead of refusing vague requests.

**Architecture:** A deterministic keyword scorer (no LLM, no network) reads the run's accumulated user turns from a new SQL conversation table and produces a tier plus evidence. That tier is passed into the Recommendation Master's prompt, and the master delegates: High to the existing recommendation → review → visualize path, Medium and Low to a single new clarification agent that behaves differently per tier. Conversation memory keeps the Mem0 summary and compacts when measured context usage crosses a threshold.

**Tech Stack:** Python 3.12, CrewAI 1.14.5a2, FastAPI, Pydantic v2, Supabase (Postgres + RLS), Mem0, pytest.

**Spec:** `docs/superpowers/specs/2026-09-06-master-agent-clarity-routing-design.md`

## Global Constraints

- Scoring must stay deterministic — no LLM call, no network I/O, no reads of `user_memory`. It reads request text only.
- `validate_request` keeps refusing `not_allowed` and `out_of_scope`. Only its `needs_clarification` rejection is removed.
- Every existing public name in `validation_tools.py` must remain importable after the vocabulary split — `crew.py` imports `validate_request` from it.
- The new SQL table's RLS mirrors `user_memory` exactly: four policies keyed on `auth.uid() = user_id`. The server holds no privileged key.
- `MAX_CONVERSATION_CONTEXT` is a **percentage**, not a token count.
- Context usage is measured over the **Mem0 memories**, never the SQL turns. SQL rows are never deleted, so measuring them would make the trigger fire forever once crossed.
- One clarification agent serves both Medium and Low. The tier reaches it as task context.
- Run tests with `uv run pytest`.

---

### Task 1: Split vocabularies out, add garment and accessory sets

**Files:**
- Create: `src/shopai/vocabulary.py`
- Modify: `src/shopai/tools/validation_tools.py:19-116`
- Test: `tests/test_vocabulary.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `COLOR_TERMS`, `SILHOUETTE_TERMS`, `EVENT_TERMS`, `VIBE_TERMS`, `GARMENT_TERMS`, `ACCESSORY_TERMS`, `FASHION_TERMS`, `OCCASION_TERMS`, `OUT_OF_SCOPE_TERMS` — all `set[str]`, importable from `shopai.vocabulary`.

The point of this task is `GARMENT_TERMS`. `FASHION_TERMS` currently contains `style`, `styling`, `fashion`, `wardrobe`, `shop`, `budget` and `price` alongside real garments. If the outfit-type dimension read from it, *"help me with my style"* would match `style` and score Medium — entering Scope Clarification instead of the Personal Style flow it exists for.

Note `outfit` and `look` belong in **neither** new set. They are generic containers, not outfit types: *"I need an outfit"* should score Low.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vocabulary.py
from shopai.vocabulary import (
    ACCESSORY_TERMS,
    COLOR_TERMS,
    EVENT_TERMS,
    FASHION_TERMS,
    GARMENT_TERMS,
    OCCASION_TERMS,
    SILHOUETTE_TERMS,
)


def test_garment_terms_are_actual_pieces():
    assert {"dress", "saree", "blazer", "jeans", "heels"} <= GARMENT_TERMS


def test_garment_terms_exclude_meta_shopping_words():
    """The trap this split exists for: 'help me with my style' must not read
    as an outfit type."""
    for meta in ("style", "styling", "fashion", "wardrobe", "shop", "budget", "price"):
        assert meta not in GARMENT_TERMS


def test_generic_containers_are_not_garments():
    """'I need an outfit' names no outfit type."""
    assert "outfit" not in GARMENT_TERMS
    assert "look" not in GARMENT_TERMS


def test_accessory_terms_cover_the_usual_suspects():
    assert {"bag", "clutch", "jewellery", "watch", "belt", "scarf"} <= ACCESSORY_TERMS


def test_fashion_terms_remains_a_superset():
    """Relevance detection still needs the broad set."""
    assert GARMENT_TERMS <= FASHION_TERMS
    assert ACCESSORY_TERMS <= FASHION_TERMS
    assert COLOR_TERMS <= FASHION_TERMS
    assert SILHOUETTE_TERMS <= FASHION_TERMS
    assert "style" in FASHION_TERMS


def test_occasion_terms_still_built_from_events_and_vibes():
    assert EVENT_TERMS <= OCCASION_TERMS
    assert "office" in OCCASION_TERMS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_vocabulary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shopai.vocabulary'`

- [ ] **Step 3: Create the vocabulary module**

Create `src/shopai/vocabulary.py`. Four of the sets move across unchanged — cut each one from `validation_tools.py` at the exact lines below and paste it in, contents untouched:

| Set | Cut from | Lines |
|---|---|---|
| `COLOR_TERMS` | `validation_tools.py` | 23-34 |
| `SILHOUETTE_TERMS` | `validation_tools.py` | 36-44 |
| `EVENT_TERMS` | `validation_tools.py` | 46-55 |
| `VIBE_TERMS` | `validation_tools.py` | 57-67 |
| `OUT_OF_SCOPE_TERMS` | `validation_tools.py` | 89-94 |

`FASHION_TERMS` (69-84) and `OCCASION_TERMS` (87) are **not** moved verbatim — they are rebuilt below from the new sets. Delete the originals.

The resulting file, with the moved sets in place and the rest written out in full:

```python
"""The word lists ShopAI matches requests against.

Shared by the guardrail (which asks "is this about clothes at all?") and by
clarity scoring (which asks "how specific is it?"). Those two questions want
different granularity, which is why GARMENT_TERMS is narrower than
FASHION_TERMS rather than the same set reused.
"""

COLOR_TERMS = {          # pasted from validation_tools.py:23-34
    "black", "white", "ivory", ...
}
SILHOUETTE_TERMS = {     # pasted from validation_tools.py:36-44
    "silhouette", "silhouettes", "fitted", ...
}
EVENT_TERMS = {          # pasted from validation_tools.py:46-55
    "party", "wedding", "marriage", ...
}
VIBE_TERMS = {           # pasted from validation_tools.py:57-67
    "corporate", "professional", "business", ...
}
OUT_OF_SCOPE_TERMS = {   # pasted from validation_tools.py:89-94
    "weather", "forecast", "temperature", ...
}

# Actual pieces someone wears. Deliberately excludes "outfit" and "look" -
# they name no type, so "I need an outfit" specifies nothing.
GARMENT_TERMS = {
    "dress", "dresses", "shirt", "tshirt", "t-shirt", "top", "tops",
    "jeans", "trousers", "pants", "skirt", "saree", "kurta", "kurti",
    "lehenga", "suit", "blazer", "jacket", "coat", "gown", "jumpsuit",
    "tee", "hoodie", "sweater", "cardigan", "shrug", "waistcoat",
    "trench", "bomber", "camisole", "bodysuit", "salwar", "anarkali",
    "sherwani", "palazzo", "co-ord", "coord",
    "shoes", "heels", "sneakers", "sandals", "boots", "loafers",
    "flats", "mules", "wedges", "juttis", "kolhapuris",
}

ACCESSORY_TERMS = {
    "accessory", "accessories", "bag", "handbag", "clutch", "tote",
    "jewellery", "jewelry", "earrings", "necklace", "bangles", "bracelet",
    "belt", "watch", "scarf", "dupatta", "sunglasses",
}

# The broad set: anything that says a request is about clothes at all,
# including meta words like "style" and "budget" that name no garment.
FASHION_TERMS = {
    "outfit", "outfits", "look", "looks", "style", "styling", "stylish",
    "wear", "wearing", "wardrobe", "fashion", "fit", "size", "colour",
    "color", "fabric", "brand", "shop", "shopping", "buy", "purchase",
    "budget", "price", "sale", "discount", "clothes", "clothing",
    "garment", "garments", "attire", "apparel", "outfitted",
    "ethnic", "western", "denim", "leather", "silk", "satin", "velvet",
    "cotton", "linen", "chiffon", "georgette", "organza", "wool",
    "knit", "lace",
} | COLOR_TERMS | SILHOUETTE_TERMS | GARMENT_TERMS | ACCESSORY_TERMS

# An occasion is an event, or a vibe specific enough to dress for.
OCCASION_TERMS = EVENT_TERMS | VIBE_TERMS | {"office", "work"}
```

- [ ] **Step 4: Point validation_tools at the new module**

In `src/shopai/tools/validation_tools.py`, delete the moved definitions (lines 23-94 and the `OCCASION_TERMS` line at 87) and import them instead. Keep `DISALLOWED_PATTERNS` and `CONTEXT_SLOTS` where they are — they are validation policy, not vocabulary:

```python
from shopai.vocabulary import (
    ACCESSORY_TERMS,
    COLOR_TERMS,
    EVENT_TERMS,
    FASHION_TERMS,
    GARMENT_TERMS,
    OCCASION_TERMS,
    OUT_OF_SCOPE_TERMS,
    SILHOUETTE_TERMS,
    VIBE_TERMS,
)
```

- [ ] **Step 5: Run the full suite to verify nothing regressed**

Run: `uv run pytest -v`
Expected: PASS — all pre-existing tests plus the six new ones. The guardrail's behaviour must be identical at this point; only where the words live has changed.

- [ ] **Step 6: Commit**

```bash
git add src/shopai/vocabulary.py src/shopai/tools/validation_tools.py tests/test_vocabulary.py
git commit -m "refactor: split vocabularies out, add garment and accessory sets"
```

---

### Task 2: The clarity score

**Files:**
- Create: `src/shopai/clarity.py`
- Test: `tests/test_clarity.py`

**Interfaces:**
- Consumes: `shopai.vocabulary` sets from Task 1.
- Produces: `score_request(text: str) -> dict` returning
  `{"tier": "high"|"medium"|"low", "score": int, "max_score": 7, "present": list[str], "missing": list[str], "matched": dict[str, list[str]]}`.
  `DIMENSION_WEIGHTS: dict[str, int]`, `HIGH_THRESHOLD: int`, `MEDIUM_THRESHOLD: int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clarity.py
import pytest

from shopai.clarity import score_request


@pytest.mark.parametrize("text,expected_tier", [
    ("black fitted midi dress for a cocktail party with gold jewellery", "high"),
    ("navy saree for my cousin's sangeet", "high"),
    ("wedding guest dress", "medium"),
    ("something nice for Diwali", "medium"),
    ("I want something in pastels", "low"),
    ("help me with my style", "low"),
    ("", "low"),
])
def test_tiers(text, expected_tier):
    assert score_request(text)["tier"] == expected_tier


def test_style_does_not_count_as_an_outfit_type():
    """The FASHION_TERMS trap: 'style' is a meta word, not a garment."""
    result = score_request("help me with my style")
    assert "outfit_type" in result["missing"]
    assert result["score"] == 0


def test_event_and_outfit_type_are_weighted_double():
    event_only = score_request("for a wedding")
    color_only = score_request("in navy")
    assert event_only["score"] == 2
    assert color_only["score"] == 1


def test_returns_evidence_not_just_a_label():
    """The clarification agent needs to know what's missing to ask about it."""
    result = score_request("wedding guest dress")
    assert set(result["present"]) == {"event", "outfit_type"}
    assert set(result["missing"]) == {"colors", "silhouette", "accessories"}
    assert "wedding" in result["matched"]["event"]


def test_a_full_request_scores_the_maximum():
    result = score_request(
        "black fitted midi dress for a cocktail party with gold jewellery"
    )
    assert result["score"] == 7
    assert result["missing"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_clarity.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shopai.clarity'`

- [ ] **Step 3: Write the implementation**

```python
# src/shopai/clarity.py
"""How clearly did the user say what they want?

Five dimensions, keyword-matched. Deterministic on purpose - it costs nothing,
runs in microseconds, and is testable without a model, which matters because
the score decides which of three workflows a request enters.

Event and outfit type carry double weight: the guardrail already treats that
pair as the blocking one, since a request missing both is not plannable however
much colour detail it carries.
"""

import re

from shopai.vocabulary import (
    ACCESSORY_TERMS,
    COLOR_TERMS,
    EVENT_TERMS,
    GARMENT_TERMS,
    SILHOUETTE_TERMS,
)

DIMENSION_TERMS = {
    "event": EVENT_TERMS,
    "outfit_type": GARMENT_TERMS,
    "colors": COLOR_TERMS,
    "silhouette": SILHOUETTE_TERMS,
    "accessories": ACCESSORY_TERMS,
}

DIMENSION_WEIGHTS = {
    "event": 2,
    "outfit_type": 2,
    "colors": 1,
    "silhouette": 1,
    "accessories": 1,
}

MAX_SCORE = sum(DIMENSION_WEIGHTS.values())  # 7

HIGH_THRESHOLD = 5
MEDIUM_THRESHOLD = 2


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z'-]*", text.lower()))


def score_request(text: str) -> dict:
    """Rate a request's clarity and say what it was rated on.

    The evidence matters as much as the tier: the clarification agent asks
    about `missing`, so a bare label would not be enough to act on.
    """
    words = _words(text)

    matched = {
        dimension: sorted(words & terms)
        for dimension, terms in DIMENSION_TERMS.items()
    }
    present = [d for d, hits in matched.items() if hits]
    missing = [d for d in DIMENSION_TERMS if d not in present]
    score = sum(DIMENSION_WEIGHTS[d] for d in present)

    if score >= HIGH_THRESHOLD:
        tier = "high"
    elif score >= MEDIUM_THRESHOLD:
        tier = "medium"
    else:
        tier = "low"

    return {
        "tier": tier,
        "score": score,
        "max_score": MAX_SCORE,
        "present": present,
        "missing": missing,
        "matched": {d: hits for d, hits in matched.items() if hits},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_clarity.py -v`
Expected: PASS — all 12 parametrised and standalone cases.

- [ ] **Step 5: Commit**

```bash
git add src/shopai/clarity.py tests/test_clarity.py
git commit -m "feat: add deterministic clarity scoring over five styling dimensions"
```

---

### Task 3: Stop the guardrail rejecting vague requests

**Files:**
- Modify: `src/shopai/tools/validation_tools.py:359-366`
- Test: `tests/test_validation_routing.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `validate_request(prompt)` returns `allowed=True` for safe, in-scope but vague requests. Its `findings["incomplete_context"]` is unchanged and still populated.

Today a request missing `garment` or `occasion` returns `needs_clarification` and the user is told "I cannot understand your request." That is exactly the Low tier's audience, so the rejection has to go — otherwise the Personal Style flow is unreachable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validation_routing.py
from shopai.tools.validation_tools import validate_request


def test_vague_but_safe_request_now_passes():
    """This used to be rejected as needs_clarification. It is the Low tier."""
    result = validate_request("help me with my style")
    assert result["allowed"] is True
    assert result["rejection"] == ""


def test_incomplete_context_finding_is_still_reported():
    """Removed as a rejection, kept as evidence."""
    result = validate_request("help me with my style")
    assert "incomplete_context" in result["findings"]
    assert result["findings"]["incomplete_context"]["sufficient"] is False


def test_unsafe_request_is_still_refused():
    result = validate_request("where do I buy a gun")
    assert result["allowed"] is False
    assert result["rejection"] == "not_allowed"


def test_out_of_scope_request_is_still_refused():
    result = validate_request("write me some python to debug this stock ticker")
    assert result["allowed"] is False
    assert result["rejection"] == "out_of_scope"


def test_empty_request_is_still_refused():
    result = validate_request("   ")
    assert result["allowed"] is False
    assert result["rejection"] == "needs_clarification"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validation_routing.py -v`
Expected: FAIL on the first two tests — `assert False is True`, because the incomplete-context branch still rejects.

- [ ] **Step 3: Remove the rejection branch**

In `validate_request`, delete this block (currently lines 359-366):

```python
    context = findings.get("incomplete_context", {})
    if not context.get("sufficient", False):
        missing = ", ".join(context.get("missing", [])) or "details"
        return blocked(
            "needs_clarification",
            f"Not enough to plan with yet - missing {missing}.",
            context.get("suggested_question") or "Could you tell me a bit more?",
        )
```

Leave the empty-prompt check above it alone — an empty string is not a vague request, it is no request. Then update the docstring's description of what the guardrail decides:

```python
    """Run every registered check and answer one question: does this pass?

    The guardrail no longer names what a request is, nor whether it is specific
    enough - both judgements belong downstream. A vague request is not refused
    here; it is scored by `shopai.clarity` and routed to a workflow that can
    handle vagueness. All this decides is safety and scope.
    """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validation_routing.py -v`
Expected: PASS — all five.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS. If a pre-existing test asserted the old rejection, update it to reflect the new contract rather than reinstating the branch.

- [ ] **Step 6: Commit**

```bash
git add src/shopai/tools/validation_tools.py tests/test_validation_routing.py
git commit -m "feat: guardrail no longer rejects vague requests, only unsafe and out-of-scope"
```

---

### Task 4: Context usage measurement

**Files:**
- Modify: `src/shopai/llm.py`
- Test: `tests/test_context_usage.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `calculate_context_usage(context: str, model: str = "gpt-5-mini") -> dict` returning `{"tokens": int, "max": int, "percent": float}`, and `MODEL_TOKEN_LIMITS: dict[str, int]`.

These are facts about models, so they live beside the model wiring. The threshold that uses them is conversation policy and lives elsewhere (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context_usage.py
from shopai.llm import MODEL_TOKEN_LIMITS, calculate_context_usage


def test_estimates_four_characters_per_token():
    result = calculate_context_usage("x" * 4000, model="gpt-4o")
    assert result["tokens"] == 1000


def test_percent_is_relative_to_the_model_window():
    result = calculate_context_usage("x" * 4000, model="gpt-4o")
    assert result["max"] == MODEL_TOKEN_LIMITS["gpt-4o"]
    assert result["percent"] == round((1000 / 128000) * 100, 1)


def test_unknown_model_falls_back_to_128k():
    """MODEL is 'auto' in this project - a gateway picks per call."""
    result = calculate_context_usage("x" * 4000, model="auto")
    assert result["max"] == 128000


def test_empty_context_is_zero_percent():
    assert calculate_context_usage("")["percent"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_context_usage.py -v`
Expected: FAIL with `ImportError: cannot import name 'MODEL_TOKEN_LIMITS'`

- [ ] **Step 3: Add the implementation to llm.py**

Append to `src/shopai/llm.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_context_usage.py -v`
Expected: PASS — all four.

- [ ] **Step 5: Commit**

```bash
git add src/shopai/llm.py tests/test_context_usage.py
git commit -m "feat: add context window usage estimation"
```

---

### Task 5: The conversation table and its store

**Files:**
- Create: `supabase/migrations/0002_conversation.sql`
- Modify: `src/shopai/memory/conversation_memory.py`
- Test: `tests/test_conversation_sql.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: on `ConversationMemory` —
  `append(run_id: str, sender: str, message: str, *, access_token: str) -> dict`,
  `history(run_id: str, *, access_token: str) -> list[dict]`,
  `user_text(run_id: str, *, access_token: str) -> str`.
  Also `CONVERSATION_TABLE: str`.

The store needs an access token per call for the same reason `UserInfoMemory` does: RLS means Postgres decides what the caller can see, and the server holds no privileged key.

- [ ] **Step 1: Write the migration**

Create `supabase/migrations/0002_conversation.sql`:

```sql
-- Conversation turns: the verbatim transcript of one run.
-- Mem0 holds the summary; this holds what was actually said.
--
-- Apply by pasting into the Supabase SQL editor (Dashboard -> SQL Editor).

create table if not exists public.conversation (
    id         uuid        primary key default gen_random_uuid(),
    run_id     uuid        not null,
    user_id    uuid        not null references auth.users (id) on delete cascade,
    sender     text        not null check (sender in ('user', 'agent')),
    message    text        not null,
    created_at timestamptz not null default now()
);

comment on table public.conversation is
    'Turn-by-turn transcript, one row per message. Clarity scoring reads the user turns.';

-- Every read is "this run's turns, in order".
create index if not exists conversation_run_created_idx
    on public.conversation (run_id, created_at);

alter table public.conversation enable row level security;

drop policy if exists "conversation_select_own" on public.conversation;
create policy "conversation_select_own" on public.conversation
    for select using (auth.uid() = user_id);

drop policy if exists "conversation_insert_own" on public.conversation;
create policy "conversation_insert_own" on public.conversation
    for insert with check (auth.uid() = user_id);

drop policy if exists "conversation_update_own" on public.conversation;
create policy "conversation_update_own" on public.conversation
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "conversation_delete_own" on public.conversation;
create policy "conversation_delete_own" on public.conversation
    for delete using (auth.uid() = user_id);
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_conversation_sql.py
from unittest.mock import MagicMock, patch

import pytest

from shopai.memory.conversation_memory import ConversationMemory


def _mock_supabase(rows):
    client = MagicMock()
    chain = client.table.return_value
    chain.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows
    chain.insert.return_value.execute.return_value.data = rows
    return client


def test_append_writes_a_row_scoped_to_the_user_and_run():
    client = _mock_supabase([{"id": "1"}])
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        ConversationMemory().append(
            "run-1", "user", "wedding guest dress", access_token="tok"
        )

    client.table.assert_called_with("conversation")
    inserted = client.table.return_value.insert.call_args[0][0]
    assert inserted["run_id"] == "run-1"
    assert inserted["sender"] == "user"
    assert inserted["message"] == "wedding guest dress"


def test_append_rejects_an_unknown_sender():
    """The column has a check constraint; fail before the round trip."""
    with pytest.raises(ValueError, match="sender"):
        ConversationMemory().append("run-1", "robot", "hi", access_token="tok")


def test_history_returns_turns_oldest_first():
    rows = [
        {"sender": "user", "message": "wedding guest dress"},
        {"sender": "agent", "message": "What colours do you like?"},
    ]
    client = _mock_supabase(rows)
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        turns = ConversationMemory().history("run-1", access_token="tok")

    assert [t["message"] for t in turns] == [
        "wedding guest dress",
        "What colours do you like?",
    ]


def test_user_text_joins_only_the_user_turns():
    """This is what clarity scoring reads - the agent's questions must not
    inflate the score with words the user never said."""
    rows = [
        {"sender": "user", "message": "wedding guest dress"},
        {"sender": "agent", "message": "Any colours in mind? Navy? Emerald?"},
        {"sender": "user", "message": "something in navy"},
    ]
    client = _mock_supabase(rows)
    with patch("shopai.memory.conversation_memory.create_client", return_value=client):
        text = ConversationMemory().user_text("run-1", access_token="tok")

    assert text == "wedding guest dress\nsomething in navy"
    assert "Emerald" not in text


def test_requires_an_access_token():
    with pytest.raises(RuntimeError, match="access token"):
        ConversationMemory().history("run-1", access_token="")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_conversation_sql.py -v`
Expected: FAIL with `AttributeError: 'ConversationMemory' object has no attribute 'append'`

- [ ] **Step 4: Add the SQL side to ConversationMemory**

Add to the imports in `src/shopai/memory/conversation_memory.py`:

```python
from supabase import Client, create_client
```

Add the module-level helpers and constants:

```python
CONVERSATION_TABLE = "conversation"

SENDERS = {"user", "agent"}


def _supabase(access_token: str) -> Client:
    """A client acting as the user - RLS decides what it can reach."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
        )
    if not access_token:
        raise RuntimeError("An access token is required: conversations are per-user.")

    client = create_client(url, key)
    client.postgrest.auth(access_token)
    return client
```

Then the three methods on `ConversationMemory`, under a new section heading:

```python
    # ------------------------------------------------------- the transcript
    #
    # Mem0 above holds the summary; these hold what was actually said. Scoring
    # reads the turns rather than the summary, so compaction can never change
    # a run's clarity score.

    def append(self, run_id: str, sender: str, message: str, *, access_token: str) -> dict:
        """Record one turn."""
        if sender not in SENDERS:
            raise ValueError(f"Unknown sender '{sender}'. Use one of: {', '.join(sorted(SENDERS))}.")

        user_id = user_id_from_token(access_token)
        result = (
            _supabase(access_token)
            .table(CONVERSATION_TABLE)
            .insert({
                "run_id": run_id,
                "user_id": user_id,
                "sender": sender,
                "message": message,
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    def history(self, run_id: str, *, access_token: str) -> list[dict]:
        """Every turn in this run, oldest first."""
        result = (
            _supabase(access_token)
            .table(CONVERSATION_TABLE)
            .select("*")
            .eq("run_id", run_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def user_text(self, run_id: str, *, access_token: str) -> str:
        """Every user turn joined - what clarity scoring reads.

        The agent's own turns are excluded deliberately: a question listing
        colour options would otherwise score as the user having named colours.
        """
        turns = self.history(run_id, access_token=access_token)
        return "\n".join(t["message"] for t in turns if t.get("sender") == "user")
```

Import `user_id_from_token` at the top:

```python
from shopai.memory.user_memory import user_id_from_token
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_conversation_sql.py -v`
Expected: PASS — all five.

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/0002_conversation.sql src/shopai/memory/conversation_memory.py tests/test_conversation_sql.py
git commit -m "feat: add conversation transcript table and store"
```

---

### Task 6: Compact on context usage instead of turn count

**Files:**
- Modify: `src/shopai/memory/conversation_memory.py` (`compact`, and the constants near line 24)
- Test: `tests/test_compaction_trigger.py`

**Interfaces:**
- Consumes: `calculate_context_usage` from Task 4.
- Produces: `MAX_CONVERSATION_CONTEXT: int` (a percentage). `compact()` keeps its existing signature and return shape.

`compact()` today fires when `len(memories) > keep_recent`. It should fire on measured usage instead. What it *does* is unchanged: old turns fold into one summary, recent ones stay verbatim.

Measure over the **Mem0 memories**, not the SQL turns. Compaction shrinks the Mem0 set and never deletes a SQL row, so measuring the transcript would mean the figure only ever grows — crossing once and then re-summarising forever.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compaction_trigger.py
from unittest.mock import MagicMock, patch

from shopai.memory.conversation_memory import MAX_CONVERSATION_CONTEXT, ConversationMemory


def _memories(count, size):
    return [{"id": str(i), "memory": "x" * size} for i in range(count)]


def test_below_the_threshold_nothing_is_compacted():
    memory = ConversationMemory()
    with patch.object(memory, "expand_conversation") as expand:
        expand.return_value = {"memories": _memories(50, 10)}
        result = memory.compact("user-1", "run-1")

    assert result["compacted"] is False
    assert "context" in result["reason"].lower()


def test_crossing_the_threshold_triggers_compaction():
    """Enough text to exceed MAX_CONVERSATION_CONTEXT percent of 128000 tokens."""
    chars_for_full_window = 128000 * 4
    oversized = int(chars_for_full_window * (MAX_CONVERSATION_CONTEXT / 100)) + 4000

    memory = ConversationMemory()
    client = MagicMock()
    with patch.object(memory, "expand_conversation") as expand, \
         patch("shopai.memory.conversation_memory._client", return_value=client), \
         patch("shopai.memory.conversation_memory.default_llm") as llm:
        expand.return_value = {"memories": _memories(20, oversized // 20)}
        llm.return_value.call.return_value = "A dense summary."
        result = memory.compact("user-1", "run-1")

    assert result["compacted"] is True
    assert result["summary"] == "A dense summary."
    assert client.delete.called


def test_compaction_keeps_the_most_recent_turns_verbatim():
    chars_for_full_window = 128000 * 4
    oversized = int(chars_for_full_window * (MAX_CONVERSATION_CONTEXT / 100)) + 4000

    memory = ConversationMemory()
    with patch.object(memory, "expand_conversation") as expand, \
         patch("shopai.memory.conversation_memory._client", return_value=MagicMock()), \
         patch("shopai.memory.conversation_memory.default_llm") as llm:
        expand.return_value = {"memories": _memories(20, oversized // 20)}
        llm.return_value.call.return_value = "A dense summary."
        result = memory.compact("user-1", "run-1", keep_recent=6)

    assert result["kept_count"] == 6
    assert result["folded_count"] == 14


def test_threshold_is_a_percentage():
    assert 0 < MAX_CONVERSATION_CONTEXT <= 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_compaction_trigger.py -v`
Expected: FAIL with `ImportError: cannot import name 'MAX_CONVERSATION_CONTEXT'`

- [ ] **Step 3: Add the threshold and change the trigger**

Add the import and constant near the existing `DEFAULT_KEEP_RECENT` (line 24) in `conversation_memory.py`:

```python
from shopai.llm import calculate_context_usage, default_llm

# Compact once the conversation fills this share of the model's context window.
# A percentage rather than a token count because MODEL is "auto" here - a
# gateway picks per call, so any hand-tuned token figure would be guesswork.
MAX_CONVERSATION_CONTEXT = 80
```

(`default_llm` is already imported; extend that line rather than duplicating it.)

Then replace the early-return in `compact()`. The current block is:

```python
        if len(memories) <= keep_recent:
            return {
                "run_id": run_id,
                "user_id": user_id,
                "compacted": False,
                "reason": "Nothing old enough to compact.",
                "memory_count": len(memories),
            }
```

Replace with a usage check:

```python
        # Measured over the memories, not the SQL turns: compaction shrinks
        # this set and never deletes a transcript row, so measuring the
        # transcript would climb forever and re-fire on every turn.
        joined = "\n".join(m.get("memory", m.get("text", "")) for m in memories)
        usage = calculate_context_usage(joined)

        if usage["percent"] < MAX_CONVERSATION_CONTEXT or len(memories) <= keep_recent:
            return {
                "run_id": run_id,
                "user_id": user_id,
                "compacted": False,
                "reason": (
                    f"Context usage {usage['percent']}% is below the "
                    f"{MAX_CONVERSATION_CONTEXT}% threshold."
                ),
                "memory_count": len(memories),
                "context_percent": usage["percent"],
            }
```

The `len(memories) <= keep_recent` clause stays as a floor — there is nothing to fold when everything would be kept, whatever the usage says.

Also add `context_percent` to the success return so callers can see what triggered it:

```python
        return {
            "run_id": run_id,
            "user_id": user_id,
            "compacted": True,
            "context_percent": usage["percent"],
            "folded_count": len(to_fold),
            "kept_count": len(to_keep),
            "summary": condensed_text,
            "added": added,
        }
```

Finally update the method docstring's first lines to describe the new trigger:

```python
        """Fold older memories into one dense summary, keep the rest as-is.

        Fires when the conversation fills MAX_CONVERSATION_CONTEXT percent of
        the model's context window - not at a fixed number of turns, since what
        matters is how much room is left, not how many times someone spoke.
        """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_compaction_trigger.py -v`
Expected: PASS — all four.

- [ ] **Step 5: Commit**

```bash
git add src/shopai/memory/conversation_memory.py tests/test_compaction_trigger.py
git commit -m "feat: trigger conversation compaction on context usage, not turn count"
```

---

### Task 7: The clarification agent

**Files:**
- Modify: `src/shopai/config/agents.yaml`
- Modify: `src/shopai/config/tasks.yaml`
- Modify: `src/shopai/crew.py` (add a method beside `review_recommendation_agent`, and extend `recommendation_crew`'s agents list)
- Test: `tests/test_clarification_agent.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Shopai.clarification_agent() -> Agent`, and a `clarification_task` config key.

One agent serves both Medium and Low. The tier decides how it works, not which agent runs — so its backstory has to carry both missions without blurring them, and the tier must arrive as task context.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clarification_agent.py
from shopai.crew import Shopai


def test_clarification_agent_is_configured():
    agent = Shopai().clarification_agent()
    assert agent.role
    assert agent.goal


def test_clarification_agent_joins_the_recommendation_crew():
    crew = Shopai().recommendation_crew("run-1")
    roles = [a.role for a in crew.agents]
    assert any("clarif" in role.lower() for role in roles)


def test_clarification_agent_does_not_delegate():
    """It asks the user; it has no one to hand work to."""
    agent = Shopai().clarification_agent()
    assert agent.allow_delegation is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_clarification_agent.py -v`
Expected: FAIL with `AttributeError: 'Shopai' object has no attribute 'clarification_agent'`

- [ ] **Step 3: Add the agent config**

Append to `src/shopai/config/agents.yaml`:

```yaml
clarification_agent:
  role: >
    Styling Clarifier
  goal: >
    Turn an unclear request into one ShopAI can actually plan against, by
    asking for what is missing from {shopping_request} — or, when there is no
    real request yet, by finding out how this person likes to dress.
  backstory: >
    You do two related jobs, and knowing which one you are on matters more
    than anything else you do.

    When the request has a goal but too few specifics, you narrow it. You are
    told which dimensions are missing — event, outfit type, colour, silhouette,
    accessories — and you ask about the one that would change the answer most.
    One question at a time. You never ask about something they already told you.

    When there is no real request yet — someone who says they want to look
    better, or dress like themselves, but names nothing — you do not
    interrogate them about an outfit they have not asked for. You find out how
    they like to dress: what they reach for, what they own and never wear, who
    they think looks right. That is a conversation, not a form.

    You never guess on the user's behalf and hand a filled-in request
    downstream. An assumption dressed as an answer is worse than the question
    you did not ask.
```

- [ ] **Step 4: Add the task config**

Append to `src/shopai/config/tasks.yaml`:

```yaml
clarification_task:
  description: >
    The request "{shopping_request}" scored {clarity_tier} on clarity.
    Dimensions present: {clarity_present}. Dimensions missing: {clarity_missing}.

    If the tier is medium, narrow the request: ask about the single missing
    dimension that would most change what you would recommend.

    If the tier is low, there is not really a request yet. Do not ask about
    the outfit. Find out how this person likes to dress instead.

    Ask one question. Do not answer it yourself, and do not assume what they
    would have said.
  expected_output: >
    A single question for the user, in plain language, with no preamble and no
    list of options unless the options genuinely narrow the choice.
```

- [ ] **Step 5: Add the agent method and wire it into the crew**

In `src/shopai/crew.py`, add beside `review_recommendation_agent`:

```python
    def clarification_agent(self) -> Agent:
        """Asks the user for what is missing - Medium and Low both land here.

        No delegation: it has no one to hand work to, and a clarifier that
        delegates would be answering its own question.
        """
        return Agent(
            llm=default_llm(),
            config=self.agents_config['clarification_agent'],  # type: ignore[index]
            tools=[],
            allow_delegation=False,
            verbose=True,
        )
```

Then extend the agents list in `recommendation_crew`:

```python
            agents=[
                self.recommendation_agent(),
                self.review_recommendation_agent(),
                self.visualize_agent(),
                self.clarification_agent(),
            ],
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_clarification_agent.py -v`
Expected: PASS — all three.

- [ ] **Step 7: Commit**

```bash
git add src/shopai/config/agents.yaml src/shopai/config/tasks.yaml src/shopai/crew.py tests/test_clarification_agent.py
git commit -m "feat: add clarification agent serving both medium and low tiers"
```

---

### Task 8: Route on the score

**Files:**
- Modify: `src/shopai/crew.py` (`run_master_recommendation`, and the `master_recommendation_task` config)
- Modify: `src/shopai/config/tasks.yaml`
- Test: `tests/test_master_routing.py`

**Interfaces:**
- Consumes: `score_request` (Task 2), `ConversationMemory.user_text` (Task 5), `clarification_agent` (Task 7).
- Produces: `Shopai.run_master_recommendation(prompt, profile=None, run_id=None, access_token="")` returns its existing dict plus `"clarity": {...}` — the full score dict from Task 2.

**Reconciliation note:** `run_master_recommendation` and `master_recommendation_task` already carry a `run_id` addition from a fix that landed between planning and execution — the master already sees `{run_id}` in its prompt so it can name which run it is on (its ledger tools take no run id; they're bound to one at build time). Step 3 and Step 4 below preserve that addition rather than reintroducing the pre-fix version — do not paste either block over what is currently in the file without checking the diff first.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_master_routing.py
from unittest.mock import MagicMock, patch

from shopai.crew import Shopai


def _run(prompt, user_text=None):
    crew = MagicMock()
    crew.kickoff.return_value = "{}"

    # Patch the instance, never the class. @CrewBase's metaclass walks class
    # attributes expecting descriptors during __call__, and a MagicMock raises
    # AttributeError: __get__ - so patch.object(Shopai, ...) fails before your
    # test body ever runs.
    shopai = Shopai()
    with patch.object(shopai, "recommendation_crew", return_value=crew), \
         patch("shopai.crew.memory") as mem:
        mem.conversation.user_text.return_value = user_text if user_text is not None else prompt
        result = shopai.run_master_recommendation(prompt, {}, access_token="tok")
    return result, crew


def test_a_specific_request_scores_high():
    result, _ = _run("black fitted midi dress for a cocktail party with gold jewellery")
    assert result["clarity"]["tier"] == "high"


def test_a_vague_request_scores_low():
    result, _ = _run("help me with my style")
    assert result["clarity"]["tier"] == "low"


def test_the_tier_reaches_the_crew_inputs():
    """The master cannot route on a score it was never handed."""
    _, crew = _run("wedding guest dress")
    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["clarity_tier"] == "medium"
    assert "colors" in inputs["clarity_missing"]


def test_scoring_reads_the_accumulated_run_text_not_just_this_turn():
    """Turn two of a run is scored against everything the user has said."""
    result, _ = _run(
        "something in navy",
        user_text="wedding guest dress\nsomething in navy",
    )
    assert result["clarity"]["tier"] == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_master_routing.py -v`
Expected: FAIL with `KeyError: 'clarity'`

- [ ] **Step 3: Score inside run_master_recommendation**

Add the imports at the top of `src/shopai/crew.py`:

```python
from shopai.clarity import score_request
from shopai.memory import memory
```

Change the signature and body of `run_master_recommendation`:

```python
    def run_master_recommendation(
        self, prompt: str, profile: dict | None = None, run_id: str | None = None,
        access_token: str = "",
    ) -> dict:
        """Hand a request to the Recommendation Master crew.

        The request is scored for clarity first, and the tier goes into the
        crew's inputs - the master routes on it: high runs the plan workflow,
        medium and low go to the clarification agent.

        Scoring reads the run's accumulated user turns rather than this one
        message, which is how a vague request climbs low -> medium -> high as
        the user answers.

        Returns:
            {"recommendations": [...], "summary": "...", "raw": "...",
             "run_id": "...", "clarity": {...}}
        """
        run_id = run_id or str(uuid.uuid4())
        profile = profile or {}
        styles = profile.get("styles") or []

        scored_text = prompt
        if access_token:
            scored_text = memory.conversation.user_text(
                run_id, access_token=access_token
            ) or prompt
        clarity = score_request(scored_text)

        inputs = {
            "shopping_request": prompt,
            "location": "India",
            "budget": "5000 INR",
            "gender": profile.get("gender") or "female",
            "height": profile.get("height") or "5'6\"",
            "body_type": profile.get("bodyType") or "average",
            "style": ", ".join(styles) or "casual",
            # The master sees which run it is on. Its ledger tools are already
            # bound to this id and take no run_id argument, so this is for the
            # agent's own reference - it cannot be used to write elsewhere.
            "run_id": run_id,
            "clarity_tier": clarity["tier"],
            "clarity_present": ", ".join(clarity["present"]) or "none",
            "clarity_missing": ", ".join(clarity["missing"]) or "none",
        }

        raw = str(self.recommendation_crew(run_id).kickoff(inputs=inputs))
        return {
            **self._parse_recommendation_crew_output(raw),
            "run_id": run_id,
            "clarity": clarity,
        }
```

The `run_id` key and its comment are not new — do not omit them. They came from the earlier fix; this step only adds the three `clarity_*` keys alongside them.

- [ ] **Step 4: Tell the master what the tier means**

`master_recommendation_task` in `src/shopai/config/tasks.yaml` already carries a
paragraph from the earlier run-id fix ("You are working on run {run_id}...").
Add the routing rule as a **new paragraph after it** — do not replace the
block, or the run-id paragraph is lost. The full description should read:

```yaml
master_recommendation_task:
  description: >
    Deliver reviewed outfit recommendations for {shopping_request}.
    The user is {gender}, height {height}, body type {body_type}, style
    preference {style}, shopping in {location} with a budget of {budget}.
    Direct the specialists: have the recommendation specialist curate options,
    have the reviewer judge them against fit, occasion and budget, and send work
    back for another pass when the reviewer's objections are material.

    You are working on run {run_id}. Your ledger tools already write to this
    run - they take no run id, so plan and update steps without naming one.

    This request scored {clarity_tier} on clarity. Present: {clarity_present}.
    Missing: {clarity_missing}.

    Route on that score, and record which path you took in the task ledger:

    - high: run the plan workflow. Delegate curation to the recommendation
      specialist, then critique to the reviewer, then imagery to the visualizer.
    - medium: delegate to the Styling Clarifier and tell it the tier is medium
      and which dimensions are missing. Do not curate anything yet.
    - low: delegate to the Styling Clarifier and tell it the tier is low. There
      is no real request yet - it must not be asked about an outfit.

    Never fill in a missing dimension yourself to promote a request to a higher
    tier. A guess recorded as fact is the one failure this routing cannot
    recover from.
  expected_output: >
    A JSON object with a "recommendations" array. Each entry has outfit_name and
    a products array of {product_name, product_price, product_url}.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_master_routing.py -v`
Expected: PASS — all four.

- [ ] **Step 6: Commit**

```bash
git add src/shopai/crew.py src/shopai/config/tasks.yaml tests/test_master_routing.py
git commit -m "feat: score requests for clarity and route the master on the tier"
```

---

### Task 9: Multi-turn API

**Files:**
- Modify: `src/shopai/api/app.py:47-50` (`PlanRequest`), `:69-84` (`PlanResponse`), `:170-198` (`_plan`)
- Test: `tests/test_api_plan.py`

**Interfaces:**
- Consumes: everything from Tasks 2, 3, 5 and 8.
- Produces: `PlanRequest.runId: Optional[str]`, `PlanResponse.runId: str`.

This is what makes the run multi-turn: `runId` absent starts a run, present continues one. Both the user's message and the reply are appended to the transcript, which is what `user_text` accumulates and scoring reads.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_plan.py
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from shopai.api.app import app

client = TestClient(app)


def test_a_new_run_returns_its_run_id():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    assert response.status_code == 200
    assert response.json()["runId"] == "run-1"


def test_a_low_tier_reply_comes_back_as_a_message_not_a_plan():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "How do you usually like to dress?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    body = response.json()
    assert body["kind"] == "message"
    assert body["message"] == "How do you usually like to dress?"


def test_a_continued_run_reuses_the_supplied_run_id():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "", "raw": "",
            "run_id": "run-1", "clarity": {"tier": "medium"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "something in navy", "userToken": "tok", "runId": "run-1"},
        )

    passed = shopai.return_value.run_master_recommendation.call_args
    assert passed.kwargs["run_id"] == "run-1"


def test_both_turns_are_appended_to_the_transcript():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem:
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    senders = [c.args[1] for c in mem.conversation.append.call_args_list]
    assert senders == ["user", "agent"]


def test_compaction_is_attempted_after_the_turn():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem, \
         patch("shopai.api.app.user_id_from_token", return_value="user-1"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    mem.conversation.compact.assert_called_once_with("user-1", "run-1")


def test_a_compaction_failure_does_not_cost_the_user_their_answer():
    """Mem0 raises outright when MEM0_API_KEY is unset. Housekeeping must not
    turn into a 500."""
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem, \
         patch("shopai.api.app.user_id_from_token", return_value="user-1"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        mem.conversation.compact.side_effect = RuntimeError("Mem0 is not configured.")
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "What's the occasion?"


def test_an_out_of_scope_request_is_still_refused():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": False, "rejection": "out_of_scope",
            "message": "This is a shopping bot, I cannot help with that request.",
            "findings": {},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "debug my python", "userToken": "tok"},
        )

    body = response.json()
    assert body["kind"] == "error"
    assert body["errorKind"] == "out_of_scope"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_plan.py -v`
Expected: FAIL — `KeyError: 'runId'`, since `PlanResponse` has no such field.

- [ ] **Step 3: Add the fields**

In `src/shopai/api/app.py`, add `runId` to the request and response models:

```python
class PlanRequest(BaseModel):
    prompt: str
    userToken: Optional[str] = None
    runId: Optional[str] = None
```

```python
class PlanResponse(BaseModel):
    kind: Literal["plan", "message", "permission", "error"] = "plan"
    message: str = ""
    outfits: List[OutfitPlanResponse] = []
    runId: str = ""
    errorKind: Literal["out_of_scope", "not_allowed", "system_down", "clarification"] = (
        "system_down"
    )
```

- [ ] **Step 4: Rewrite the turn lifecycle**

Add the import:

```python
from shopai.memory import memory
```

Replace `_plan` with the six-step lifecycle:

```python
async def _plan(request: PlanRequest) -> PlanResponse:
    """One turn: record it, check it, score it, run it, record the reply.

    A runId continues an existing run; without one a new run starts. That is
    what lets a vague request climb tiers - scoring reads every user turn in
    the run, not just this message.
    """
    token = request.userToken or ""
    run_id = request.runId or str(uuid.uuid4())

    if token:
        memory.conversation.append(run_id, "user", request.prompt, access_token=token)

    verdict, rejection = await _guard(request.prompt)
    if rejection is not None:
        rejection.runId = run_id
        return rejection

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: Shopai().run_master_recommendation(
                request.prompt, {}, run_id=run_id, access_token=token
            ),
        )
    except Exception as exc:
        failure = _failure(f"Recommendation master failed: {exc}")
        failure.runId = run_id
        return failure

    _plan_store[run_id] = {
        "recommendation": result,
        "inputs": {"shopping_request": request.prompt},
        "userToken": request.userToken,
        "validation": verdict,
    }

    response = _plan_result(
        _recommendation_to_outfits(run_id, result),
        summary=result.get("summary", ""),
    )
    response.runId = run_id

    if token and response.message:
        memory.conversation.append(run_id, "agent", response.message, access_token=token)

    _compact_if_full(run_id, token)
    return response
```

And the compaction step, above `_plan`:

```python
def _compact_if_full(run_id: str, access_token: str) -> None:
    """Fold the conversation down if it has filled the context window.

    compact() decides for itself whether the threshold has been crossed; this
    only has to ask. Failures are swallowed on purpose - compaction is
    housekeeping, and Mem0 raises outright when MEM0_API_KEY is unset, which
    must not cost the user their answer.
    """
    if not access_token:
        return

    user_id = user_id_from_token(access_token)
    if not user_id:
        return

    try:
        memory.conversation.compact(user_id, run_id)
    except Exception:
        pass
```

This needs one more import:

```python
from shopai.memory import memory
from shopai.memory.user_memory import user_id_from_token
```

Note `_plan_store` is now keyed by `run_id` rather than a fresh uuid per call — a continued run overwrites its own entry instead of leaking a new one per turn.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_api_plan.py -v`
Expected: PASS — all seven.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS — every test from Tasks 1-9 plus the pre-existing suite.

- [ ] **Step 7: Commit**

```bash
git add src/shopai/api/app.py tests/test_api_plan.py
git commit -m "feat: multi-turn plan API with run continuation and transcript recording"
```

---

## Manual verification

Automated tests cover the scoring and the wiring, but not whether the master
actually honours the tier — that is the spec's stated risk, and only a real run
shows it.

- [ ] Apply `supabase/migrations/0002_conversation.sql` in the Supabase SQL editor.
- [ ] Start the server: `uv run run_api`.
- [ ] POST `{"prompt": "help me with my style", "userToken": "<token>"}` to
      `/outfit/plan/regular`. Expect `kind: "message"`, a `runId`, and a
      question about how the user dresses — **not** a question about an outfit.
      A question about the outfit means the master handed the agent the wrong
      tier, which is the failure mode the spec flags.
- [ ] POST again with the same `runId` and a more specific answer. Confirm the
      tier climbs — check `memory.task.get_status(run_id)` for the ledger entry
      recording which path each turn took.
- [ ] POST `{"prompt": "black fitted midi dress for a cocktail party with gold jewellery"}`
      and confirm it goes straight to the plan workflow with `kind: "plan"`.
