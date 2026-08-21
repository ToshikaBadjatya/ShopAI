package com.shopai.android.data.model

data class UserProfile(
    val height: String = "",
    val bodyType: String = "",
    val favoriteColors: List<String> = emptyList(),
    val styles: List<String> = emptyList()
)

data class OutfitPlanRequest(
    val prompt: String
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

data class VisualizeData(
    val outfitId: String = "",
    val visualUrl: String = "",
    val outfitName: String = "",
    val items: List<ProductData> = emptyList(),
    val colorPalette: List<String> = emptyList()
)

data class ProductLink(
    val name: String = "",
    val url: String = "",
    val price: String = "",
    val platform: String = ""
)

data class GetLinksRequest(
    val outfitId: String,
    val selectedItems: List<String>
)

data class VisualizeRequest(
    val outfitDescription: String,
    val bodyType: String,
    val height: String
)
