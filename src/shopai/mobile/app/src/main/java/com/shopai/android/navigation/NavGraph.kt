package com.shopai.android.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.shopai.android.data.model.VisualizeData
import com.shopai.android.screens.MoodScreen
import com.shopai.android.screens.ProfileScreen
import com.shopai.android.screens.RecommendationScreen
import com.shopai.android.screens.VisualizeScreen
import com.shopai.android.viewmodel.MoodViewModel
import com.shopai.android.viewmodel.ProfileViewModel
import com.shopai.android.viewmodel.RecommendationViewModel
import com.shopai.android.viewmodel.VisualizeViewModel

sealed class Screen(val route: String) {
    object Mood : Screen("mood")
    object Profile : Screen("profile")
    object Recommendation : Screen("recommendation")
    object Visualize : Screen("visualize/{outfitId}") {
        fun createRoute(outfitId: String) = "visualize/$outfitId"
    }
}

@Composable
fun NavGraph(
    navController: NavHostController = rememberNavController(),
    startDestination: String = Screen.Mood.route
) {
    NavHost(navController = navController, startDestination = startDestination) {
        composable(Screen.Mood.route) {
            val viewModel: MoodViewModel = viewModel()
            val moodText by viewModel.moodText.collectAsState()
            val selectedVibes by viewModel.selectedVibes.collectAsState()
            val isLoading by viewModel.isLoading.collectAsState()
            val planResult by viewModel.planResult.collectAsState()

            LaunchedEffect(planResult) {
                if (planResult != null) {
                    navController.navigate(Screen.Recommendation.route)
                }

            }

            MoodScreen(
                onBack = { navController.popBackStack() },
                onPlanOutfit = { viewModel.planOutfit() },
                moodText = moodText,
                onMoodTextChanged = { viewModel.updateMoodText(it) },
                selectedVibes = selectedVibes,
                onVibeToggled = { viewModel.toggleVibe(it) },
                goToProfile = {navController.navigate(Screen.Profile.route)},
                isLoading = isLoading
            )
        }

        composable(Screen.Profile.route) {
            val viewModel: ProfileViewModel = viewModel()
            val profileState by viewModel.profileState.collectAsState()

            ProfileScreen(
                onBack = { navController.popBackStack() },
                onSaveProfile = {
                    viewModel.saveProfile()
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Mood.route) { inclusive = true }
                    }
                },
                selectedHeight = profileState.height.ifEmpty { "Select your height" },
                onHeightSelected = { viewModel.updateHeight(it) },
                selectedBodyType = profileState.bodyType,
                onBodyTypeSelected = { viewModel.updateBodyType(it) },
                selectedColors = profileState.favoriteColors.toSet(),
                onColorToggled = { viewModel.toggleColor(it) },
                selectedStyles = profileState.styles.toSet(),
                onStyleToggled = { viewModel.toggleStyle(it) }
            )
        }

        composable(Screen.Recommendation.route) {
            val viewModel: RecommendationViewModel = viewModel()
            val recommendation by viewModel.recommendation.collectAsState()
            val isFavorite by viewModel.isFavorite.collectAsState()

            RecommendationScreen(
                onBack = {
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Mood.route) { inclusive = true }
                    }
                },
                onRegenerate = { viewModel.regenerate() },
                onVisualize = { outfitId ->
                    navController.navigate(Screen.Visualize.createRoute(outfitId))
                },
                isFavorite = isFavorite,
                onFavoriteToggled = { viewModel.toggleFavorite() },
                outfitPlan = recommendation
            )
        }

        composable(
            route = Screen.Visualize.route,
            arguments = listOf(navArgument("outfitId") { type = NavType.StringType })
        ) { backStackEntry ->
            val outfitId = backStackEntry.arguments?.getString("outfitId") ?: ""
            val viewModel: VisualizeViewModel = viewModel()
            val visualizeData by viewModel.visualizeData.collectAsState()

            LaunchedEffect(outfitId) {
                viewModel.loadVisualize(outfitId)
            }

            VisualizeScreen(
                onBack = { navController.popBackStack() },
                outfitName = visualizeData?.outfitName ?: "",
                visualizeData = visualizeData ?: VisualizeData()
            )
        }
    }
}
