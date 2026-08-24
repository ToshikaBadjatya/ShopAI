package com.shopai.android.reusables.chat

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextSecondary

/**
 * One muted line saying what Sia is working on. The text breathes so the line reads
 * as live without a spinner; set [animated] to false for previews and screenshots.
 */
@Composable
fun ThinkingItem(
    text: String,
    modifier: Modifier = Modifier,
    animated: Boolean = true
) {
    val alpha = if (animated) {
        val transition = rememberInfiniteTransition(label = "thinking")
        val pulse by transition.animateFloat(
            initialValue = 0.4f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = 900),
                repeatMode = RepeatMode.Reverse
            ),
            label = "thinking-alpha"
        )
        pulse
    } else {
        0.7f
    }

    Text(
        text = text,
        color = TextSecondary,
        fontSize = 15.sp,
        lineHeight = 22.sp,
        modifier = modifier
            .fillMaxWidth()
            .alpha(alpha)
    )
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7)
@Composable
private fun ThinkingItemPreview() {
    ShopAITheme {
        ThinkingItem(
            text = "Reading your style profile...",
            animated = false,
            modifier = Modifier.padding(16.dp)
        )
    }
}
