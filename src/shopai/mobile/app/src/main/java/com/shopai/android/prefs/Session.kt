package com.shopai.android.prefs

import android.content.Context
import com.shopai.android.data.model.AuthSession
import com.shopai.android.data.model.UserProfile

object Session {
    private const val PREFS_NAME = "shopai_session"
    private const val KEY_HEIGHT = "height"
    private const val KEY_BODY_TYPE = "body_type"
    private const val KEY_COLORS = "favorite_colors"
    private const val KEY_STYLES = "styles"
    private const val KEY_ACCESS_TOKEN = "access_token"
    private const val KEY_REFRESH_TOKEN = "refresh_token"
    private const val KEY_EXPIRES_AT = "expires_at"
    private const val KEY_EMAIL = "user_email"
    private const val KEY_USER_ID = "user_id"

    fun getProfile(context: Context): UserProfile {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val colors = prefs.getString(KEY_COLORS, "")
            ?.split(",")?.filter { it.isNotBlank() } ?: emptyList()
        val styles = prefs.getString(KEY_STYLES, "")
            ?.split(",")?.filter { it.isNotBlank() } ?: emptyList()
        return UserProfile(
            height = prefs.getString(KEY_HEIGHT, "") ?: "",
            bodyType = prefs.getString(KEY_BODY_TYPE, "") ?: "",
            favoriteColors = colors,
            styles = styles
        )
    }

    fun saveProfile(context: Context, profile: UserProfile) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_HEIGHT, profile.height)
            .putString(KEY_BODY_TYPE, profile.bodyType)
            .putString(KEY_COLORS, profile.favoriteColors.joinToString(","))
            .putString(KEY_STYLES, profile.styles.joinToString(","))
            .apply()
    }

    // ------------------------------------------------------------------ auth

    fun saveAuth(context: Context, session: AuthSession) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_ACCESS_TOKEN, session.accessToken)
            .putString(KEY_REFRESH_TOKEN, session.refreshToken)
            .putLong(KEY_EXPIRES_AT, session.expiresAt)
            .putString(KEY_EMAIL, session.email)
            .putString(KEY_USER_ID, session.userId)
            .apply()
    }

    fun getAuth(context: Context): AuthSession {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return AuthSession(
            accessToken = prefs.getString(KEY_ACCESS_TOKEN, "") ?: "",
            refreshToken = prefs.getString(KEY_REFRESH_TOKEN, "") ?: "",
            expiresAt = prefs.getLong(KEY_EXPIRES_AT, 0L),
            email = prefs.getString(KEY_EMAIL, "") ?: "",
            userId = prefs.getString(KEY_USER_ID, "") ?: ""
        )
    }

    /** True when a token is stored. Says nothing about whether it has expired. */
    fun isLoggedIn(context: Context): Boolean = getAuth(context).isValid

    fun clearAuth(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .remove(KEY_EXPIRES_AT)
            .remove(KEY_EMAIL)
            .remove(KEY_USER_ID)
            .apply()
    }
}
