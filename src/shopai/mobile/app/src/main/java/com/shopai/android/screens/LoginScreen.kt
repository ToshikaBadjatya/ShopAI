package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.reusables.PrimaryButton
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.CardBackground
import com.shopai.android.ui.theme.ChipBorder
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextPrimary
import com.shopai.android.ui.theme.TextSecondary
import com.shopai.android.viewmodel.AuthMode

/**
 * Sign in or create an account. Stateless - the caller owns every field, so the
 * same screen serves both modes.
 */
@Composable
fun LoginScreen(
    mode: AuthMode,
    email: String,
    password: String,
    confirmPassword: String,
    modifier: Modifier = Modifier,
    submitting: Boolean = false,
    error: String? = null,
    notice: String? = null,
    needsConfirmation: Boolean = false,
    onModeChange: (AuthMode) -> Unit = {},
    onEmailChange: (String) -> Unit = {},
    onPasswordChange: (String) -> Unit = {},
    onConfirmPasswordChange: (String) -> Unit = {},
    onSubmit: () -> Unit = {},
    onResendConfirmation: () -> Unit = {}
) {
    val isSignUp = mode == AuthMode.SIGN_UP

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Background)
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(horizontal = 24.dp, vertical = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "ShopAI",
            color = ShopAIRed,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Sign in or create an account",
            color = TextSecondary,
            fontSize = 15.sp,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(28.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = CardBackground),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ModeTab(
                        label = "Sign in",
                        selected = !isSignUp,
                        onClick = { onModeChange(AuthMode.SIGN_IN) },
                        modifier = Modifier.weight(1f)
                    )
                    ModeTab(
                        label = "Sign up",
                        selected = isSignUp,
                        onClick = { onModeChange(AuthMode.SIGN_UP) },
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                AuthField(
                    value = email,
                    onValueChange = onEmailChange,
                    label = "Email",
                    keyboardType = KeyboardType.Email
                )

                Spacer(modifier = Modifier.height(12.dp))

                AuthField(
                    value = password,
                    onValueChange = onPasswordChange,
                    label = "Password",
                    keyboardType = KeyboardType.Password,
                    isPassword = true,
                    imeAction = if (isSignUp) ImeAction.Next else ImeAction.Done
                )

                if (isSignUp) {
                    Spacer(modifier = Modifier.height(12.dp))
                    AuthField(
                        value = confirmPassword,
                        onValueChange = onConfirmPasswordChange,
                        label = "Confirm password",
                        keyboardType = KeyboardType.Password,
                        isPassword = true
                    )
                }

                if (error != null) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(text = error, color = ShopAIRed, fontSize = 14.sp, lineHeight = 20.sp)
                }

                if (needsConfirmation) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Resend confirmation email",
                        color = ShopAIRed,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        textDecoration = TextDecoration.Underline,
                        modifier = Modifier.clickable(onClick = onResendConfirmation)
                    )
                }

                if (notice != null) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(text = notice, color = TextSecondary, fontSize = 14.sp, lineHeight = 20.sp)
                }

                Spacer(modifier = Modifier.height(20.dp))

                if (submitting) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(28.dp),
                            color = ShopAIRed
                        )
                    }
                } else {
                    PrimaryButton(
                        text = if (isSignUp) "Create account" else "Log in",
                        onClick = onSubmit
                    )
                }
            }
        }
    }
}

@Composable
private fun ModeTab(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val shape = RoundedCornerShape(12.dp)
    Text(
        text = label,
        color = if (selected) Color.White else TextSecondary,
        fontSize = 15.sp,
        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
        textAlign = TextAlign.Center,
        modifier = modifier
            .background(if (selected) ShopAIRed else Background, shape)
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp)
    )
}

@Composable
private fun AuthField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    keyboardType: KeyboardType,
    isPassword: Boolean = false,
    imeAction: ImeAction = ImeAction.Next
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(text = label, fontSize = 14.sp) },
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        visualTransformation = if (isPassword) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType, imeAction = imeAction),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = ShopAIRed,
            unfocusedBorderColor = ChipBorder,
            focusedLabelColor = ShopAIRed,
            unfocusedLabelColor = TextSecondary,
            cursorColor = ShopAIRed,
            focusedTextColor = TextPrimary,
            unfocusedTextColor = TextPrimary
        )
    )
}

@Preview(showBackground = true, heightDp = 800)
@Composable
private fun LoginScreenSignInPreview() {
    ShopAITheme {
        LoginScreen(
            mode = AuthMode.SIGN_IN,
            email = "you@example.com",
            password = "secret",
            confirmPassword = ""
        )
    }
}

@Preview(showBackground = true, heightDp = 800)
@Composable
private fun LoginScreenSignUpPreview() {
    ShopAITheme {
        LoginScreen(
            mode = AuthMode.SIGN_UP,
            email = "you@example.com",
            password = "secret",
            confirmPassword = "secre",
            error = "Passwords don't match."
        )
    }
}

@Preview(showBackground = true, heightDp = 800)
@Composable
private fun LoginScreenUnconfirmedPreview() {
    ShopAITheme {
        LoginScreen(
            mode = AuthMode.SIGN_IN,
            email = "you@example.com",
            password = "secret",
            confirmPassword = "",
            error = "This email hasn't been confirmed yet. Check your inbox for the link, or resend it.",
            needsConfirmation = true
        )
    }
}
