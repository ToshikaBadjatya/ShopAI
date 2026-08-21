package com.shopai.android.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Checkroom
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.QuickVibe
import com.shopai.android.reusables.ChipSelector
import com.shopai.android.reusables.PrimaryButton
import com.shopai.android.reusables.ShopAITopBar
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.TextHint
import com.shopai.android.ui.theme.TextSecondary

@Composable
fun MoodScreen(
    onBack: () -> Unit = {},
    onPlanOutfit: (occasional: Boolean) -> Unit = {},
    moodText: String = "",
    onMoodTextChanged: (String) -> Unit = {},
    selectedVibes: Set<String> = emptySet(),
    quickVibes: List<QuickVibe> = QuickVibe.all,
    onQuickVibeSelected: (QuickVibe) -> Unit = {},
    goToProfile: () -> Unit,
    isLoading: Boolean = false,
    planIdeas: List<OutfitPlanResponse> = emptyList(),
    onOutfitSelected: (OutfitPlanResponse) -> Unit = {},
    onViewWardrobe: () -> Unit = {},
    onViewStyleGuide: () -> Unit = {}
) {
    val stylingTabs = listOf(OCCASIONAL_STYLING, "Everyday Styling")
    var selectedStylingTab by remember { mutableStateOf(stylingTabs.first()) }
    val planOutfit = { onPlanOutfit(selectedStylingTab == OCCASIONAL_STYLING) }

    Scaffold(
        topBar = {
            ShopAITopBar(
                showBack = true,
                onBack = onBack,
                actions = {
                    IconButton(onClick = goToProfile) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "Settings",
                            tint = Color(0xFF6B6B80)
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
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp)
            ) {
                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "SIA:- SHOPPING INTELLIGENCE ASSISTANT",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = ShopAIRed,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Hello bestie, How can I\nhelp you?",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1A1A2E),
                    lineHeight = 36.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Describe your vibe, destination, or preference and let AI do the styling.",
                    fontSize = 14.sp,
                    color = TextSecondary,
                    lineHeight = 20.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(24.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(20.dp)
                        ) {
                            stylingTabs.forEach { tab ->
                                val isSelected = tab == selectedStylingTab
                                Column(
                                    modifier = Modifier.clickable { selectedStylingTab = tab }
                                ) {
                                    Text(
                                        text = tab,
                                        fontSize = 15.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                        color = if (isSelected) ShopAIRed else TextSecondary
                                    )
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Box(
                                        modifier = Modifier
                                            .height(2.dp)
                                            .width(if (isSelected) 130.dp else 0.dp)
                                            .background(ShopAIRed)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(4.dp))
                        HorizontalDivider(color = Color(0xFFEEEEF2))

                        TextField(
                            value = moodText,
                            onValueChange = onMoodTextChanged,
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 100.dp),
                            placeholder = {
                                Text(
                                    text = "e.g. A futuristic street-wear look for a rainy Tokyo evening with neon accents...",
                                    color = TextHint,
                                    fontSize = 14.sp,
                                    lineHeight = 20.sp
                                )
                            },
                            colors = TextFieldDefaults.colors(
                                focusedContainerColor = Color.Transparent,
                                unfocusedContainerColor = Color.Transparent,
                                focusedIndicatorColor = Color.Transparent,
                                unfocusedIndicatorColor = Color.Transparent
                            ),
                            maxLines = 5
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Sia is listening...",
                                fontSize = 12.sp,
                                color = TextHint,
                                modifier = Modifier.weight(1f)
                            )
                            IconButton(onClick = {}) {
                                Icon(
                                    imageVector = Icons.Default.Image,
                                    contentDescription = "Image input",
                                    tint = Color(0xFF6B6B80)
                                )
                            }
                            IconButton(onClick = planOutfit) {
                                Icon(
                                    imageVector = Icons.AutoMirrored.Filled.Send,
                                    contentDescription = "Send",
                                    tint = ShopAIRed
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                WardrobeCard(onClick = onViewWardrobe)

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "✦ Quick Vibes",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF1A1A2E)
                )

                Spacer(modifier = Modifier.height(10.dp))

                ChipSelector(
                    options = quickVibes.map { it.label },
                    selected = selectedVibes,
                    onSelectionChanged = { newSet ->
                        val toggledLabel = ((newSet - selectedVibes) + (selectedVibes - newSet)).firstOrNull()
                        val toggledVibe = quickVibes.firstOrNull { it.label == toggledLabel }
                        toggledVibe?.let(onQuickVibeSelected)
                    },
                    multiSelect = false
                )

                if (planIdeas.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(28.dp))

                    Text(
                        text = "✦ Outfit Ideas",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF1A1A2E)
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        contentPadding = PaddingValues(end = 4.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        items(planIdeas) { idea ->
                            OutfitIdeaCard(
                                idea = idea,
                                onClick = { onOutfitSelected(idea) }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp,
                color = Color.White
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(48.dp),
                            color = ShopAIRed
                        )
                    } else {
                        PrimaryButton(text = "⚡ Plan My Outfit", onClick = planOutfit)

                        Spacer(modifier = Modifier.height(12.dp))

                        OutlinedButton(
                            onClick = onViewStyleGuide,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            shape = RoundedCornerShape(26.dp),
                            border = BorderStroke(1.dp, Color(0xFFDDDDE8)),
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = TextSecondary
                            )
                        ) {
                            Icon(
                                imageVector = Icons.Default.MenuBook,
                                contentDescription = null,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "View my style guide",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WardrobeCard(
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = BorderStroke(1.dp, Color(0xFFDDDDE8)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(ShopAIRed.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Checkroom,
                    contentDescription = null,
                    tint = ShopAIRed
                )
            }
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "View my Wardrobe",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF1A1A2E)
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "Manage your digital closet",
                    fontSize = 13.sp,
                    color = TextSecondary
                )
            }
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = null,
                tint = TextSecondary
            )
        }
    }
}

@Composable
private fun OutfitIdeaCard(
    idea: OutfitPlanResponse,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .width(220.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .background(ShopAIRed)
            )
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = idea.outfitName,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1A1A2E),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = idea.description,
                    fontSize = 12.sp,
                    color = TextSecondary,
                    lineHeight = 17.sp,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
                if (idea.tags.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = idea.tags.take(2).joinToString(" · "),
                        fontSize = 11.sp,
                        color = ShopAIRed,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}

@Composable
private fun TrendCard(
    label: String,
    imageUrl: String,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .height(140.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF2A2A3E)),
        contentAlignment = Alignment.BottomStart
    ) {
        if (imageUrl.isNotEmpty()) {
            AsyncImage(
                model = imageUrl,
                contentDescription = label,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.6f))
                    )
                )
        )
        Text(
            text = label,
            color = Color.White,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(12.dp)
        )
    }
}

private const val OCCASIONAL_STYLING = "Occasional Styling"
