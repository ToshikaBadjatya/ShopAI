"""Task memory - the ledger the master agent plans against.

One ledger per run: an ordered list of steps the master has assigned to its
specialists, each carrying the context and guardrails that step must respect,
and the status it has reached.

Held in process, keyed by run_id. A ledger is scaffolding for one orchestration
run - written and re-read many times inside a single agent loop, worthless once
the run is over - so it lives where it is cheap to touch rather than in
Postgres. Swapping in a durable backend later means reimplementing this class,
not changing any caller.
"""

import threading
from typing import Any, Literal, Optional

from shopai.memory.base import Memory

TaskStatus = Literal["planned", "in_progress", "blocked", "completed", "cancelled"]

TASK_STATUSES: set[str] = {"planned", "in_progress", "blocked", "completed", "cancelled"}

# Statuses a task can still be stopped from. A finished task is not haltable.
ACTIVE_STATUSES: set[str] = {"planned", "in_progress", "blocked"}


class TaskMemory(Memory):
    """The master agent's task ledger, one per run.

    Every entry has the shape:

        {"step": 1,
         "agent": "recommendation_agent",
         "task": "curate four party looks",
         "user_context": "size medium, avoids orange",
         "task_context": "budget 5000 INR, monsoon weather",
         "guardrails": ["stay within budget", "no fast fashion"],
         "on_task_complete": "hand to review_recommendation_agent",
         "status": "planned"}
    """

    name = "task"

    def __init__(self) -> None:
        self._ledgers: dict[str, list[dict]] = {}
        # Ledgers are keyed per run, but two requests can still be in flight at
        # once - the lock keeps step numbering from colliding.
        self._lock = threading.Lock()

    # ---------------------------------------------------------- ABC surface

    def read(self, key: str, **_: Any) -> dict:
        """The whole ledger for a run. An alias for get_status()."""
        return self.get_status(key)

    def write(self, key: str, values: dict, **_: Any) -> dict:
        """Add one task. `values` carries the fields plan_task() takes."""
        return self.plan_task(key, **values)

    def delete(self, key: str, **_: Any) -> bool:
        """Discard a run's ledger entirely. True when there was one."""
        with self._lock:
            return self._ledgers.pop(key, None) is not None

    # ------------------------------------------------------------- ledger

    def plan_task(
        self,
        run_id: str,
        agent: str,
        task: str,
        user_context: str = "",
        task_context: str = "",
        guardrails: Optional[list[str]] = None,
        on_task_complete: str = "",
    ) -> dict:
        """Create and assign a step to a subagent.

        The step number is assigned here rather than by the caller, so two
        concurrent writes cannot claim the same one.
        """
        if not run_id:
            raise ValueError("A task needs a run_id to belong to.")
        if not agent or not task:
            raise ValueError("A task needs both an agent to run it and a task to do.")

        with self._lock:
            ledger = self._ledgers.setdefault(run_id, [])
            entry = {
                "step": len(ledger) + 1,
                "agent": agent,
                "task": task,
                "user_context": user_context,
                "task_context": task_context,
                "guardrails": list(guardrails or []),
                "on_task_complete": on_task_complete,
                "status": "planned",
            }
            ledger.append(entry)
            return dict(entry)

    def update_task_status(self, run_id: str, step: int, status: str) -> dict:
        """Move a step to a new status."""
        if status not in TASK_STATUSES:
            raise ValueError(
                f"Unknown status '{status}'. Use one of: {', '.join(sorted(TASK_STATUSES))}."
            )

        with self._lock:
            entry = self._find(run_id, step)
            entry["status"] = status
            return dict(entry)

    def update_task_context(
        self,
        run_id: str,
        step: int,
        user_context: Optional[str] = None,
        task_context: Optional[str] = None,
        guardrails: Optional[list[str]] = None,
    ) -> dict:
        """Revise what a step knows.

        Only the fields given are touched - passing nothing for a field leaves
        it as it was, so a caller correcting the task context cannot silently
        wipe the guardrails.
        """
        with self._lock:
            entry = self._find(run_id, step)
            if user_context is not None:
                entry["user_context"] = user_context
            if task_context is not None:
                entry["task_context"] = task_context
            if guardrails is not None:
                entry["guardrails"] = list(guardrails)
            return dict(entry)

    def stop_task(self, run_id: str, step: int, reason: str = "") -> dict:
        """Cancel a step that is no longer wanted.

        Refuses to stop a step that already finished - cancelling a completed
        task would rewrite history rather than halt work.
        """
        with self._lock:
            entry = self._find(run_id, step)
            if entry["status"] not in ACTIVE_STATUSES:
                raise ValueError(
                    f"Step {step} is already '{entry['status']}' and cannot be stopped."
                )
            entry["status"] = "cancelled"
            if reason:
                entry["stopped_because"] = reason
            return dict(entry)

    def get_status(self, run_id: str, step: Optional[int] = None) -> dict:
        """Where a run has got to - one step, or the whole ledger with counts."""
        with self._lock:
            if step is not None:
                return dict(self._find(run_id, step))

            ledger = self._ledgers.get(run_id, [])
            counts: dict[str, int] = {}
            for entry in ledger:
                counts[entry["status"]] = counts.get(entry["status"], 0) + 1

            return {
                "run_id": run_id,
                "task_count": len(ledger),
                "status_counts": counts,
                "tasks": [dict(entry) for entry in ledger],
            }

    # ------------------------------------------------------------ internal

    def _find(self, run_id: str, step: int) -> dict:
        """The live entry for a step. Caller must already hold the lock."""
        for entry in self._ledgers.get(run_id, []):
            if entry["step"] == step:
                return entry
        raise KeyError(f"No step {step} in run '{run_id}'.")
