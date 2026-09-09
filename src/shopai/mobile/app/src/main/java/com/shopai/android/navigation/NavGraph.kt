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
import com.shopai.android.prefs.Session
import com.shopai.android.screens.ChatScreen
import com.shopai.android.screens.LoginScreen
import com.shopai.android.screens.MoodScreen
import com.shopai.android.screens.ProfileScreen
import com.shopai.android.viewmodel.AuthViewModel
import com.shopai.android.viewmodel.ChatViewModel
import com.shopai.android.viewmodel.MoodViewModel
import com.shopai.android.viewmodel.ProfileViewModel

sealed class Screen(val route: String) {
    object Mood : Screen("mood")
    object Profile : Screen("profile")
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
            MoodScreen(
                onBack = { navController.popBackStack() },
                onPlanOutfit = { occasional ->
                    // A request from here starts a new conversation: the old
                    // transcript goes and the server's task ledger is cleared.
                    chatViewModel.startNewConversation(
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

        composable(Screen.Chat.route) {
            val chatItems by chatViewModel.items.collectAsState()
            val selectedOptionIds by chatViewModel.selectedOptionIds.collectAsState()

            ChatScreen(
                items = chatItems,
                selectedOptionIds = selectedOptionIds,
                onOptionSelected = { _, optionId -> chatViewModel.selectOption(optionId) },
                onBack = { navController.popBackStack() },
                onSendMessage = { message -> chatViewModel.planOutfit(moodText = message) },
                onLeave = { chatViewModel.clearCurrentTask() }
            )
        }

    }
}
