package com.shopai.android.data.api

import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.PlanResponse
import com.shopai.android.data.model.UserProfile
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

interface ShopAIApiService {

    @POST("profile/update")
    suspend fun updateProfile(@Body profile: UserProfile): Response<Unit>

    /**
     * The chat has ended: drops the task ledger for one run. No body - the ledger is
     * keyed on runId alone. When [authorization] is `Bearer <token>` the server also
     * summarises the finished chat and learns the shopper's profile from it; a null
     * value omits the header and only the ledger is cleared.
     */
    @DELETE("task/{runId}")
    suspend fun clearTask(
        @Path("runId") runId: String,
        @Header("Authorization") authorization: String? = null,
    ): Response<Unit>

    @POST("outfit/plan/regular")
    suspend fun planRegularOutfit(@Body request: OutfitPlanRequest): Response<PlanResponse>

    @POST("outfit/plan/occasional")
    suspend fun planOccasionalOutfit(@Body request: OutfitPlanRequest): Response<PlanResponse>
}
