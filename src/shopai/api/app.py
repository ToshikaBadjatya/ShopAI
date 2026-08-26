"""ShopAI FastAPI server.

Two endpoints, both taking a prompt and an optional user token:
  POST /outfit/plan/regular
  POST /outfit/plan/occasional

Both answer with the same envelope: `kind` says what happened, and the client
decides how to draw it. Everything else is kept below, commented out.
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

# outfitId -> {planning|recommendation, inputs, userToken}
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


def _crew_inputs(prompt: str) -> dict:
    return {
        "shopping_request": prompt,
        "location": "India",
        "budget": "5000 INR",
        "gender": "female",
        "height": "5'6\"",
        "body_type": "average",
        "style": "casual",
    }


def _planning_to_outfits(plan_id: str, planning: dict) -> List[OutfitPlanResponse]:
    return [
        OutfitPlanResponse(
            outfitId=f"{plan_id}:{i}",
            outfitName=outfit.get("outfit_name", ""),
            description=outfit.get("rationale", ""),
            tags=outfit.get("items", []),
        )
        for i, outfit in enumerate(planning.get("outfits", [])[:5])
    ]


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


def _plan_result(outfits: List[OutfitPlanResponse]) -> PlanResponse:
    """A plan with nothing in it is a message, not a plan - say so plainly."""
    if not outfits:
        return PlanResponse(
            kind="message",
            message="I couldn't pull a look together for that. Tell me a bit more?",
        )
    return PlanResponse(kind="plan", outfits=outfits)


def _failure(message: str, error_kind: str = "system_down") -> PlanResponse:
    """Crew failures come back as an envelope, not a 5xx - the chat has to say something."""
    return PlanResponse(kind="error", message=message, errorKind=error_kind)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/outfit/plan/regular", response_model=PlanResponse)
async def plan_regular(request: PlanRequest) -> PlanResponse:
    inputs = _crew_inputs(request.prompt)
    loop = asyncio.get_event_loop()

    try:
        planning = await loop.run_in_executor(None, Shopai().run_planning, inputs)
    except Exception as exc:
        return _failure(f"Planning agent failed: {exc}")

    plan_id = str(uuid.uuid4())
    _plan_store[plan_id] = {
        "planning": planning,
        "inputs": inputs,
        "userToken": request.userToken,
    }
    return _plan_result(_planning_to_outfits(plan_id, planning))


@app.post("/outfit/plan/occasional", response_model=PlanResponse)
async def plan_occasional(request: PlanRequest) -> PlanResponse:
    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(
            None, lambda: Shopai().plan_occasional_outfit(request.prompt, {})
        )
    except ValueError as exc:
        return _failure(str(exc), error_kind="out_of_scope")
    except Exception as exc:
        return _failure(f"Occasional outfit planning failed: {exc}")

    plan_id = str(uuid.uuid4())
    _plan_store[plan_id] = {
        "recommendation": result,
        "inputs": {"shopping_request": request.prompt},
        "userToken": request.userToken,
    }
    return _plan_result(_recommendation_to_outfits(plan_id, result))


# ===========================================================================
# Everything below is the previous surface, kept for reference.
# ===========================================================================

# """ShopAI FastAPI server — Human-in-the-Loop pipeline.

# Endpoints match the Android ShopAIApiService exactly:
#   POST /profile/update
#   POST /outfit/plan
#   POST /outfit/plan/occasional
#   GET  /outfit/recommendations
#   POST /outfit/visualize
# """

# from __future__ import annotations

# import asyncio
# import os
# import re
# import uuid
# import warnings
# from typing import List, Optional

# warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# from fastapi import FastAPI, HTTPException
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel

# from shopai.crew import Shopai
# from shopai.telemetry import setup_telemetry

# setup_telemetry()

# app = FastAPI(title="ShopAI", version="0.1.0")

# # Serve generated images at /static/<filename>
# _OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
# os.makedirs(_OUTPUT_DIR, exist_ok=True)
# app.mount("/static", StaticFiles(directory=_OUTPUT_DIR), name="static")

# # ---------------------------------------------------------------------------
# # Minimal in-memory state — bridges the three sequential calls.
# # No sessions; just stores the latest profile and per-outfitId crew outputs.
# # ---------------------------------------------------------------------------
# _profile: dict = {}
# _outfit_store: dict[str, dict] = {}   # outfitId → {planning, recommendation}
# _current_outfit_id: Optional[str] = None


# # ---------------------------------------------------------------------------
# # Request / response models — mirror Android data classes exactly
# # ---------------------------------------------------------------------------

