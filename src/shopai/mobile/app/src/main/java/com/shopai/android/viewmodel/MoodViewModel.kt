package com.shopai.android.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MoodViewModel : ViewModel() {
    private val _moodText = MutableStateFlow("")
    val moodText: StateFlow<String> = _moodText.asStateFlow()

    private val _selectedVibes = MutableStateFlow<Set<String>>(emptySet())
    val selectedVibes: StateFlow<Set<String>> = _selectedVibes.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _planResult = MutableStateFlow<OutfitPlanResponse?>(null)
    val planResult: StateFlow<OutfitPlanResponse?> = _planResult.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    fun updateMoodText(text: String) {
        _moodText.value = text
    }

    fun toggleVibe(vibe: String) {
        _selectedVibes.value = if (_selectedVibes.value.contains(vibe)) {
            _selectedVibes.value - vibe
        } else {
            _selectedVibes.value + vibe
        }
    }

    fun planOutfit() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                val response = RetrofitClient.apiService.planOutfit(
                    OutfitPlanRequest(
                        moodText = _moodText.value,
                        vibes = _selectedVibes.value.toList()
                    )
                )
                if (response.isSuccessful) {
                    _planResult.value = response.body()
                } else {
                    _error.value = "Failed to plan outfit"
                }
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
}
