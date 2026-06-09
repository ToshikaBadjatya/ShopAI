package com.shopai.android.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.shopai.android.screens.MoodScreen
import com.shopai.android.screens.ProfileScreen
import com.shopai.android.screens.RecommendationScreen

sealed class Screen(val route: String) {
    object Mood : Screen("mood")
    object Profile : Screen("profile")
    object Recommendation : Screen("recommendation")
}

@Composable
fun NavGraph(
    navController: NavHostController = rememberNavController(),
    startDestination: String = Screen.Mood.route
) {
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(Screen.Mood.route) {
            MoodScreen(
                onBack = { navController.popBackStack() },
                onPlanOutfit = { _ ->
                    navController.navigate(Screen.Recommendation.route)
                }
            )
        }

        composable(Screen.Profile.route) {
            ProfileScreen(
                onBack = { navController.popBackStack() },
                onSaveProfile = {
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Mood.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Recommendation.route) {
            RecommendationScreen(
                onBack = {
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Mood.route) { inclusive = true }
                    }
                },
                onRegenerate = { /* trigger re-fetch */ }
            )
        }
    }
}
