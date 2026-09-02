"""ShopAI FastAPI server.

Two endpoints, both taking a prompt and an optional user token:
  POST /outfit/plan/regular
  POST /outfit/plan/occasional

Every request is validated first. Only an allowed request reaches the
Recommendation Master agent; anything else comes straight back as an error
envelope the chat can render.
"""

from __future__ import annotations

import asyncio
import os
import uuid
import warnings
from typing import List, Literal, Optional

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from shopai.crew import Shopai
from shopai.telemetry import setup_telemetry

setup_telemetry()

app = FastAPI(title="ShopAI", version="0.1.0")

# Serve generated images at /static/<filename>
_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(_OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_OUTPUT_DIR), name="static")

# planId -> {recommendation, inputs, userToken, validation}
_plan_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / response models - mirror the Android data classes
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    prompt: str
    userToken: Optional[str] = None


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
    """

    kind: Literal["plan", "message", "permission", "error"] = "plan"
    message: str = ""
    outfits: List[OutfitPlanResponse] = []
    errorKind: Literal["out_of_scope", "not_allowed", "system_down", "clarification"] = (
        "system_down"
    )


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


def _plan_result(outfits: List[OutfitPlanResponse], summary: str = "") -> PlanResponse:
    """A plan with nothing in it is a message, not a plan - say so plainly."""
    if outfits:
        return PlanResponse(kind="plan", outfits=outfits)
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

async def _plan(request: PlanRequest) -> PlanResponse:
    """Guardrail, then hand the request to the Recommendation Master agent.

    Both routes share this: the API does not decide what a request is beyond
    pass/fail - the master reads it and picks the specialists.
    """
    verdict, rejection = await _guard(request.prompt)
    if rejection is not None:
        return rejection

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: Shopai().run_master_recommendation(request.prompt, {})
        )
    except Exception as exc:
        return _failure(f"Recommendation master failed: {exc}")

    plan_id = str(uuid.uuid4())
    _plan_store[plan_id] = {
        "recommendation": result,
        "inputs": {"shopping_request": request.prompt},
        "userToken": request.userToken,
        "validation": verdict,
    }
    return _plan_result(
        _recommendation_to_outfits(plan_id, result),
        summary=result.get("summary", ""),
    )


@app.post("/outfit/plan/regular", response_model=PlanResponse)
async def plan_regular(request: PlanRequest) -> PlanResponse:
    """Guardrail, then the Recommendation Master crew."""
    return await _plan(request)


@app.post("/outfit/plan/occasional", response_model=PlanResponse)
async def plan_occasional(request: PlanRequest) -> PlanResponse:
    """Guardrail, then the Recommendation Master crew - same pipeline as regular."""
    return await _plan(request)
