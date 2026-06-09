package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shopai.android.reusables.PrimaryButton
import com.shopai.android.reusables.ShopAITopBar
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.ChipBorder
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.TextSecondary

data class ProductItem(
    val imageUrl: String,
    val name: String,
    val price: String,
    val platform: String
)

@Composable
fun RecommendationScreen(
    onBack: () -> Unit = {},
    onRegenerate: () -> Unit = {}
) {
    var isFavorite by remember { mutableStateOf(false) }

    val styleTags = listOf("Sophisticated", "Productive", "Summer 24")
    val products = listOf(
        ProductItem("", "Tailored Charcoal Blazer", "\$189.00", "Amazon"),
        ProductItem("", "Structured Leather Tote", "\$245.00", "Myntra"),
        ProductItem("", "Pointed-Toe Suede Pumps", "\$120.00", "Amazon"),
        ProductItem("", "Ivory Silk Blouse", "\$95.00", "Myntra"),
        ProductItem("", "Classic Minimalist Watch", "\$310.00", "Amazon")
    )

    Scaffold(
        topBar = {
            ShopAITopBar(
                showBack = true,
                onBack = onBack,
                actions = {
                    IconButton(onClick = {}) {
                        Icon(Icons.Default.Share, contentDescription = "Share", tint = Color(0xFF6B6B80))
                    }
                    IconButton(onClick = { isFavorite = !isFavorite }) {
                        Icon(
                            imageVector = if (isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                            contentDescription = "Favorite",
                            tint = if (isFavorite) ShopAIRed else Color(0xFF6B6B80)
                        )
                    }
                }
            )
        },
        containerColor = Background
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            LazyColumn(
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(bottom = 16.dp)
            ) {
                item {
                    // Hero image
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                            .background(Color(0xFF2A2A3E))
                    ) {
                        AsyncImage(
                            model = "",
                            contentDescription = "Outfit hero",
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop
                        )
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(
                                    Brush.verticalGradient(
                                        colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.3f))
                                    )
                                )
                        )
                        Surface(
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(12.dp),
                            shape = RoundedCornerShape(20.dp),
                            color = ShopAIRed
                        ) {
                            Text(
                                text = "Curated by AI",
                                color = Color.White,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }
                    }
                }

                item {
                    Column(modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp)) {
                        Text(
                            text = "Modern Corporate Look",
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1A1A2E)
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "A sharp, monochromatic base with bold textural contrasts for the modern professional.",
                            fontSize = 14.sp,
                            color = TextSecondary,
                            lineHeight = 20.sp
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            styleTags.forEach { tag ->
                                Surface(
                                    shape = RoundedCornerShape(20.dp),
                                    color = Color.White,
                                    border = ButtonDefaults.outlinedButtonBorder
                                ) {
                                    Text(
                                        text = tag,
                                        fontSize = 12.sp,
                                        color = Color(0xFF1A1A2E),
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                                    )
                                }
                            }
                        }
                    }
                }

                item {
                    HorizontalDivider(
                        modifier = Modifier.padding(horizontal = 20.dp),
                        color = Color(0xFFEEEEF2)
                    )
                    Text(
                        text = "Featured Items",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1A1A2E),
                        modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp)
                    )
                }

                items(products) { product ->
                    Column(modifier = Modifier.padding(horizontal = 20.dp)) {
                        com.shopai.android.reusables.ProductCard(
                            imageUrl = product.imageUrl,
                            name = product.name,
                            price = product.price,
                            platform = product.platform,
                            onBuyClick = {}
                        )
                        HorizontalDivider(color = Color(0xFFEEEEF2))
                    }
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp,
                color = Color.White
            ) {
                PrimaryButton(
                    text = "Regenerate Outfit Recommendations",
                    onClick = onRegenerate,
                    modifier = Modifier.padding(16.dp)
                )
            }
        }
    }
}
