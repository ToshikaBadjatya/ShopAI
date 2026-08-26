package com.shopai.android.data.api

import com.shopai.android.BuildConfig
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
}
