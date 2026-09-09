package com.shopai.android.data.api

import android.content.Context
import com.shopai.android.BuildConfig
import com.shopai.android.data.model.AuthSession
import com.shopai.android.prefs.Session
import io.github.jan.supabase.SupabaseClient
import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.gotrue.Auth
import io.github.jan.supabase.gotrue.auth

/**
 * Supabase entry point. Credentials come from local.properties via BuildConfig,
 * so nothing secret lives in source.
 */
object SupabaseAuth {

    /** The builder adds the scheme itself, so it wants a bare host. */
    private val host: String = BuildConfig.SUPABASE_URL
        .removePrefix("https://")
        .removePrefix("http://")
        .trimEnd('/')

    val isConfigured: Boolean
        get() = host.isNotBlank() && BuildConfig.SUPABASE_ANON_KEY.isNotBlank()

    val client: SupabaseClient by lazy {
        createSupabaseClient(supabaseUrl = host, supabaseKey = BuildConfig.SUPABASE_ANON_KEY) {
            install(Auth) {
                // prefs/Session owns persistence, so the SDK's own storage stays out of it.
                autoLoadFromStorage = false
                autoSaveToStorage = false
            }
        }
    }

    val auth get() = client.auth

    /** Refresh happens a bit early, not exactly at expiry - a request already in
     * flight when the clock hits zero should not have to race a refresh. */
    private const val REFRESH_BUFFER_SECONDS = 60L

    /**
     * The access token to send with the next request, refreshed first if it is
     * expired or close to it.
     *
     * Soft by design: a failed refresh - a revoked or already-expired refresh
     * token, a network error - is not this function's problem to solve. It
     * returns whatever token is stored, stale or not, rather than throwing or
     * forcing the caller into a sign-out. The backend already treats a stale
     * token as routine (it drops what needs auth and carries on), so a caller
     * degrading the same way is consistent, not risky.
     */
    suspend fun freshAccessToken(context: Context): String? {
        val session = Session.getAuth(context)
        if (!session.isValid) return null

        val nowPlusBuffer = System.currentTimeMillis() / 1000 + REFRESH_BUFFER_SECONDS
        if (session.expiresAt == 0L || session.expiresAt > nowPlusBuffer) {
            return session.accessToken
        }

        if (session.refreshToken.isBlank()) return session.accessToken

        return try {
            val refreshed = auth.refreshSession(session.refreshToken)
            Session.saveAuth(
                context,
                AuthSession(
                    accessToken = refreshed.accessToken,
                    refreshToken = refreshed.refreshToken,
                    expiresAt = refreshed.expiresAt.epochSeconds,
                    email = session.email,
                    userId = session.userId
                )
            )
            refreshed.accessToken
        } catch (e: Exception) {
            // Soft failure - see the doc comment above.
            session.accessToken
        }
    }
}
