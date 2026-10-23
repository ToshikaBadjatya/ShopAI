"""ShopAI FastAPI server.

Two endpoints start a plan, both taking a prompt and an optional user token:
  POST /outfit/plan/regular
  POST /outfit/plan/occasional

Every request is validated first, synchronously - the guardrail is instant, so
a rejection comes straight back as an error envelope the chat can render. An
allowed request starts the Recommendation Master in the background and gets a
`status` envelope at once; a plan takes minutes, far longer than one request
should stay open. The client then polls, and may stop the run:
  GET  /outfit/plan/{run_id}/status
  POST /outfit/plan/{run_id}/stop
"""

from __future__ import annotations

import asyncio
import os
import threading
import uuid
import warnings
from contextlib import asynccontextmanager
from typing import Callable, Dict, List, Literal, Optional

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from opentelemetry import context as otel_context
from opentelemetry import trace
from pydantic import BaseModel

from shopai.crew import Shopai
from shopai.memory import memory
from shopai.memory.user_memory import user_id_from_token
from shopai.progress import STARTING
from shopai.runs import RunCancelled, runs
from shopai.telemetry import setup_telemetry

# planId -> {recommendation, inputs, userToken, validation}
_plan_store: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Process start-up and shut-down.

    Tracing is registered here rather than at import, so importing this module
    (tests do) has no side effects. On the way out, pending spans are flushed -
    the Arize exporter batches them, and a stop would otherwise drop the last
    few - every background run is told to stop, and the in-memory stores are
    cleared.
    """
    setup_telemetry()
    yield

    runs.stop_all()

    provider = trace.get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)  # the no-op default has none
    if callable(shutdown):
        shutdown()
    _plan_store.clear()
    runs.clear()


app = FastAPI(title="ShopAI", version="0.1.0", lifespan=lifespan)

# Serve generated images at /static/<filename>. The directory has to exist when
# the mount is created, so this stays at import time.
_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(_OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_OUTPUT_DIR), name="static")


# ---------------------------------------------------------------------------
# Request / response models - mirror the Android data classes
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    prompt: str
    userToken: Optional[str] = None
    runId: Optional[str] = None


class ProductData(BaseModel):
    id: str = ""
    imageUrl: str = ""
    name: str = ""
    price: str = ""
    platform: str = ""


class OutfitPlanResponse(BaseModel):
    outfitId: str = ""
    outfitName: str = ""
    description: str = ""
    tags: List[str] = []
    heroImageUrl: str = ""
    products: List[ProductData] = []


class PlanResponse(BaseModel):
    """One shape for every outcome.

    `kind` tells the client what it is holding:
      plan       - `outfits` is populated
      message    - plain reply from Sia, `message` only
      permission - Sia needs access before continuing, `message` explains what
      error      - `message` says what went wrong, `errorKind` how to show it
      status     - the run is still going; `message` says what it is doing,
                   `step` moves on each time that changes. Poll again.

    `state` is where the run stands: running until it has succeeded, failed,
    or been cancelled. A client polls until it is anything but running.
    """

    kind: Literal["plan", "message", "permission", "error", "status"] = "plan"
    message: str = ""
    outfits: List[OutfitPlanResponse] = []
    runId: str = ""
    errorKind: Literal["out_of_scope", "not_allowed", "system_down", "clarification", "busy"] = (
        "system_down"
    )
    state: Literal["running", "succeeded", "failed", "cancelled"] = "succeeded"
    step: int = 0
    # The master's ledger, counted by status - {"completed": 2, "in_progress": 1}.
    ledger: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _platform_from_url(url: str) -> str:
    for name in ("amazon", "flipkart", "myntra", "meesho"):
        if name in url:
            return name.capitalize()
    return ""


def _recommendation_to_outfits(plan_id: str, recommendation: dict) -> List[OutfitPlanResponse]:
    outfits: List[OutfitPlanResponse] = []
    for i, entry in enumerate(recommendation.get("recommendations", [])[:5]):
        products = [
            ProductData(
                id=str(j),
                name=p.get("product_name") or "",
                price=p.get("product_price") or "",
                platform=_platform_from_url(p.get("product_url") or ""),
            )
            for j, p in enumerate(entry.get("products", []))
        ]
        outfits.append(
            OutfitPlanResponse(
                outfitId=f"{plan_id}:{i}",
                outfitName=entry.get("outfit_name", ""),
                products=products,
            )
        )
    return outfits


def _plan_result(
    outfits: List[OutfitPlanResponse], summary: str = "", top_pick: str = ""
) -> PlanResponse:
    """A plan with nothing in it is a message, not a plan - say so plainly."""
    if outfits:
        # `message` carries the master's single pick when the user asked for one.
        return PlanResponse(kind="plan", outfits=outfits, message=top_pick)
    return PlanResponse(
        kind="message",
        message=summary or "I couldn't pull a look together for that. Tell me a bit more?",
    )


def _failure(message: str, error_kind: str = "system_down") -> PlanResponse:
    """Crew failures come back as an envelope, not a 5xx - the chat has to say something."""
    return PlanResponse(kind="error", message=message, errorKind=error_kind)


# How a guardrail rejection is drawn in the chat.
_REJECTION_KIND = {
    "out_of_scope": "out_of_scope",
    "not_allowed": "not_allowed",
    "needs_clarification": "clarification",
}


async def _guard(prompt: str) -> tuple[dict, Optional[PlanResponse]]:
    """Run the guardrail before anything else.

    Returns (verdict, rejection). `rejection` is None when the request passed
    and should go to the master agent; otherwise it is the envelope to return
    as-is. A guardrail that itself fails counts as a rejection - failing open
    would defeat the point of having one.
    """
    loop = asyncio.get_event_loop()
    try:
        verdict = await loop.run_in_executor(None, Shopai().run_validation, prompt)
    except Exception as exc:
        return {}, _failure(f"Could not check that request: {exc}")

    if verdict.get("allowed"):
        return verdict, None

    rejection = verdict.get("rejection", "needs_clarification")
    # The fixed line from the guardrail, never the diagnostic reason.
    message = verdict.get("message") or "I can't help with that one."
    return verdict, _failure(message, error_kind=_REJECTION_KIND.get(rejection, "system_down"))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

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


def _spawn(job: Callable[[], None]) -> None:
    """Run a job off the request. A seam, so tests can run it inline.

    A daemon thread rather than the event loop's executor: a run lasts
    minutes, and must not hold the server open on shutdown - lifespan has
    already told it to stop by then.
    """
    threading.Thread(target=job, daemon=True).start()


CANCELLED_MESSAGE = "Stopped. Tell me when you want to pick it back up."


async def _plan(request: PlanRequest) -> PlanResponse:
    """Check the request, then start the master in the background.

    The guardrail answers here, at once. Anything it allows becomes a
    background run, and the reply is a `status` envelope - the client polls
    GET /outfit/plan/{runId}/status for what happens next.

    A runId continues an existing run; without one a new run starts. That is
    what lets a vague request climb tiers - scoring reads every user turn in
    the run, not just this message. One run takes one job at a time.
    """
    token = request.userToken or ""
    run_id = request.runId or str(uuid.uuid4())

    verdict, rejection = await _guard(request.prompt)
    if rejection is not None:
        rejection.runId = run_id
        return rejection

    try:
        runs.start(run_id, STARTING)
    except ValueError:
        busy = _failure("I'm still working on your last message - give me a moment.", "busy")
        busy.runId = run_id
        return busy

    # The worker thread starts with an empty trace context; carry this
    # request's over so the crew's spans join its trace in Arize.
    trace_context = otel_context.get_current()
    _spawn(lambda: _run_job(request, run_id, token, verdict, trace_context))

    return PlanResponse(
        kind="status", state="running", runId=run_id, message=STARTING, step=0,
    )


def _run_job(
    request: PlanRequest, run_id: str, token: str, verdict: dict, trace_context=None,
) -> None:
    """One turn of the master, in the background. Always records an ending.

    Recording the transcript is the master's own job, not this layer's - see
    Shopai._append_turn - so both turns are written from inside
    run_master_recommendation, before this function ever sees a result.
    """
    attached = otel_context.attach(trace_context) if trace_context is not None else None
    try:
        try:
            result = Shopai().run_master_recommendation(
                request.prompt, {}, run_id=run_id, access_token=token,
                on_progress=lambda line: runs.progress(run_id, line),
                should_stop=lambda: runs.is_cancelled(run_id),
            )
        except RunCancelled:
            runs.finish(
                run_id, "cancelled",
                PlanResponse(kind="message", message=CANCELLED_MESSAGE,
                             runId=run_id, state="cancelled"),
            )
            return
        except Exception as exc:
            failure = _failure(f"Recommendation master failed: {exc}")
            failure.runId = run_id
            failure.state = "failed"
            runs.finish(run_id, "failed", failure)
            return

        # The master echoes back the run it acted under. The registry is keyed
        # on the id the client polls, so that one stays; the store follows the
        # master, which is authoritative on where its ledger lives.
        acted_on = result.get("run_id", run_id)

        _plan_store[acted_on] = {
            "recommendation": result,
            "inputs": {"shopping_request": request.prompt},
            "userToken": request.userToken,
            "validation": verdict,
        }

        response = _plan_result(
            _recommendation_to_outfits(acted_on, result),
            summary=result.get("summary", ""),
            top_pick=result.get("top_pick", ""),
        )
        response.runId = acted_on

        _compact_if_full(acted_on, token)
        runs.finish(run_id, "succeeded", response)
    finally:
        if attached is not None:
            otel_context.detach(attached)


@app.post("/outfit/plan/regular", response_model=PlanResponse)
async def plan_regular(request: PlanRequest) -> PlanResponse:
    """Guardrail, then the Recommendation Master crew."""
    return await _plan(request)


@app.post("/outfit/plan/occasional", response_model=PlanResponse)
async def plan_occasional(request: PlanRequest) -> PlanResponse:
    """Guardrail, then the Recommendation Master crew - same pipeline as regular."""
    return await _plan(request)


@app.get("/outfit/plan/{run_id}/status", response_model=PlanResponse)
async def plan_status(run_id: str) -> PlanResponse:
    """Where a background run has got to.

    Running: a `status` envelope - what the master is doing now, and its
    ledger counts. Finished: the run's final envelope, exactly as the
    blocking endpoint used to return it, with `state` saying how it ended.
    """
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No run '{run_id}'.")

    if run.state != "running":
        response = run.result.model_copy()
        response.state = run.state
        return response

    try:
        ledger = memory.task.get_status(run_id).get("status_counts", {})
    except Exception:
        ledger = {}
    return PlanResponse(
        kind="status", state="running", runId=run_id,
        message=run.message, step=run.step, ledger=ledger,
    )


@app.post("/outfit/plan/{run_id}/stop")
async def stop_plan(run_id: str) -> dict:
    """Ask a run to stop. It ends at its next step and the poll reports it.

    Idempotent: stopping a finished run leaves it as it finished.
    """
    state = runs.request_stop(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No run '{run_id}'.")
    return {"runId": run_id, "state": state}


@app.delete("/task/{run_id}")
async def clear_task(run_id: str) -> dict:
    """Discard a run's task ledger entirely, stopping the run if it is going.

    The app calls this as the chat screen is left - nobody is waiting for the
    answer any more, so the crew should not keep spending on it.
    """
    runs.request_stop(run_id)
    cleared = memory.task.delete(run_id)
    return {"cleared": cleared}
