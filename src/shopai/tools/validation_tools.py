"""Tools the validator agent uses to interrogate a request before anything acts on it.

Each tool answers one narrow question and returns JSON. They are deliberately
deterministic - keyword and heuristic checks that cost nothing and run in
milliseconds - so the agent spends its own reasoning on the judgement call
rather than on lookups.

New checks can be added at runtime with `register_validator_tool`; the agent
picks up whatever is registered when it is built.
"""

import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

COLOR_TERMS = {
    "black", "white", "ivory", "cream", "beige", "nude", "tan", "brown", "chocolate",
    "grey", "gray", "charcoal", "silver", "gold", "rose", "copper", "bronze",
    "red", "maroon", "burgundy", "wine", "crimson", "scarlet", "rust",
    "pink", "blush", "fuchsia", "magenta", "coral", "peach", "salmon",
    "orange", "amber", "mustard", "yellow", "lemon",
    "green", "olive", "emerald", "sage", "mint", "teal", "forest",
    "blue", "navy", "cobalt", "indigo", "denim", "powder", "turquoise", "aqua",
    "purple", "lavender", "lilac", "violet", "plum", "mauve",
    "pastel", "pastels", "neon", "metallic", "monochrome", "neutral", "neutrals",
    "jewel", "earthy", "muted", "bright", "dark", "light", "warm", "cool",
}

SILHOUETTE_TERMS = {
    "silhouette", "silhouettes", "fitted", "loose", "oversized", "relaxed", "tailored",
    "structured", "flowy", "draped", "bodycon", "wrap", "shift", "slip", "sheath",
    "a-line", "aline", "empire", "peplum", "flared", "straight", "skinny", "wide-leg",
    "wideleg", "bootcut", "cropped", "high-waisted", "highwaisted", "low-rise",
    "midi", "maxi", "mini", "knee-length", "ankle-length", "floor-length",
    "sleeveless", "strapless", "halter", "off-shoulder", "puffed", "balloon",
    "v-neck", "vneck", "square-neck", "boat-neck", "collared", "layered", "asymmetric",
}

EVENT_TERMS = {
    "party", "wedding", "marriage", "shaadi", "engagement", "reception", "sangeet",
    "mehendi", "haldi", "cocktail", "birthday", "anniversary", "graduation",
    "festival", "diwali", "holi", "eid", "christmas", "navratri", "puja", "pooja",
    "date", "brunch", "dinner", "lunch", "night-out", "clubbing", "concert",
    "interview", "presentation", "meeting", "conference", "offsite", "farewell",
    "travel", "vacation", "holiday", "honeymoon", "beach", "resort", "cruise",
    "gym", "workout", "yoga", "run", "hike", "college", "school", "reunion",
    "funeral", "temple", "church", "baby-shower", "housewarming",
}

VIBE_TERMS = {
    "corporate", "professional", "business", "boardroom", "workwear",
    "casual", "smart-casual", "semi-formal", "formal", "black-tie",
    "chic", "elegant", "classy", "sophisticated", "polished", "minimal", "minimalist",
    "bold", "dramatic", "statement", "edgy", "grunge", "punk", "rebel",
    "boho", "bohemian", "romantic", "feminine", "flirty", "playful", "quirky",
    "vintage", "retro", "classic", "timeless", "preppy", "sporty", "athleisure",
    "streetwear", "street", "y2k", "coquette", "cottagecore", "clean-girl",
    "glam", "glamorous", "sultry", "sexy", "cozy", "comfy", "effortless",
    "traditional", "indo-western", "fusion", "festive", "summery", "wintery",
}

