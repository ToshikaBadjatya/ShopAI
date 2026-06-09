package com.shopai.android.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.ProductData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class RecommendationViewModel : ViewModel() {
    private val _recommendation = MutableStateFlow<OutfitPlanResponse?>(null)
    val recommendation: StateFlow<OutfitPlanResponse?> = _recommendation.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _isFavorite = MutableStateFlow(false)
    val isFavorite: StateFlow<Boolean> = _isFavorite.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        _recommendation.value = OutfitPlanResponse(
            outfitId = "mock-001",
            outfitName = "Modern Corporate Look",
            description = "A sharp, monochromatic base with bold textural contrasts for the modern professional.",
            tags = listOf("Sophisticated", "Productive", "Summer 24"),
            heroImageUrl = "",
            products = listOf(
                ProductData("1", "", "Tailored Charcoal Blazer", "\$189.00", "Amazon"),
                ProductData("2", "", "Structured Leather Tote", "\$245.00", "Myntra"),
                ProductData("3", "", "Pointed-Toe Suede Pumps", "\$120.00", "Amazon"),
                ProductData("4", "", "Ivory Silk Blouse", "\$95.00", "Myntra"),
                ProductData("5", "", "Classic Minimalist Watch", "\$310.00", "Amazon")
            )
        )
    }

    fun toggleFavorite() {
        _isFavorite.value = !_isFavorite.value
    }

    fun regenerate() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                val response = RetrofitClient.apiService.getRecommendations()
                if (response.isSuccessful) {
                    _recommendation.value = response.body()
                } else {
                    _error.value = "Failed to load recommendations"
                }
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
}
