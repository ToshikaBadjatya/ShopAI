package com.shopai.android.data.model

/** What we keep from a Supabase sign-in. */
data class AuthSession(
    val accessToken: String = "",
    val refreshToken: String = "",
    /** Epoch seconds; 0 when the server did not say. */
    val expiresAt: Long = 0L,
    val email: String = "",
    val userId: String = ""
) {
    val isValid: Boolean get() = accessToken.isNotBlank()
}
