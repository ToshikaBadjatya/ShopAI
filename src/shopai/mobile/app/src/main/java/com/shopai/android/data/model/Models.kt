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
    val userToken: String? = null,
    /** Continues an existing run; omitted, the backend starts a new one. */
    val runId: String? = null
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

/**
 * One shape for every plan outcome. [kind] says what the body holds:
 * `plan` (outfits populated), `message`, `permission`, `error`, or `status` -
 * the run is still going and [message] says what Sia is doing.
 *
 * [state] is where the run stands: `running` until it `succeeded`, `failed` or
 * was `cancelled`. [step] moves on each time the status line changes.
 */
data class PlanResponse(
    val kind: String = "plan",
    val message: String = "",
    val outfits: List<OutfitPlanResponse> = emptyList(),
    val runId: String = "",
    val errorKind: String = "system_down",
    val state: String = "",
    val step: Int = 0
)
