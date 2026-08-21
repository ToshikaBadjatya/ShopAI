package com.shopai.android.data.api

import com.shopai.android.data.model.GetLinksRequest
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.ProductLink
import com.shopai.android.data.model.UserProfile
import com.shopai.android.data.model.VisualizeData
import com.shopai.android.data.model.VisualizeRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface ShopAIApiService {

    @POST("profile/update")
    suspend fun updateProfile(@Body profile: UserProfile): Response<Unit>

    @POST("outfit/plan")
    suspend fun planOutfit(@Body request: OutfitPlanRequest): Response<List<OutfitPlanResponse>>

    @POST("outfit/plan/occasional")
    suspend fun planOccasionalOutfit(
        @Body request: OutfitPlanRequest
    ): Response<List<OutfitPlanResponse>>

    @GET("outfit/recommendations")
    suspend fun getRecommendations(): Response<OutfitPlanResponse>

    @POST("outfit/links")
    suspend fun getLinks(@Body request: GetLinksRequest): Response<List<ProductLink>>

    @POST("outfit/visualize")
    suspend fun visualizeOutfit(@Body request: VisualizeRequest): Response<VisualizeData>
}