# class UserProfile(BaseModel):
#     height: str = ""
#     bodyType: str = ""
#     favoriteColors: List[str] = []
#     styles: List[str] = []


# class OutfitPlanRequest(BaseModel):
#     prompt: str


# class OccasionalOutfitRequest(BaseModel):
#     prompt: str


# class ProductData(BaseModel):
#     id: str = ""
#     imageUrl: str = ""
#     name: str = ""
#     price: str = ""
#     platform: str = ""


# class OutfitPlanResponse(BaseModel):
#     outfitId: str = ""
#     outfitName: str = ""
#     description: str = ""
#     tags: List[str] = []
#     heroImageUrl: str = ""
#     products: List[ProductData] = []


# class VisualizeData(BaseModel):
#     outfitId: str = ""
#     visualUrl: str = ""
#     outfitName: str = ""
#     items: List[ProductData] = []
#     colorPalette: List[str] = []


# class GetLinksRequest(BaseModel):
#     outfitId: str = ""
#     selectedItems: List[str] = []


# class ProductLink(BaseModel):
#     name: str = ""
#     url: str = ""
#     price: str = ""
#     platform: str = ""


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _platform_from_url(url: str) -> str:
#     if "amazon" in url:
#         return "Amazon"
#     if "flipkart" in url:
#         return "Flipkart"
#     if "myntra" in url:
#         return "Myntra"
#     if "meesho" in url:
#         return "Meesho"
#     return ""


# def _crew_inputs(mood_text: str, vibes: List[str]) -> dict:
#     profile = _profile
#     style = ", ".join(profile.get("styles", []) + vibes) or "casual"
#     return {
#         "shopping_request": mood_text,
#         "location": "India",
#         "budget": "5000 INR",
#         "gender": "female",
#         "height": profile.get("height", "5'6\""),
#         "body_type": profile.get("bodyType", "average"),
#         "style": style,
#     }


# def _planning_to_outfit_list(plan_id: str, planning: dict, products: List[ProductData] = None) -> List[OutfitPlanResponse]:
#     outfits = planning.get("outfits", [])[:5]
#     return [
#         OutfitPlanResponse(
#             outfitId=f"{plan_id}:{i}",
#             outfitName=outfit.get("outfit_name", ""),
#             description=outfit.get("rationale", ""),
#             tags=outfit.get("items", []),
#             heroImageUrl="",
#             products=products or [],
#         )
#         for i, outfit in enumerate(outfits)
#     ]


# def _planning_to_response(plan_id: str, planning: dict, outfit_idx: int = 0, products: List[ProductData] = None) -> OutfitPlanResponse:
#     outfits = planning.get("outfits", [])
#     outfit = outfits[outfit_idx] if outfit_idx < len(outfits) else {}
#     return OutfitPlanResponse(
#         outfitId=f"{plan_id}:{outfit_idx}",
#         outfitName=outfit.get("outfit_name", ""),
#         description=outfit.get("rationale", ""),
#         tags=outfit.get("items", []),
#         heroImageUrl="",
#         products=products or [],
#     )


# def _recommendation_products(recommendation: dict) -> List[ProductData]:
#     recs = recommendation.get("recommendations", [])
#     products: List[ProductData] = []
#     for i, entry in enumerate(recs):
#         for p in entry.get("products", []):
#             url = p.get("product_url") or ""
#             products.append(ProductData(
#                 id=str(i),
#                 imageUrl="",
#                 name=p.get("product_name") or "",
#                 price=p.get("product_price") or "",
#                 platform=_platform_from_url(url),
#             ))
#     return products


# def _recommendation_to_outfit_list(plan_id: str, recommendation: dict) -> List[OutfitPlanResponse]:
#     recs = recommendation.get("recommendations", [])[:5]
#     outfits: List[OutfitPlanResponse] = []
#     for i, entry in enumerate(recs):
#         products = [
#             ProductData(
#                 id=str(j),
#                 imageUrl="",
#                 name=p.get("product_name") or "",
#                 price=p.get("product_price") or "",
#                 platform=_platform_from_url(p.get("product_url") or ""),
#             )
#             for j, p in enumerate(entry.get("products", []))
#         ]
#         outfits.append(OutfitPlanResponse(
#             outfitId=f"{plan_id}:{i}",
#             outfitName=entry.get("outfit_name", ""),
#             description="",
#             tags=[],
#             heroImageUrl="",
#             products=products,
#         ))
#     return outfits


