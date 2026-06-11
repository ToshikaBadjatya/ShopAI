package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.UserProfile
import com.shopai.android.prefs.Session
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ProfileViewModel(application: Application) : AndroidViewModel(application) {
    private val _profileState = MutableStateFlow(Session.getProfile(application))
    val profileState: StateFlow<UserProfile> = _profileState.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    fun updateHeight(height: String) {
        _profileState.value = _profileState.value.copy(height = height)
    }

    fun updateBodyType(bodyType: String) {
        _profileState.value = _profileState.value.copy(bodyType = bodyType)
    }

    fun toggleColor(color: String) {
        val current = _profileState.value.favoriteColors.toMutableList()
        if (current.contains(color)) current.remove(color) else current.add(color)
        _profileState.value = _profileState.value.copy(favoriteColors = current)
    }

    fun toggleStyle(style: String) {
        val current = _profileState.value.styles.toMutableList()
        if (current.contains(style)) current.remove(style) else current.add(style)
        _profileState.value = _profileState.value.copy(styles = current)
    }

    fun saveProfile() {
        Session.saveProfile(getApplication(), _profileState.value)
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                RetrofitClient.apiService.updateProfile(_profileState.value)
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _isLoading.value = false
            }
        }
    }
}
