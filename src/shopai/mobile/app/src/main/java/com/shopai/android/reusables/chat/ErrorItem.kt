package com.shopai.android.reusables.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.HelpOutline
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.data.model.ErrorKind
import com.shopai.android.ui.theme.ErrorSurfaceSoft
import com.shopai.android.ui.theme.QuickReplyBubble
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAIRedDark
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextPrimary

/**
 * A reply Sia cannot fulfil as asked - out of scope, refused, unavailable, or
 * ambiguous. [kind] picks the icon and colouring; [quickReplies] adds a chip row
 * under the bubble and is normally used with [ErrorKind.CLARIFICATION].
 */
@Composable
fun ErrorItem(
    text: String,
    kind: ErrorKind,
    modifier: Modifier = Modifier,
    quickReplies: List<String> = emptyList(),
    onQuickReply: (String) -> Unit = {}
) {
    val style = kind.style()

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier
                .widthIn(max = 320.dp)
                .background(style.container, RoundedCornerShape(16.dp))
                .padding(horizontal = 16.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(
                imageVector = style.icon,
                contentDescription = null,
                tint = style.content,
                modifier = Modifier
                    .padding(top = 2.dp)
                    .size(20.dp)
            )
            Text(
                text = text,
                color = style.content,
                fontSize = 16.sp,
                lineHeight = 24.sp
            )
        }

        if (quickReplies.isNotEmpty()) {
            Row(
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                quickReplies.forEach { reply ->
                    Text(
                        text = reply,
                        color = TextPrimary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier
                            .background(QuickReplyBubble, RoundedCornerShape(10.dp))
                            .clickable { onQuickReply(reply) }
                            .padding(horizontal = 16.dp, vertical = 10.dp)
                    )
                }
            }
        }
    }
}

private data class ErrorStyle(
    val container: Color,
    val content: Color,
    val icon: ImageVector
)

private fun ErrorKind.style(): ErrorStyle = when (this) {
    ErrorKind.OUT_OF_SCOPE -> ErrorStyle(ShopAIRed, Color.White, Icons.Default.Info)
    ErrorKind.NOT_ALLOWED -> ErrorStyle(ShopAIRedDark, Color.White, Icons.Default.Gavel)
    ErrorKind.SYSTEM_DOWN -> ErrorStyle(ErrorSurfaceSoft, ShopAIRed, Icons.Default.WarningAmber)
    ErrorKind.CLARIFICATION -> ErrorStyle(
        container = ShopAIRed,
        content = Color.White,
        icon = Icons.AutoMirrored.Filled.HelpOutline
    )
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7, heightDp = 560)
@Composable
private fun ErrorItemPreview() {
    ShopAITheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            ErrorItem(
                text = "I'm a shopping assistant, I cannot do this job.",
                kind = ErrorKind.OUT_OF_SCOPE
            )
            ErrorItem(
                text = "I'm not allowed to perform this task. Ask for something else.",
                kind = ErrorKind.NOT_ALLOWED
            )
            ErrorItem(
                text = "System is down and we'll be back till 4:00 PM.",
                kind = ErrorKind.SYSTEM_DOWN
            )
            ErrorItem(
                text = "I'm not sure if I'm understanding it right. Are you looking for " +
                    "formal shoes for a wedding?",
                kind = ErrorKind.CLARIFICATION,
                quickReplies = listOf("Yes, exactly", "No, casual")
            )
        }
    }
}