FASHION_TERMS = {
    "outfit", "outfits", "look", "looks", "style", "styling", "stylish", "wear",
    "wearing", "dress", "dresses", "shirt", "tshirt", "t-shirt", "top", "tops",
    "jeans", "trousers", "pants", "skirt", "saree", "kurta", "lehenga", "suit",
    "blazer", "jacket", "coat", "shoes", "heels", "sneakers", "sandals", "boots",
    "bag", "handbag", "accessory", "accessories", "jewellery", "jewelry",
    "wardrobe", "fashion", "fit", "size", "colour", "color", "fabric", "brand",
    "shop", "shopping", "buy", "purchase", "budget", "price", "sale", "discount",
    "clothes", "clothing", "garment", "garments", "attire", "apparel", "outfitted",
    "jumpsuit", "gown", "tee", "hoodie", "sweater", "scarf", "belt", "watch",
    "sunglasses", "ethnic", "western", "denim", "leather", "silk", "satin", "velvet",
    "cotton", "linen", "chiffon", "georgette", "organza", "wool", "knit", "lace",
    "co-ord", "coord", "kurti", "salwar", "anarkali", "sherwani", "dupatta", "palazzo",
    "shrug", "cardigan", "waistcoat", "trench", "bomber", "camisole", "bodysuit",
    "loafers", "flats", "mules", "wedges", "juttis", "kolhapuris", "clutch", "tote",
} | COLOR_TERMS | SILHOUETTE_TERMS

# An occasion is an event, or a vibe specific enough to dress for ("corporate look").
OCCASION_TERMS = EVENT_TERMS | VIBE_TERMS | {"office", "work"}

OUT_OF_SCOPE_TERMS = {
    "weather", "forecast", "temperature", "news", "stock", "crypto", "recipe",
    "cook", "code", "python", "javascript", "debug", "homework", "math",
    "translate", "flight", "hotel", "medicine", "doctor", "symptom", "diagnose",
    "loan", "tax", "invest", "score", "match", "movie", "song", "lyrics",
}

DISALLOWED_PATTERNS = [
    (r"\bhack(ing|ed)?\b", "hacking"),
    (r"\bexploit\b|\bmalware\b|\bransomware\b|\bkeylogger\b", "malicious software"),
    (r"\bsteal\b|\bstolen\b|\bshoplift(ing)?\b|\bcounterfeit\b|\bfake receipts?\b", "theft or fraud"),
    (r"\bcredit card (number|details)\b|\bcvv\b|\bcard dump\b", "payment credential misuse"),
    (r"\bweapon\b|\bgun\b|\bexplosive\b|\bbomb\b", "weapons"),
    (r"\bdrugs?\b|\bcocaine\b|\bheroin\b|\bmeth\b", "illicit drugs"),
    (r"\bnude\b|\bnaked\b|\bporn\b|\bsexual\b", "sexual content"),
    (r"\bkill\b|\bharm (myself|yourself)\b|\bsuicide\b", "harm"),
]

# What a plan needs before it is worth running the crew.
CONTEXT_SLOTS = {
    "occasion": OCCASION_TERMS,
    "garment": FASHION_TERMS,
    "color": COLOR_TERMS,
    "silhouette": SILHOUETTE_TERMS,
    "budget": {"budget", "under", "cheap", "affordable", "premium", "rupees", "inr", "rs", "price"},
    "timing": {"today", "tonight", "tomorrow", "weekend", "friday", "saturday", "sunday",
               "monday", "tuesday", "wednesday", "thursday", "morning", "evening", "night"},
}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z'-]*", text.lower()))


def _hits(text: str, vocabulary: set[str]) -> list[str]:
    return sorted(_words(text) & vocabulary)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class RequestInput(BaseModel):
    """Every validation tool takes the raw user request."""

    request: str = Field(..., description="The user's request, verbatim.")


