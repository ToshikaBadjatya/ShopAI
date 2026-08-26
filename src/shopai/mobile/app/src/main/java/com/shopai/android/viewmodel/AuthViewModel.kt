package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.SupabaseAuth
import com.shopai.android.data.model.AuthSession
import com.shopai.android.prefs.Session
import io.github.jan.supabase.gotrue.OtpType
import io.github.jan.supabase.gotrue.providers.builtin.Email
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class AuthMode { SIGN_IN, SIGN_UP }

/**
 * Email + password auth against Supabase. Tokens land in [Session] on success;
 * the screen watches [loggedIn] to know when to move on.
 */
class AuthViewModel(application: Application) : AndroidViewModel(application) {

    private val _mode = MutableStateFlow(AuthMode.SIGN_IN)
    val mode: StateFlow<AuthMode> = _mode.asStateFlow()

    private val _email = MutableStateFlow("")
    val email: StateFlow<String> = _email.asStateFlow()

    private val _password = MutableStateFlow("")
    val password: StateFlow<String> = _password.asStateFlow()

    private val _confirmPassword = MutableStateFlow("")
    val confirmPassword: StateFlow<String> = _confirmPassword.asStateFlow()

    private val _submitting = MutableStateFlow(false)
    val submitting: StateFlow<Boolean> = _submitting.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    /** True while the signed-in-with address is known to be unconfirmed. */
    private val _needsConfirmation = MutableStateFlow(false)
    val needsConfirmation: StateFlow<Boolean> = _needsConfirmation.asStateFlow()

    /** Set when sign-up succeeded but the account still needs email confirmation. */
    private val _notice = MutableStateFlow<String?>(null)
    val notice: StateFlow<String?> = _notice.asStateFlow()

    private val _loggedIn = MutableStateFlow(false)
    val loggedIn: StateFlow<Boolean> = _loggedIn.asStateFlow()

    fun setMode(mode: AuthMode) {
        _mode.value = mode
        _error.value = null
        _notice.value = null
        _needsConfirmation.value = false
    }

    fun updateEmail(value: String) {
        _email.value = value.trim()
    }

    fun updatePassword(value: String) {
        _password.value = value
    }

    fun updateConfirmPassword(value: String) {
        _confirmPassword.value = value
    }

    fun submit() {
        if (_submitting.value) return
        if (_mode.value == AuthMode.SIGN_IN) signIn() else signUp()
    }

    private fun signIn() {


        _error.value = null
        _notice.value = null
        _submitting.value = true
        viewModelScope.launch {
            try {
                SupabaseAuth.auth.signInWith(Email) {
                    email = _email.value
                    password = _password.value
                }
                persistSession()
            } catch (e: Exception) {
                _error.value = readableError(e)
            } finally {
                _submitting.value = false
            }
        }
    }

    private fun signUp() {
       

        _error.value = null
        _notice.value = null
        _submitting.value = true
        viewModelScope.launch {
            try {
                SupabaseAuth.auth.signUpWith(Email) {
                    email = _email.value
                    password = _password.value
                }
                // With email confirmation on, sign-up returns no session - the
                // account is not usable until the link is clicked.
                if (SupabaseAuth.auth.currentSessionOrNull() == null) {
                    _notice.value =
                        "Check your email to confirm your account, then sign in."
                    _mode.value = AuthMode.SIGN_IN
                    _password.value = ""
                    _confirmPassword.value = ""
                } else {
                    persistSession()
                }
            } catch (e: Exception) {
                _error.value = readableError(e)
            } finally {
                _submitting.value = false
            }
        }
    }

    /**
     * Sends the confirmation link again. Only reachable once a sign-in has come
     * back unconfirmed, so there is an address worth resending to.
     */
    fun resendConfirmation() {
        if (_submitting.value || _email.value.isBlank()) return
        _error.value = null
        _submitting.value = true
        viewModelScope.launch {
            try {
                SupabaseAuth.auth.resendEmail(OtpType.Email.SIGNUP, _email.value)
                _notice.value = "Confirmation link sent to ${_email.value}."
                _needsConfirmation.value = false
            } catch (e: Exception) {
                _error.value = readableError(e)
            } finally {
                _submitting.value = false
            }
        }
    }

    fun signOut() {
        viewModelScope.launch {
            try {
                SupabaseAuth.auth.signOut()
            } catch (e: Exception) {
                // Local state is dropped either way - the point is to not leave
                // them stuck signed in on a device.
                _error.value = readableError(e)
            }
            Session.clearAuth(getApplication())
            _loggedIn.value = false
        }
    }

    private fun persistSession() {
        val session = SupabaseAuth.auth.currentSessionOrNull()
        if (session == null) {
            _error.value = "Signed in, but no session came back. Try again."
            return
        }
        Session.saveAuth(
            getApplication(),
            AuthSession(
                accessToken = session.accessToken,
                refreshToken = session.refreshToken,
                expiresAt = session.expiresAt.epochSeconds,
                email = session.user?.email ?: _email.value,
                userId = session.user?.id ?: ""
            )
        )
        _loggedIn.value = true
    }

    private fun validate(checkConfirmation: Boolean): String? = when {
        !SupabaseAuth.isConfigured ->
            "Supabase isn't configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to local.properties."
        _email.value.isBlank() -> "Enter your email."
        _password.value.isBlank() -> "Enter your password."
        checkConfirmation && _password.value != _confirmPassword.value ->
            "Passwords don't match."
        else -> null
    }

    /** GoTrue reports an unconfirmed account as `email_not_confirmed`. */
    private fun isUnconfirmed(e: Exception): Boolean =
        e.message?.contains("not_confirmed", ignoreCase = true) == true ||
            e.message?.contains("not confirmed", ignoreCase = true) == true

    private fun readableError(e: Exception): String = when {
        isUnconfirmed(e) ->
            "This email hasn't been confirmed yet. Check your inbox for the link, or resend it."
        e.message?.contains("invalid_credentials", ignoreCase = true) == true ||
            e.message?.contains("Invalid login", ignoreCase = true) == true ->
            "Wrong email or password."
        e.message?.contains("already registered", ignoreCase = true) == true ->
            "That email is already registered - sign in instead."
        else -> e.message?.takeIf { it.isNotBlank() } ?: "Something went wrong. Try again."
    }
}
