package com.shopai.android.data.api

import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.UserProfile
import com.shopai.android.data.model.VisualizeData
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ShopAIApiService {
    @POST("profile/update")
    suspend fun updateProfile(@Body profile: UserProfile): Response<Unit>

    @POST("outfit/plan")
    suspend fun planOutfit(@Body request: OutfitPlanRequest): Response<OutfitPlanResponse>

    @GET("outfit/recommendations")
    suspend fun getRecommendations(): Response<OutfitPlanResponse>

    @GET("outfit/visualize/{outfitId}")
    suspend fun visualizeOutfit(@Path("outfitId") outfitId: String): Response<VisualizeData>
}
