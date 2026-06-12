package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.ProductLink
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
    outfitPlan: OutfitPlanResponse? = null,
    selectedItems: Set<String> = emptySet(),
    onItemToggled: (String) -> Unit = {},
    onGetLinks: () -> Unit = {},
    isLoadingLinks: Boolean = false,
    links: List<ProductLink>? = null
) {
    val outfitName = outfitPlan?.outfitName ?: "Modern Corporate Look"
    val outfitDescription = outfitPlan?.description
        ?: "A sharp, monochromatic base with bold textural contrasts for the modern professional."
    val styleTags = outfitPlan?.tags ?: listOf("Sophisticated", "Productive", "Summer 24")
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
                    Text(
                        text = "Select items to get marketplace links",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        modifier = Modifier.padding(horizontal = 20.dp)
                    )
                }

                items(styleTags) { tag ->
                    val isSelected = tag in selectedItems
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 20.dp, vertical = 4.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (isSelected) Color(0xFFFFEEEE) else Color.White)
                            .clickable { onItemToggled(tag) }
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = isSelected,
                            onCheckedChange = { onItemToggled(tag) },
                            colors = CheckboxDefaults.colors(checkedColor = ShopAIRed)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = tag,
                            fontSize = 14.sp,
                            color = Color(0xFF1A1A2E)
                        )
                    }
                }

                if (products.isNotEmpty()) {
                    item {
                        HorizontalDivider(
                            modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                            color = Color(0xFFEEEEF2)
                        )
                        Text(
                            text = "Products",
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

                if (!links.isNullOrEmpty()) {
                    item {
                        HorizontalDivider(
                            modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                            color = Color(0xFFEEEEF2)
                        )
                        Text(
                            text = "Shop Links",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1A1A2E),
                            modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp)
                        )
                    }

                    items(links) { link ->
                        Column(modifier = Modifier.padding(horizontal = 20.dp)) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = link.name,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = Color(0xFF1A1A2E)
                                    )
                                    if (link.price.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(
                                            text = link.price,
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = ShopAIRed
                                        )
                                    }
                                    if (link.url.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(
                                            text = link.url,
                                            fontSize = 11.sp,
                                            color = Color(0xFF4A90E2),
                                            maxLines = 1
                                        )
                                    }
                                }
                                if (link.platform.isNotEmpty()) {
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = link.platform,
                                        fontSize = 11.sp,
                                        color = Color(0xFF6B6B80),
                                        modifier = Modifier
                                            .background(Color(0xFFF5F5F5), RoundedCornerShape(6.dp))
                                            .padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                            HorizontalDivider(color = Color(0xFFEEEEF2))
                        }
                    }
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp,
                color = Color.White
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        if (isLoadingLinks) {
                            CircularProgressIndicator(
                                color = ShopAIRed,
                                modifier = Modifier.size(28.dp),
                                strokeWidth = 3.dp
                            )
                        } else {
                            PrimaryButton(
                                text = if (selectedItems.isEmpty()) "Select items to Get Links"
                                       else "Get Links (${selectedItems.size})",
                                onClick = onGetLinks
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    PrimaryButton(
                        text = "Visualize Outfit",
                        onClick = { onVisualize(outfitPlan?.outfitId ?: "") }
                    )
                }
            }
        }
    }
}