# def _recommendation_to_links(recommendation: dict) -> List[ProductLink]:
#     recs = recommendation.get("recommendations", [])
#     links: List[ProductLink] = []
#     for entry in recs:
#         for p in entry.get("products", []):
#             url = p.get("product_url") or ""
#             links.append(ProductLink(
#                 name=p.get("product_name") or "",
#                 url=url,
#                 price=p.get("product_price") or "",
#                 platform=_platform_from_url(url),
#             ))
#     return links


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------

# @app.post("/profile/update", status_code=200)
# async def update_profile(profile: UserProfile):
#     global _profile
#     _profile = profile.model_dump()
#     return {}


# @app.post("/outfit/plan", response_model=List[OutfitPlanResponse])
# async def plan_outfit(request: OutfitPlanRequest):
#     global _current_outfit_id

#     inputs = _crew_inputs(request.prompt, [])
#     loop = asyncio.get_event_loop()

#     try:
#         planning = await loop.run_in_executor(None, Shopai().run_planning, inputs)
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Planning agent failed: {exc}")

#     plan_id = str(uuid.uuid4())
#     _outfit_store[plan_id] = {"planning": planning, "inputs": inputs}
#     _current_outfit_id = plan_id

#     return _planning_to_outfit_list(plan_id, planning)


# @app.post("/outfit/plan/occasional", response_model=List[OutfitPlanResponse])
# async def plan_occasional_outfit(request: OccasionalOutfitRequest):
#     global _current_outfit_id

#     loop = asyncio.get_event_loop()
#     try:
#         result = await loop.run_in_executor(
#             None, lambda: Shopai().plan_occasional_outfit(request.prompt, _profile)
#         )
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Occasional outfit planning failed: {exc}")

#     plan_id = str(uuid.uuid4())
#     _outfit_store[plan_id] = {"recommendation": result, "inputs": {"shopping_request": request.prompt}}
#     _current_outfit_id = plan_id

#     return _recommendation_to_outfit_list(plan_id, result)


# @app.get("/outfit/recommendations", response_model=OutfitPlanResponse)
# async def get_recommendations():
#     if not _current_outfit_id or _current_outfit_id not in _outfit_store:
#         raise HTTPException(status_code=404, detail="No outfit plan found. Call /outfit/plan first.")

#     plan_id = _current_outfit_id
#     entry = _outfit_store[plan_id]
#     planning = entry["planning"]
#     inputs = entry["inputs"]

#     loop = asyncio.get_event_loop()
#     try:
#         recommendation = await loop.run_in_executor(
#             None, lambda: Shopai().run_recommendation(inputs, planning)
#         )
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Recommendation agent failed: {exc}")

#     _outfit_store[plan_id]["recommendation"] = recommendation
#     products = _recommendation_products(recommendation)

#     return _planning_to_response(plan_id, planning, outfit_idx=0, products=products)


# @app.post("/outfit/links", response_model=List[ProductLink])
# async def get_links(request: GetLinksRequest):
#     if not _current_outfit_id or _current_outfit_id not in _outfit_store:
#         raise HTTPException(status_code=404, detail="No outfit plan found. Call /outfit/plan first.")

#     plan_id = _current_outfit_id
#     entry = _outfit_store[plan_id]
#     inputs = entry["inputs"]

#     selected_planning = {
#         "outfits": [
#             {
#                 "outfit_name": "Selected Items",
#                 "items": request.selectedItems,
#                 "rationale": "User-selected items for link lookup",
#             }
#         ]
#     }

#     loop = asyncio.get_event_loop()
#     try:
#         recommendation = await loop.run_in_executor(
#             None, lambda: Shopai().run_recommendation(inputs, selected_planning)
#         )
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Recommendation agent failed: {exc}")

#     _outfit_store[plan_id]["recommendation"] = recommendation
#     return _recommendation_to_links(recommendation)


# class VisualizeRequest(BaseModel):
#     outfitDescription: str
#     bodyType: str
#     height: str = ""


# @app.post("/outfit/visualize", response_model=VisualizeData)
# async def visualize_outfit(req: VisualizeRequest):
#     loop = asyncio.get_event_loop()
#     try:
#         viz = await loop.run_in_executor(
#             None, lambda: Shopai().run_visualization(req.outfitDescription, req.bodyType, req.height)
#         )
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))

#     if error := viz.get("error"):
#         raise HTTPException(status_code=422, detail=error)

#     image_path = viz.get("image_path", "")
#     visual_url = f"/static/{os.path.basename(image_path)}" if image_path else ""

#     return VisualizeData(
#         outfitId="",
#         visualUrl=visual_url,
#         outfitName=req.outfitDescription,
#         items=[],
#         colorPalette=[],
#     )


# @app.get("/health")
# def health():
#     return {"status": "ok"}
