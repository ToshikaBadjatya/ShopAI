package com.shopai.android.data.model

data class UserProfile(
    val height: String = "",
    val bodyType: String = "",
    val favoriteColors: List<String> = emptyList(),
    val styles: List<String> = emptyList()
)

data class OutfitPlanRequest(
    val prompt: String,
    /** Identifies the shopper to the backend; nothing verifies it yet. */
    val userToken: String? = null
)

data class ProductData(
    val id: String = "",
    val imageUrl: String = "",
    val name: String = "",
    val price: String = "",
    val platform: String = ""
)

data class OutfitPlanResponse(
    val outfitId: String = "",
    val outfitName: String = "",
    val description: String = "",
    val tags: List<String> = emptyList(),
    val heroImageUrl: String = "",
    val products: List<ProductData> = emptyList()
)

/** Asks the backend to drop whatever task ledger it is holding for this user. */
data class ClearTaskRequest(
    val userToken: String? = null
)

/**
 * One shape for every plan outcome. [kind] says what the body holds:
 * `plan` (outfits populated), `message`, `permission`, or `error`.
 */
data class PlanResponse(
    val kind: String = "plan",
    val message: String = "",
    val outfits: List<OutfitPlanResponse> = emptyList(),
    val errorKind: String = "system_down"
)
