package com.shopai.android.reusables

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shopai.android.ui.theme.ShopAIRed

@Composable
fun ProductCard(
    imageUrl: String,
    name: String,
    price: String,
    platform: String,
    onBuyClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        AsyncImage(
            model = imageUrl,
            contentDescription = name,
            modifier = Modifier
                .size(72.dp)
                .clip(RoundedCornerShape(8.dp)),
            contentScale = ContentScale.Crop
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = name,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF1A1A2E)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = price,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = ShopAIRed
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedButton(
                onClick = onBuyClick,
                shape = RoundedCornerShape(8.dp),
                border = BorderStroke(1.dp, ShopAIRed),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = ShopAIRed)
            ) {
                Text(
                    text = "Buy on $platform ↗",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}
