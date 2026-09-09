"""The word lists ShopAI matches requests against.

Shared by the guardrail (which asks "is this about clothes at all?") and by
clarity scoring (which asks "how specific is it?"). Those two questions want
different granularity, which is why GARMENT_TERMS is narrower than
FASHION_TERMS rather than the same set reused.
"""

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

OUT_OF_SCOPE_TERMS = {
    "weather", "forecast", "temperature", "news", "stock", "crypto", "recipe",
    "cook", "code", "python", "javascript", "debug", "homework", "math",
    "translate", "flight", "hotel", "medicine", "doctor", "symptom", "diagnose",
    "loan", "tax", "invest", "score", "match", "movie", "song", "lyrics",
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
