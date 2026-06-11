"""ShopAI FastAPI server — Human-in-the-Loop pipeline.

Endpoints match the Android ShopAIApiService exactly:
  POST /profile/update
  POST /outfit/plan
  GET  /outfit/recommendations
  GET  /outfit/visualize/{outfitId}
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
import warnings
from typing import List, Optional

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from shopai.crew import Shopai

app = FastAPI(title="ShopAI", version="0.1.0")

# Serve generated images at /static/<filename>
_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(_OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_OUTPUT_DIR), name="static")

# ---------------------------------------------------------------------------
# Minimal in-memory state — bridges the three sequential calls.
# No sessions; just stores the latest profile and per-outfitId crew outputs.
# ---------------------------------------------------------------------------
_profile: dict = {}
_outfit_store: dict[str, dict] = {}   # outfitId → {planning, recommendation}
_current_outfit_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Request / response models — mirror Android data classes exactly
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    height: str = ""
    bodyType: str = ""
    favoriteColors: List[str] = []
    styles: List[str] = []


class OutfitPlanRequest(BaseModel):
    moodText: str
    vibes: List[str] = []


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


class VisualizeData(BaseModel):
    outfitId: str = ""
    visualUrl: str = ""
    outfitName: str = ""
    items: List[ProductData] = []
    colorPalette: List[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _platform_from_url(url: str) -> str:
    if "amazon" in url:
        return "Amazon"
    if "flipkart" in url:
        return "Flipkart"
    if "myntra" in url:
        return "Myntra"
    if "meesho" in url:
        return "Meesho"
    return ""


def _crew_inputs(mood_text: str, vibes: List[str]) -> dict:
    profile = _profile
    style = ", ".join(profile.get("styles", []) + vibes) or "casual"
    return {
        "shopping_request": mood_text,
        "location": "India",
        "budget": "5000 INR",
        "gender": "female",
        "height": profile.get("height", "5'6\""),
        "body_type": profile.get("bodyType", "average"),
        "style": style,
    }


def _planning_to_response(outfit_id: str, planning: dict, products: List[ProductData] = None) -> OutfitPlanResponse:
    outfits = planning.get("outfits", [])
    first = outfits[0] if outfits else {}
    return OutfitPlanResponse(
        outfitId=outfit_id,
        outfitName=first.get("outfit_name", ""),
        description=first.get("rationale", ""),
        tags=first.get("items", []),
        heroImageUrl="",
        products=products or [],
    )


def _recommendation_products(recommendation: dict) -> List[ProductData]:
    recs = recommendation.get("recommendations", [])
    products: List[ProductData] = []
    for i, entry in enumerate(recs):
        for p in entry.get("products", []):
            products.append(ProductData(
                id=str(i),
                imageUrl="",
                name=p.get("product_name", ""),
                price=p.get("product_price", ""),
                platform=_platform_from_url(p.get("product_url", "")),
            ))
    return products


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/profile/update", status_code=200)
async def update_profile(profile: UserProfile):
    global _profile
    _profile = profile.model_dump()
    return {}


@app.post("/outfit/plan", response_model=OutfitPlanResponse)
async def plan_outfit(request: OutfitPlanRequest):
    global _current_outfit_id

    inputs = _crew_inputs(request.moodText, request.vibes)
    loop = asyncio.get_event_loop()

    try:
        planning = await loop.run_in_executor(None, Shopai().run_planning, inputs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Planning agent failed: {exc}")

    outfit_id = str(uuid.uuid4())
    _outfit_store[outfit_id] = {"planning": planning, "inputs": inputs}
    _current_outfit_id = outfit_id

    return _planning_to_response(outfit_id, planning)


@app.get("/outfit/recommendations", response_model=OutfitPlanResponse)
async def get_recommendations():
    if not _current_outfit_id or _current_outfit_id not in _outfit_store:
        raise HTTPException(status_code=404, detail="No outfit plan found. Call /outfit/plan first.")

    outfit_id = _current_outfit_id
    entry = _outfit_store[outfit_id]
    planning = entry["planning"]
    inputs = entry["inputs"]

    loop = asyncio.get_event_loop()
    try:
        recommendation = await loop.run_in_executor(
            None, lambda: Shopai().run_recommendation(inputs, planning)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendation agent failed: {exc}")

    _outfit_store[outfit_id]["recommendation"] = recommendation
    products = _recommendation_products(recommendation)

    return _planning_to_response(outfit_id, planning, products)


@app.get("/outfit/visualize/{outfitId}", response_model=VisualizeData)
async def visualize_outfit(outfitId: str):
    entry = _outfit_store.get(outfitId)
    if not entry:
        raise HTTPException(status_code=404, detail="Outfit not found.")
    if "recommendation" not in entry:
        raise HTTPException(status_code=400, detail="Recommendations not ready. Call /outfit/recommendations first.")

    planning = entry["planning"]
    recommendation = entry["recommendation"]
    inputs = entry["inputs"]

    loop = asyncio.get_event_loop()
    try:
        viz = await loop.run_in_executor(
            None, lambda: Shopai().run_visualization(inputs, planning, recommendation)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Visualization agent failed: {exc}")

    image_path = viz.get("image_path", "")
    visual_url = f"/static/{os.path.basename(image_path)}" if image_path else ""

    outfits = planning.get("outfits", [])
    outfit_name = outfits[0].get("outfit_name", "") if outfits else ""
    products = _recommendation_products(recommendation)

    return VisualizeData(
        outfitId=outfitId,
        visualUrl=visual_url,
        outfitName=outfit_name,
        items=products,
        colorPalette=[],
    )


@app.get("/health")
def health():
    return {"status": "ok"}