class IntentValidatorTool(BaseTool):
    name: str = "intent_validator"
    description: str = (
        "Reads a user request and reports which intent bucket its wording points to: "
        "shopping_or_styling, other_domain, or unclear. Returns JSON with the matched "
        "terms behind the call. A signal, not a verdict - weigh it with the other checks."
    )
    args_schema: Type[BaseModel] = RequestInput

    def _run(self, request: str) -> str:
        fashion = _hits(request, FASHION_TERMS)
        occasion = _hits(request, OCCASION_TERMS)
        other = _hits(request, OUT_OF_SCOPE_TERMS)

        if fashion or occasion:
            bucket = "shopping_or_styling" if len(fashion) + len(occasion) >= len(other) else "unclear"
        elif other:
            bucket = "other_domain"
        else:
            bucket = "unclear"

        return json.dumps({
            "intent": bucket,
            "fashion_terms": fashion,
            "occasion_terms": occasion,
            "colors": _hits(request, COLOR_TERMS),
            "silhouettes": _hits(request, SILHOUETTE_TERMS),
            "events": _hits(request, EVENT_TERMS),
            "vibes": _hits(request, VIBE_TERMS),
            "other_domain_terms": other,
        })


class RelevanceFinderTool(BaseTool):
    name: str = "relevance_finder"
    description: str = (
        "Scores how relevant a request is to fashion, styling and shopping, from 0.0 to "
        "1.0, and says which signals produced the score. Use it to separate a request "
        "that merely mentions clothing from one that is actually asking for a look."
    )
    args_schema: Type[BaseModel] = RequestInput

    def _run(self, request: str) -> str:
        words = _words(request)
        if not words:
            return json.dumps({"relevance": 0.0, "verdict": "irrelevant", "signals": []})

        fashion = _hits(request, FASHION_TERMS)
        occasion = _hits(request, OCCASION_TERMS)
        other = _hits(request, OUT_OF_SCOPE_TERMS)

        score = (len(fashion) * 2 + len(occasion)) / (len(fashion) * 2 + len(occasion) + len(other) * 3 + 1)
        score = round(min(score, 1.0), 2)

        verdict = "relevant" if score >= 0.5 else "borderline" if score >= 0.2 else "irrelevant"
        return json.dumps({
            "relevance": score,
            "verdict": verdict,
            "signals": fashion + occasion,
            "competing_signals": other,
        })


class InappropriateFlagTool(BaseTool):
    name: str = "flag_inappropriate"
    description: str = (
        "Checks a request against the categories ShopAI must refuse - hacking, fraud, "
        "theft, weapons, drugs, sexual content, harm. Returns flagged true/false with "
        "the category. A flag means refuse, whatever the other checks say."
    )
    args_schema: Type[BaseModel] = RequestInput

    def _run(self, request: str) -> str:
        lowered = request.lower()
        categories = [name for pattern, name in DISALLOWED_PATTERNS if re.search(pattern, lowered)]
        return json.dumps({
            "flagged": bool(categories),
            "categories": categories,
            "action": "refuse" if categories else "allow",
        })


class IncompleteContextTool(BaseTool):
    name: str = "incomplete_context"
    description: str = (
        "Reports which planning details the request is missing - occasion, garment, "
        "budget, timing - and suggests the single most useful follow-up question. "
        "Use it to decide whether to ask one question before planning."
    )
    args_schema: Type[BaseModel] = RequestInput

    def _run(self, request: str) -> str:
        present = {slot: _hits(request, vocab) for slot, vocab in CONTEXT_SLOTS.items()}
        missing = [slot for slot, hits in present.items() if not hits]

        questions = {
            "occasion": "What's the occasion?",
            "garment": "What kind of pieces are you after?",
            "color": "Any colours you want to lean into?",
            "silhouette": "What kind of fit or shape are you after?",
            "budget": "Roughly what budget are you working with?",
            "timing": "When do you need it for?",
        }
        # Occasion and garment are what planning actually needs; the rest are nice to have.
        blocking = [slot for slot in ("garment", "occasion") if slot in missing]

        return json.dumps({
            "present": {slot: hits for slot, hits in present.items() if hits},
            "missing": missing,
            "sufficient": not blocking,
            "suggested_question": questions[blocking[0]] if blocking else "",
        })


# ---------------------------------------------------------------------------
# Registry - lets checks be added at runtime
# ---------------------------------------------------------------------------

_DEFAULT_TOOLS: list[BaseTool] = [
    IntentValidatorTool(),
    RelevanceFinderTool(),
    InappropriateFlagTool(),
    IncompleteContextTool(),
]

