package com.shopai.android.reusables.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextPrimary
import com.shopai.android.ui.theme.UserBubble

/** Grey, right-weighted bubble carrying what the user typed. */
@Composable
fun UserMessageItem(
    text: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End
    ) {
        Text(
            text = text,
            color = TextPrimary,
            fontSize = 16.sp,
            lineHeight = 24.sp,
            modifier = Modifier
                .widthIn(max = 300.dp)
                .background(
                    color = UserBubble,
                    shape = RoundedCornerShape(
                        topStart = 20.dp,
                        topEnd = 20.dp,
                        bottomStart = 20.dp,
                        bottomEnd = 4.dp
                    )
                )
                .padding(horizontal = 18.dp, vertical = 14.dp)
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7)
@Composable
private fun UserMessageItemPreview() {
    ShopAITheme {
        UserMessageItem(
            text = "A bold late night party outfit with sleek fabrics, statement " +
                "accessories, and a dramatic silhouette.",
            modifier = Modifier.padding(16.dp)
        )
    }
}
