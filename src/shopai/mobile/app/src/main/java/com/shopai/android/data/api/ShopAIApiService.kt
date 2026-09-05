package com.shopai.android.data.api

import com.shopai.android.data.model.ClearTaskRequest
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.PlanResponse
import com.shopai.android.data.model.UserProfile
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

interface ShopAIApiService {

    @POST("profile/update")
    suspend fun updateProfile(@Body profile: UserProfile): Response<Unit>

    /** Not implemented server-side yet; callers must tolerate a 404. */
    @POST("task/clear")
    suspend fun clearTask(@Body request: ClearTaskRequest): Response<Unit>

    @POST("outfit/plan/regular")
    suspend fun planRegularOutfit(@Body request: OutfitPlanRequest): Response<PlanResponse>

    @POST("outfit/plan/occasional")
    suspend fun planOccasionalOutfit(@Body request: OutfitPlanRequest): Response<PlanResponse>
}
