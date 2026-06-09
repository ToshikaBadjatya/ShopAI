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
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.reusables.PrimaryButton
import com.shopai.android.reusables.ShopAITopBar
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.TextSecondary

@Composable
fun RecommendationScreen(
    onBack: () -> Unit = {},
    onRegenerate: () -> Unit = {},
    onVisualize: (outfitId: String) -> Unit = {},
    isFavorite: Boolean = false,
    onFavoriteToggled: () -> Unit = {},
    outfitPlan: OutfitPlanResponse? = null
) {
    val outfitName = outfitPlan?.outfitName ?: "Modern Corporate Look"
    val outfitDescription = outfitPlan?.description
        ?: "A sharp, monochromatic base with bold textural contrasts for the modern professional."
    val styleTags = outfitPlan?.tags ?: listOf("Sophisticated", "Productive", "Summer 24")
    val heroImageUrl = outfitPlan?.heroImageUrl ?: ""
    val products = outfitPlan?.products ?: emptyList()

    Scaffold(
        topBar = {
            ShopAITopBar(
                showBack = true,
                onBack = onBack,
                actions = {
                    IconButton(onClick = {}) {
                        Icon(Icons.Default.Share, contentDescription = "Share", tint = Color(0xFF6B6B80))
                    }
                    IconButton(onClick = onFavoriteToggled) {
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
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                            .background(Color(0xFF2A2A3E))
                    ) {
                        AsyncImage(
                            model = heroImageUrl,
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
                            text = outfitName,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1A1A2E)
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = outfitDescription,
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
                Column(modifier = Modifier.padding(16.dp)) {
                    OutlinedButton(
                        onClick = { onVisualize(outfitPlan?.outfitId ?: "") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ShopAIRed),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ShopAIRed)
                    ) {
                        Text(
                            text = "Visualize Outfit",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 15.sp
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    PrimaryButton(
                        text = "Regenerate Outfit Recommendations",
                        onClick = onRegenerate
                    )
                }
            }
        }
    }
}
