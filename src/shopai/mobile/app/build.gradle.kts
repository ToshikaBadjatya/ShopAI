import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
}

// Supabase credentials live in local.properties, which is not checked in.
val localProperties = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

fun localProperty(name: String): String = localProperties.getProperty(name) ?: ""

android {
    namespace = "com.shopai.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.shopai.android"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        // Emulator default; override API_BASE_URL in local.properties for a physical device.
        val apiBaseUrl = localProperty("API_BASE_URL").ifBlank { "http://10.0.2.2:8000/" }
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        buildConfigField("String", "SUPABASE_URL", "\"${localProperty("SUPABASE_URL")}\"")
        buildConfigField("String", "SUPABASE_ANON_KEY", "\"${localProperty("SUPABASE_ANON_KEY")}\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.02.00")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("io.coil-kt:coil-compose:2.5.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.google.code.gson:gson:2.10.1")
    // supabase-kt 2.x is the Kotlin 1.9 line; 3.x (auth-kt) needs Kotlin 2.0+
    implementation("io.github.jan-tennert.supabase:gotrue-kt:2.6.1")
    implementation("io.ktor:ktor-client-okhttp:2.3.13")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
