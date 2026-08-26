package com.shopai.android.navigation

import androidx.activity.ComponentActivity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.shopai.android.data.model.VisualizeData
import com.shopai.android.data.repository.OutfitRepository
import com.shopai.android.prefs.Session
import com.shopai.android.screens.ChatScreen
import com.shopai.android.screens.LoginScreen
import com.shopai.android.screens.MoodScreen
import com.shopai.android.screens.ProfileScreen
import com.shopai.android.screens.RecommendationScreen
import com.shopai.android.screens.VisualizeScreen
import com.shopai.android.viewmodel.AuthViewModel
import com.shopai.android.viewmodel.ChatViewModel
import com.shopai.android.viewmodel.MoodViewModel
import com.shopai.android.viewmodel.ProfileViewModel
import com.shopai.android.viewmodel.RecommendationViewModel
import com.shopai.android.viewmodel.VisualizeViewModel

sealed class Screen(val route: String) {
    object Mood : Screen("mood")
    object Profile : Screen("profile")
    object Recommendation : Screen("recommendation")
    object Visualize : Screen("visualize")
    object Chat : Screen("chat")
    object Login : Screen("login")
}

@Composable
fun NavGraph(
    navController: NavHostController = rememberNavController(),
    startDestination: String? = null
) {
    // Activity-scoped so the screen that starts a request and the screen that shows
    // it share one transcript.
    val activity = LocalContext.current as ComponentActivity
    val chatViewModel: ChatViewModel = viewModel(viewModelStoreOwner = activity)

    // A stored token decides where the app opens - no session, no app.
    val start = startDestination ?: remember {
        if (Session.isLoggedIn(activity)) Screen.Mood.route else Screen.Login.route
    }

    NavHost(navController = navController, startDestination = start) {
        composable(Screen.Login.route) {
            val authViewModel: AuthViewModel = viewModel()
            val mode by authViewModel.mode.collectAsState()
            val email by authViewModel.email.collectAsState()
            val password by authViewModel.password.collectAsState()
            val confirmPassword by authViewModel.confirmPassword.collectAsState()
            val submitting by authViewModel.submitting.collectAsState()
            val error by authViewModel.error.collectAsState()
            val notice by authViewModel.notice.collectAsState()
            val needsConfirmation by authViewModel.needsConfirmation.collectAsState()
            val loggedIn by authViewModel.loggedIn.collectAsState()

            LaunchedEffect(loggedIn) {
                if (loggedIn) {
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Login.route) { inclusive = true }
                    }
                }
            }

            LoginScreen(
                mode = mode,
                email = email,
                password = password,
                confirmPassword = confirmPassword,
                submitting = submitting,
                error = error,
                notice = notice,
                needsConfirmation = needsConfirmation,
                onModeChange = { authViewModel.setMode(it) },
                onEmailChange = { authViewModel.updateEmail(it) },
                onPasswordChange = { authViewModel.updatePassword(it) },
                onConfirmPasswordChange = { authViewModel.updateConfirmPassword(it) },
                onSubmit = { authViewModel.submit() },
                onResendConfirmation = { authViewModel.resendConfirmation() }
            )
        }

        composable(Screen.Mood.route) {
            val viewModel: MoodViewModel = viewModel()
            val moodText by viewModel.moodText.collectAsState()
            val selectedVibes by viewModel.selectedVibes.collectAsState()
            val isLoading by viewModel.isLoading.collectAsState()
            val planIdeas by viewModel.planIdeas.collectAsState()
            val selectedOutfit by viewModel.selectedOutfit.collectAsState()

            LaunchedEffect(selectedOutfit) {
                if (selectedOutfit != null) {
                    navController.navigate(Screen.Recommendation.route)
                    viewModel.clearSelectedOutfit()
                }
            }

            MoodScreen(
                onBack = { navController.popBackStack() },
                onPlanOutfit = { occasional ->
                    chatViewModel.planOutfit(
                        moodText = moodText,
                        vibes = selectedVibes.toList(),
                        occasional = occasional
                    )
                    navController.navigate(Screen.Chat.route)
                },
                moodText = moodText,
                onMoodTextChanged = { viewModel.updateMoodText(it) },
                selectedVibes = selectedVibes,
                quickVibes = viewModel.quickVibes,
                onQuickVibeSelected = { viewModel.selectQuickVibe(it) },
                goToProfile = { navController.navigate(Screen.Profile.route) },
                isLoading = isLoading,
                planIdeas = planIdeas,
                onOutfitSelected = { viewModel.selectOutfit(it) }
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
            val selectedItems by viewModel.selectedItems.collectAsState()
            val links by viewModel.links.collectAsState()
            val isLoadingLinks by viewModel.isLoadingLinks.collectAsState()

            RecommendationScreen(
                onBack = {
                    navController.navigate(Screen.Mood.route) {
                        popUpTo(Screen.Mood.route) { inclusive = true }
                    }
                },
                onRegenerate = { viewModel.regenerate() },
                onVisualize = { outfitDescription ->
                    OutfitRepository.pendingVisualizeDescription = outfitDescription
                    navController.navigate(Screen.Visualize.route)
                },
                isFavorite = isFavorite,
                onFavoriteToggled = { viewModel.toggleFavorite() },
                outfitPlan = recommendation,
                selectedItems = selectedItems,
                onItemToggled = { viewModel.toggleItem(it) },
                onGetLinks = { viewModel.getLinks() },
                isLoadingLinks = isLoadingLinks,
                links = links
            )
        }

        composable(Screen.Chat.route) {
            val chatItems by chatViewModel.items.collectAsState()
            val selectedOptionIds by chatViewModel.selectedOptionIds.collectAsState()

            ChatScreen(
                items = chatItems,
                selectedOptionIds = selectedOptionIds,
                onOptionSelected = { _, optionId -> chatViewModel.selectOption(optionId) },
                onBack = { navController.popBackStack() },
                onSendMessage = { message -> chatViewModel.planOutfit(moodText = message) }
            )
        }

        composable(route = Screen.Visualize.route) {
            val context = LocalContext.current
            val profile = Session.getProfile(context)
            val viewModel: VisualizeViewModel = viewModel()
            val visualizeData by viewModel.visualizeData.collectAsState()
            val description = OutfitRepository.pendingVisualizeDescription

            LaunchedEffect(description) {
                viewModel.loadVisualize(
                    outfitDescription = description,
                    bodyType = profile.bodyType,
                    height = profile.height
                )
            }

            VisualizeScreen(
                onBack = { navController.popBackStack() },
                outfitName = visualizeData?.outfitName ?: "",
                visualizeData = visualizeData ?: VisualizeData()
            )
        }
    }
}
