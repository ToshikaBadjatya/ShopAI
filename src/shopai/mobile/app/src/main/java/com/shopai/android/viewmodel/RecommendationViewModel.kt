package com.shopai.android.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.GetLinksRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.ProductLink
import com.shopai.android.data.repository.OutfitRepository
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

    private val _selectedItems = MutableStateFlow<Set<String>>(emptySet())
    val selectedItems: StateFlow<Set<String>> = _selectedItems.asStateFlow()

    private val _links = MutableStateFlow<List<ProductLink>?>(null)
    val links: StateFlow<List<ProductLink>?> = _links.asStateFlow()

    private val _isLoadingLinks = MutableStateFlow(false)
    val isLoadingLinks: StateFlow<Boolean> = _isLoadingLinks.asStateFlow()

    init {
        _recommendation.value = OutfitRepository.lastPlanResult
    }

    fun toggleFavorite() {
        _isFavorite.value = !_isFavorite.value
    }

    fun toggleItem(item: String) {
        val current = _selectedItems.value.toMutableSet()
        if (current.contains(item)) current.remove(item) else current.add(item)
        _selectedItems.value = current
    }

    fun regenerate() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                val response = RetrofitClient.apiService.getRecommendations()
                if (response.isSuccessful) {
                    val result = response.body()
                    OutfitRepository.lastPlanResult = result
                    _recommendation.value = result
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

    fun getLinks() {
        val outfitId = _recommendation.value?.outfitId ?: return
        val selected = _selectedItems.value.toList()
        if (selected.isEmpty()) return
        viewModelScope.launch {
            _isLoadingLinks.value = true
            _error.value = null
            try {
                val response = RetrofitClient.apiService.getLinks(GetLinksRequest(outfitId, selected))
                if (response.isSuccessful) {
                    _links.value = response.body()
                } else {
                    _error.value = "Failed to get links"
                }
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _isLoadingLinks.value = false
            }
        }
    }
}
