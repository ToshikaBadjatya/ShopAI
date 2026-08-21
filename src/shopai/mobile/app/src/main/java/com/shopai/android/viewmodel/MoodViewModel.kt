package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.QuickVibe
import com.shopai.android.data.repository.OutfitRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MoodViewModel(application: Application) : AndroidViewModel(application) {
    private val _moodText = MutableStateFlow("")
    val moodText: StateFlow<String> = _moodText.asStateFlow()

    private val _selectedVibes = MutableStateFlow<Set<String>>(emptySet())
    val selectedVibes: StateFlow<Set<String>> = _selectedVibes.asStateFlow()

    val quickVibes: List<QuickVibe> = QuickVibe.all

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

    fun selectQuickVibe(vibe: QuickVibe) {
        if (_selectedVibes.value.contains(vibe.label)) {
            _selectedVibes.value = emptySet()
        } else {
            _selectedVibes.value = setOf(vibe.label)
            _moodText.value = vibe.prompt
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