_EXTRA_TOOLS: list[BaseTool] = []


def register_validator_tool(tool: BaseTool) -> None:
    """Add a check the validator will use from its next build onwards.

    Registering a tool whose name is already known replaces it, so a caller can
    override a default check rather than ending up with two of them.
    """
    global _EXTRA_TOOLS
    _EXTRA_TOOLS = [t for t in _EXTRA_TOOLS if t.name != tool.name] + [tool]


def unregister_validator_tool(name: str) -> None:
    """Drop a previously registered check. Defaults cannot be removed."""
    global _EXTRA_TOOLS
    _EXTRA_TOOLS = [t for t in _EXTRA_TOOLS if t.name != name]


def validator_tools() -> list[BaseTool]:
    """Every check the validator should run: defaults, plus anything registered.

    A registered tool sharing a default's name wins - that is how a default is
    swapped out without editing this file.
    """
    overridden = {t.name for t in _EXTRA_TOOLS}
    return [t for t in _DEFAULT_TOOLS if t.name not in overridden] + list(_EXTRA_TOOLS)


# ---------------------------------------------------------------------------
# Direct verdict - no agent, no LLM
# ---------------------------------------------------------------------------

# What the user is actually shown. Fixed wording, one line per verdict: the
# reason a request was turned down is diagnostic detail, not something to
# explain back to whoever asked.
REJECTION_MESSAGES = {
    "needs_clarification": "I cannot understand your request.",
        "not_allowed": "I'm not allowed to give these answers.",

    "out_of_scope": "This is a shopping bot, I cannot help with that request.",
}

def validate_request(prompt: str) -> dict:
    """Run every registered check and answer one question: does this pass?

    The guardrail no longer names what a request is - that judgement belongs to
    the Recommendation Master agent downstream. All this decides is whether the
    request reaches it, and if not, which line the user is shown.

    Returns:
        {"allowed": bool,
         "rejection": "" | "not_allowed" | "out_of_scope" | "needs_clarification",
         "message": "...",        # what the user sees; empty when allowed
         "reason": "...",         # diagnostic, never shown
         "clarification": "...",  # follow-up question, when there is one
         "findings": {tool_name: parsed_output, ...}}
    """
    findings: dict[str, dict] = {}
    for tool in validator_tools():
        try:
            findings[tool.name] = json.loads(tool._run(prompt))
        except Exception as exc:  # a broken check must not wave a request through
            findings[tool.name] = {"error": str(exc)}

    def blocked(rejection: str, reason: str, clarification: str = "") -> dict:
        return {
            "allowed": False,
            "rejection": rejection,
            "message": REJECTION_MESSAGES.get(rejection, ""),
            "reason": reason,
            "clarification": clarification,
            "findings": findings,
        }

    if not prompt.strip():
        return blocked(
            "needs_clarification",
            "The request was empty.",
            "What are you shopping for?",
        )

    flagged = findings.get("flag_inappropriate", {})
    if flagged.get("flagged"):
        categories = ", ".join(flagged.get("categories", [])) or "disallowed content"
        return blocked("not_allowed", f"The request involves {categories}.")

    intent_check = findings.get("intent_validator", {})
    relevance = findings.get("relevance_finder", {})

    if intent_check.get("intent") == "other_domain" or relevance.get("verdict") == "irrelevant":
        competing = ", ".join(relevance.get("competing_signals", [])) or "another topic"
        return blocked(
            "out_of_scope",
            f"That reads as a question about {competing}, not styling or shopping.",
        )

    context = findings.get("incomplete_context", {})
    if not context.get("sufficient", False):
        missing = ", ".join(context.get("missing", [])) or "details"
        return blocked(
            "needs_clarification",
            f"Not enough to plan with yet - missing {missing}.",
            context.get("suggested_question") or "Could you tell me a bit more?",
        )

    return {
        "allowed": True,
        "rejection": "",
        "message": "",
        "reason": "Passed the guardrail; handing over to the master agent.",
        "clarification": "",
        "findings": findings,
    }
