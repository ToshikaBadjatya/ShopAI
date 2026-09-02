"""The task ledger the master agent works through.

Five tools over one run's ledger in task memory: plan a step, move its status,
revise its context, stop it, read where things stand.

The tools are bound to a run_id when they are built, not asked for it at call
time - a model that has to invent an identifier eventually invents the wrong
one, and a step written into someone else's ledger is worse than no step at
all.
"""

import json
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from shopai.memory import memory
from shopai.memory.task_memory import TASK_STATUSES

STATUS_LIST = ", ".join(sorted(TASK_STATUSES))


def _fail(exc: Exception) -> str:
    """A refused call is information for the agent, not a crash."""
    return json.dumps({"ok": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class PlanTaskInput(BaseModel):
    agent: str = Field(..., description="Which subagent should carry out this step.")
    task: str = Field(..., description="What that subagent must do, in one sentence.")
    user_context: str = Field("", description="What is known about the shopper that this step must respect.")
    task_context: str = Field("", description="Constraints and inputs specific to this step - budget, occasion, weather.")
    guardrails: list[str] = Field(default_factory=list, description="Rules this step must not break.")
    on_task_complete: str = Field("", description="What should happen once this step is done.")


class UpdateTaskStatusInput(BaseModel):
    step: int = Field(..., description="The step number to update.")
    status: str = Field(..., description=f"New status. One of: {STATUS_LIST}.")


class UpdateTaskContextInput(BaseModel):
    step: int = Field(..., description="The step number to revise.")
    user_context: Optional[str] = Field(None, description="Replacement user context. Omit to leave unchanged.")
    task_context: Optional[str] = Field(None, description="Replacement task context. Omit to leave unchanged.")
    guardrails: Optional[list[str]] = Field(None, description="Replacement guardrails. Omit to leave unchanged.")


class StopTaskInput(BaseModel):
    step: int = Field(..., description="The step number to halt.")
    reason: str = Field("", description="Why it is being stopped.")


class GetStatusInput(BaseModel):
    step: Optional[int] = Field(None, description="A single step to inspect. Omit for the whole ledger.")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class PlanTaskTool(BaseTool):
    name: str = "plan_task"
    description: str = (
        "Create and assign a new task to a subagent. Returns the stored entry, "
        "including the step number assigned to it - the ledger numbers steps, not you."
    )
    args_schema: Type[BaseModel] = PlanTaskInput
    run_id: str = ""

    def _run(self, agent: str, task: str, user_context: str = "", task_context: str = "",
             guardrails: Optional[list[str]] = None, on_task_complete: str = "") -> str:
        try:
            return json.dumps({"ok": True, "task": memory.task.plan_task(
                self.run_id, agent, task, user_context, task_context,
                guardrails, on_task_complete,
            )})
        except Exception as exc:
            return _fail(exc)


class UpdateTaskStatusTool(BaseTool):
    name: str = "update_task_status"
    description: str = (
        f"Update a task's execution status. Valid statuses: {STATUS_LIST}. "
        "Returns the updated entry."
    )
    args_schema: Type[BaseModel] = UpdateTaskStatusInput
    run_id: str = ""

    def _run(self, step: int, status: str) -> str:
        try:
            return json.dumps({"ok": True, "task": memory.task.update_task_status(
                self.run_id, step, status,
            )})
        except Exception as exc:
            return _fail(exc)


class UpdateTaskContextTool(BaseTool):
    name: str = "update_task_context"
    description: str = (
        "Add or change the information a task carries - user context, task "
        "context, or guardrails. Fields left out keep their current value."
    )
    args_schema: Type[BaseModel] = UpdateTaskContextInput
    run_id: str = ""

    def _run(self, step: int, user_context: Optional[str] = None,
             task_context: Optional[str] = None, guardrails: Optional[list[str]] = None) -> str:
        try:
            return json.dumps({"ok": True, "task": memory.task.update_task_context(
                self.run_id, step, user_context, task_context, guardrails,
            )})
        except Exception as exc:
            return _fail(exc)


class StopTaskTool(BaseTool):
    name: str = "stop_task"
    description: str = (
        "Halt a task that is no longer needed, marking it cancelled. A task "
        "that already completed cannot be stopped."
    )
    args_schema: Type[BaseModel] = StopTaskInput
    run_id: str = ""

    def _run(self, step: int, reason: str = "") -> str:
        try:
            return json.dumps({"ok": True, "task": memory.task.stop_task(
                self.run_id, step, reason,
            )})
        except Exception as exc:
            return _fail(exc)


class GetStatusTool(BaseTool):
    name: str = "get_status"
    description: str = (
        "Read where the run stands: one step with `step`, or the whole ledger "
        "with per-status counts when `step` is omitted."
    )
    args_schema: Type[BaseModel] = GetStatusInput
    run_id: str = ""

    def _run(self, step: Optional[int] = None) -> str:
        try:
            return json.dumps({"ok": True, "status": memory.task.get_status(self.run_id, step)})
        except Exception as exc:
            return _fail(exc)


def task_ledger_tools(run_id: str) -> list[BaseTool]:
    """The five ledger tools, all bound to one run."""
    if not run_id:
        raise ValueError("Ledger tools must be bound to a run_id.")
    return [
        PlanTaskTool(run_id=run_id),
        UpdateTaskStatusTool(run_id=run_id),
        UpdateTaskContextTool(run_id=run_id),
        StopTaskTool(run_id=run_id),
        GetStatusTool(run_id=run_id),
    ]
