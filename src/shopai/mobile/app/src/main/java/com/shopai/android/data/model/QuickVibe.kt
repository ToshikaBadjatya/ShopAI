package com.shopai.android.data.model

sealed class QuickVibe(val label: String, val prompt: String) {

    object SummerBrunch : QuickVibe(
        label = "Summer Brunch",
        prompt = "A breezy summer brunch outfit with light pastel tones, flowy fabrics, and comfortable sandals.Show me outfit recommendations and help me choose one."

    )

    object CorporateChic : QuickVibe(
        label = "Corporate Chic",
        prompt = "A polished corporate chic look with a tailored blazer, structured silhouette, and minimal accessories.Show me outfit recommendations and help me choose one."
    )

    object LateNightParty : QuickVibe(
        label = "Late Night Party",
        prompt = "                  ."
    )

    object ScandiMinimal : QuickVibe(
        label = "Scandi Minimal",
        prompt = "A Scandi minimal outfit with neutral tones, clean lines, and understated layering.Show me outfit recommendations and help me choose one."
    )

    object Gorpcore : QuickVibe(
        label = "Gorpcore",
        prompt = "A gorpcore outfit mixing rugged outdoor technical wear with utilitarian layers and earthy tones.Show me outfit recommendations and help me choose one."
    )

    companion object {
        val all: List<QuickVibe> = listOf(
            SummerBrunch, CorporateChic, LateNightParty, ScandiMinimal, Gorpcore
        )
    }
}
