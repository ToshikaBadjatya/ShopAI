"""Background runs - what the master is doing right now, and how it ended.

A plan takes minutes, far longer than one HTTP request should stay open, so
the API starts the master in the background and the client polls. This is the
board both sides read: the worker writes progress lines and the final
envelope; the status endpoint reads them; the stop endpoint raises a flag the
worker checks between steps.

Held in process, keyed by run_id, like the task ledger - a run's live state is
worthless once the client has read how it ended.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

RunStatus = Literal["running", "succeeded", "failed", "cancelled"]

TERMINAL_STATES: set[str] = {"succeeded", "failed", "cancelled"}

# A finished run is kept this long for the client's last poll to find it.
FINISHED_TTL_SECONDS = 15 * 60


class RunCancelled(BaseException):
    """Raised inside a run once someone asked it to stop.

    A BaseException, not an Exception, on purpose: CrewAI retries an agent on
    any Exception (and its passthrough list is empty), and the tool and
    clarifier layers swallow Exceptions too. Every one of those would turn a
    stop into one more model call. Like KeyboardInterrupt, this goes straight
    through them.
    """


@dataclass
class RunState:
    state: RunStatus = "running"
    message: str = ""
    step: int = 0
    # The final envelope, once there is one. Typed loosely so this module does
    # not have to import the API's models.
    result: Any = None
    cancel: threading.Event = field(default_factory=threading.Event)
    updated_at: float = field(default_factory=time.monotonic)


class RunRegistry:
    """Every background run this process knows about."""

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()

    def start(self, run_id: str, message: str = "") -> RunState:
        """Register a new run. Refuses one that is already running."""
        with self._lock:
            self._sweep()
            existing = self._runs.get(run_id)
            if existing is not None and existing.state == "running":
                raise ValueError(f"Run '{run_id}' is already running.")
            run = RunState(message=message)
            self._runs[run_id] = run
            return run

    def is_running(self, run_id: str) -> bool:
        with self._lock:
            run = self._runs.get(run_id)
            return run is not None and run.state == "running"

    def progress(self, run_id: str, message: str) -> None:
        """Say what the run is doing now. A repeat of the current line is not news."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.state != "running" or not message or message == run.message:
                return
            run.message = message
            run.step += 1
            run.updated_at = time.monotonic()

    def finish(self, run_id: str, state: RunStatus, result: Any = None) -> None:
        """Record how a run ended. The first ending wins."""
        if state not in TERMINAL_STATES:
            raise ValueError(f"'{state}' is not an ending.")
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.state != "running":
                return
            run.state = state
            run.result = result
            run.updated_at = time.monotonic()

    def request_stop(self, run_id: str) -> Optional[str]:
        """Ask a run to stop. Returns its state, or None for an unknown run.

        Only raises the flag - the run itself notices at its next step and
        records the ending, so a finished run stays exactly as it finished.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            if run.state == "running":
                run.cancel.set()
            return run.state

    def stop_all(self) -> None:
        with self._lock:
            for run in self._runs.values():
                run.cancel.set()

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            run = self._runs.get(run_id)
            return run is not None and run.cancel.is_set()

    def get(self, run_id: str) -> Optional[RunState]:
        """A snapshot of the run, safe to read without the lock."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            return RunState(
                state=run.state, message=run.message, step=run.step,
                result=run.result, cancel=run.cancel, updated_at=run.updated_at,
            )

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()

    def _sweep(self) -> None:
        """Drop finished runs nobody has come back for. Caller holds the lock."""
        cutoff = time.monotonic() - FINISHED_TTL_SECONDS
        for run_id in [
            rid for rid, run in self._runs.items()
            if run.state in TERMINAL_STATES and run.updated_at < cutoff
        ]:
            del self._runs[run_id]


runs = RunRegistry()
