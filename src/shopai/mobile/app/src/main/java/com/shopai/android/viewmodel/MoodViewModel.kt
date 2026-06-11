package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.repository.OutfitRepository
import com.shopai.android.prefs.Session
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MoodViewModel(application: Application) : AndroidViewModel(application) {
    private val _moodText = MutableStateFlow("")
    val moodText: StateFlow<String> = _moodText.asStateFlow()

    private val _selectedVibes = MutableStateFlow<Set<String>>(emptySet())
    val selectedVibes: StateFlow<Set<String>> = _selectedVibes.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val     _planIdeas = MutableStateFlow<List<OutfitPlanResponse>>(emptyList())
    val planIdeas: StateFlow<List<OutfitPlanResponse>> = _planIdeas.asStateFlow()

    private val _selectedOutfit = MutableStateFlow<OutfitPlanResponse?>(null)
    val selectedOutfit: StateFlow<OutfitPlanResponse?> = _selectedOutfit.asStateFlow()

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
            _planIdeas.value = emptyList()
            try {
                val profile = Session.getProfile(getApplication())
                val vibesText = _selectedVibes.value.joinToString(", ")
                val fullMoodText = when {
                    _moodText.value.isNotEmpty() && vibesText.isNotEmpty() ->
                        "${_moodText.value}. Vibe: $vibesText"
                    _moodText.value.isNotEmpty() -> _moodText.value
                    else -> vibesText
                }
                val request = OutfitPlanRequest(moodText = fullMoodText, profile = profile)
                val response = RetrofitClient.apiService.planOutfit(request)
                if (response.isSuccessful) {
                    _planIdeas.value = response.body() ?: emptyList()
                } else {
                    _error.value = "Failed to plan outfit: ${response.code()}"
                }
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun selectOutfit(outfit: OutfitPlanResponse) {
        OutfitRepository.lastPlanResult = outfit
        _selectedOutfit.value = outfit
    }

    fun clearSelectedOutfit() {
        _selectedOutfit.value = null
    }
}
