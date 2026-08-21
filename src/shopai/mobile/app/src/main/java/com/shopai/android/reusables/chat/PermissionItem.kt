package com.shopai.android.reusables.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAITheme

/**
 * Sia asking to be let into something. Offers an inline allow/deny pair plus a link
 * to the full list of actions she intends to perform.
 */
@Composable
fun PermissionItem(
    text: String,
    modifier: Modifier = Modifier,
    allowLabel: String = "Allow",
    denyLabel: String = "Deny",
    detailsLabel: String = "View More",
    onAllow: () -> Unit = {},
    onDeny: () -> Unit = {},
    onViewDetails: () -> Unit = {}
) {
    Column(
        modifier = modifier
            .widthIn(max = 320.dp)
            .background(ShopAIRed, RoundedCornerShape(16.dp))
            .padding(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text(
            text = text,
            color = Color.White,
            fontSize = 16.sp,
            lineHeight = 24.sp
        )

        if (detailsLabel.isNotEmpty()) {
            Text(
                text = detailsLabel,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                textDecoration = TextDecoration.Underline,
                modifier = Modifier.clickable(onClick = onViewDetails)
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            PermissionAction(
                label = allowLabel,
                filled = true,
                onClick = onAllow,
                modifier = Modifier.weight(1f)
            )
            PermissionAction(
                label = denyLabel,
                filled = false,
                onClick = onDeny,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun PermissionAction(
    label: String,
    filled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val shape = RoundedCornerShape(10.dp)
    Text(
        text = label,
        color = if (filled) ShopAIRed else Color.White,
        fontSize = 15.sp,
        fontWeight = FontWeight.SemiBold,
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        modifier = modifier
            .then(
                if (filled) {
                    Modifier.background(Color.White, shape)
                } else {
                    Modifier.border(1.dp, Color.White.copy(alpha = 0.7f), shape)
                }
            )
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp)
    )
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7)
@Composable
private fun PermissionItemPreview() {
    ShopAITheme {
        PermissionItem(
            text = "Sia needs permission to access your socials. View more to see the " +
                "actions performed.",
            modifier = Modifier.padding(16.dp)
        )
    }
}
