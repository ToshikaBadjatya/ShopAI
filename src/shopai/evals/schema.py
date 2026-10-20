"""Basic eval schema, defined before any Arize wiring exists.

Two shapes only:

`GoldenExample` - a hand-written or replayed case. Its fields mirror the
`inputs` dict `Shopai.run_master_recommendation` builds (see crew.py), so a
golden example can be fed straight into `kickoff()` without translation.

`EvalResult` - the outcome of scoring one example (or one live span) against
one category from `EvalCategory`. `to_arize_row` shapes it into the
`context.span_id` / `eval.<name>.label` / `eval.<name>.score` /
`eval.<name>.explanation` columns Arize's evaluation ingestion expects -
kept here so the column names are settled before the upload code exists,
not invented at upload time.

No pydantic/pandas dependency: the project has neither yet, and a handful of
dataclasses is enough to keep golden sets and eval output shaped the same
way across scripts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvalCategory(str, Enum):
    """One entry per component in the failure-mode taxonomy.

    Matches the component column of the taxonomy table exactly (not the finer
    code-level split used earlier), so a failing eval groups the same way the
    taxonomy - and any dashboard built from it - already does. `implemented`
    on `GoldenExample` says whether the owning code exists yet; several of
    these components are architecture-diagram-only today.
    """

    VALIDATOR = "validator"                                    # run_validation
    CLARIFICATION = "clarification"                             # clarification_agent
    MASTER_RECOMMENDATION = "master_recommendation"             # recommendation_master_agent + task ledger
    RECOMMENDATION = "recommendation"                           # recommendation_agent
    VISUALIZATION = "visualization"                             # visualize_agent
    WARDROBE = "wardrobe"                                       # planned - Wardrobe Manager Agent, not in crew.py yet
    SOCIAL_MEDIA = "social_media"                               # planned - Social Media Tool, not in crew.py yet
    MARKETPLACE = "marketplace"                                 # marketplace_agent (stub, no tools yet)
    SHOPPING_EXPERIENCE_LEARNING = "shopping_experience_learning"  # planned - User Shopping Patterns Agents, not in crew.py yet


@dataclass
class GoldenExample:
    """One labeled case for offline/regression eval.

    `id` is stable across runs so results can be diffed run-over-run.
    Fields through `conversation_text` mirror the `inputs` dict built in
    `Shopai.run_master_recommendation`; the `expected_*` fields are what a
    human (or a prior good run) says should happen.
    """

    id: str
    category: EvalCategory
    failure_mode: str = ""   # verbatim line-item from the taxonomy table, e.g.
                              # "Prompt Injection Bypassed (Delete the database)"
    severity: str = "medium"  # "low" | "medium" | "high" | "critical"
    implemented: bool = True  # False when the owning agent/tool doesn't exist in
                               # crew.py yet (Wardrobe, Social Media, most of
                               # Marketplace, Shopping Experience Learning) - the
                               # example still documents the expected contract.
    tags: list[str] = field(default_factory=list)

    # --- inputs, same shape as run_master_recommendation's `inputs` dict ---
    shopping_request: str = ""
    location: str = "India"
    budget: str = "5000 INR"
    gender: str = "female"
    height: str = "5'6\""
    body_type: str = "average"
    style: str = "casual"
    conversation_text: str = ""  # accumulated turns; empty means single-turn
    persistent_profile: dict[str, Any] = field(default_factory=dict)
    # Seeds UserInfoMemory (user_memory.py WRITABLE_FIELDS) as it would exist
    # *before* this run starts - a returning user's stored culture_summary,
    # skin_tone, undertone, preferred_fabrics, etc. Separate from
    # conversation_text because the Context Builder's job is to merge both
    # sources, not just replay this run's turns.

    # --- expectations, one eval category cares about a subset of these ---
    expected_clarity_tier: str | None = None        # "low" | "medium" | "high"
    expected_missing_dimensions: list[str] = field(default_factory=list)
    expected_route: str | None = None                # "clarification" | "plan"
    expected_recommendation_count_min: int | None = None
    expected_budget_max_inr: int | None = None
    expected_required_terms: list[str] = field(default_factory=list)  # must appear in output
    expected_forbidden_terms: list[str] = field(default_factory=list)  # must not appear
    # Open bag for checks that don't fit a named field above - e.g.
    # {"max_questions": 5}, {"no_duplicate_agent_task_pairs": True},
    # {"all_planned_tasks_resolved": True}, {"wardrobe_match_score_min": 50},
    # {"requires_user_confirmation": True}. Named fields exist for the checks
    # reused across many examples; this is for the ones that aren't.
    expected_checks: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GoldenExample":
        d = dict(d)
        d["category"] = EvalCategory(d["category"])
        return cls(**d)


@dataclass
class EvalResult:
    """The score for one (example or live span) x (category) pair.

    `example_id` links back to a `GoldenExample.id` for offline runs;
    `span_id`/`trace_id` link to a live OpenInference span captured by the
    `arize.otel.register(auto_instrument=True)` wiring in telemetry.py, for
    online eval. At least one of the two id pairs should be set.
    """

    category: EvalCategory
    label: str            # short verdict, e.g. "correct" / "incorrect" / "pass" / "fail"
    score: float           # numeric, 0.0-1.0 unless the category defines otherwise
    explanation: str = ""

    example_id: str | None = None
    run_id: str | None = None
    span_id: str | None = None
    trace_id: str | None = None
    agent_name: str | None = None   # e.g. "recommendation_master_agent"
    task_name: str | None = None    # e.g. "master_recommendation_task"

    def to_arize_row(self) -> dict[str, Any]:
        """Shape this result into Arize's per-span eval column convention.

        Arize's evaluation ingestion expects one row per span with columns
        named `context.span_id` and, per eval, `eval.<name>.label`,
        `eval.<name>.score`, `eval.<name>.explanation`. Building that here
        means the column names are fixed before any upload script exists.
        """
        name = self.category.value
        return {
            "context.span_id": self.span_id,
            "context.trace_id": self.trace_id,
            f"eval.{name}.label": self.label,
            f"eval.{name}.score": self.score,
            f"eval.{name}.explanation": self.explanation,
        }

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


def load_golden_examples(path: str) -> list[GoldenExample]:
    """Read a JSONL file of golden examples, one JSON object per line."""
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(GoldenExample.from_dict(json.loads(line)))
    return examples


def write_eval_results(path: str, results: list[EvalResult]) -> None:
    """Append eval results as JSONL, one JSON object per line."""
    with open(path, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_dict()) + "\n")
