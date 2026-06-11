package com.shopai.android.prefs

import android.content.Context
import com.shopai.android.data.model.UserProfile

object Session {
    private const val PREFS_NAME = "shopai_session"
    private const val KEY_HEIGHT = "height"
    private const val KEY_BODY_TYPE = "body_type"
    private const val KEY_COLORS = "favorite_colors"
    private const val KEY_STYLES = "styles"

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
}
