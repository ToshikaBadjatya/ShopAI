package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Mic
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
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
    onPlanOutfit: () -> Unit = {},
    moodText: String = "",
    onMoodTextChanged: (String) -> Unit = {},
    selectedVibes: Set<String> = emptySet(),
    onVibeToggled: (String) -> Unit = {},
    isLoading: Boolean = false
) {
    val quickVibes = listOf(
        "Summer Brunch", "Corporate Chic", "Late Night Party", "Scandi Minimal", "Gorpcore"
    )

    Scaffold(
        topBar = {
            ShopAITopBar(
                showBack = true,
                onBack = onBack,
                actions = {
                    IconButton(onClick = {}) {
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
                    text = "What's the outfit mood\nfor today?",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1A1A2E),
                    lineHeight = 36.sp
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Describe your vibe, destination, or preference and let AI do the styling.",
                    fontSize = 14.sp,
                    color = TextSecondary,
                    lineHeight = 20.sp
                )

                Spacer(modifier = Modifier.height(24.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
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
                                text = "AI-Stylist is listening...",
                                fontSize = 12.sp,
                                color = TextHint,
                                modifier = Modifier.weight(1f)
                            )
                            IconButton(onClick = {}) {
                                Icon(
                                    imageVector = Icons.Default.Mic,
                                    contentDescription = "Voice input",
                                    tint = Color(0xFF6B6B80)
                                )
                            }
                            IconButton(onClick = {}) {
                                Icon(
                                    imageVector = Icons.Default.Image,
                                    contentDescription = "Image input",
                                    tint = Color(0xFF6B6B80)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "✦ Quick Vibes",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF1A1A2E)
                )

                Spacer(modifier = Modifier.height(10.dp))

                ChipSelector(
                    options = quickVibes,
                    selected = selectedVibes,
                    onSelectionChanged = { newSet ->
                        val added = newSet - selectedVibes
                        val removed = selectedVibes - newSet
                        (added + removed).forEach { onVibeToggled(it) }
                    },
                    multiSelect = false
                )

                Spacer(modifier = Modifier.height(24.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    TrendCard(label = "Trending Now", imageUrl = "", modifier = Modifier.weight(1f))
                    TrendCard(label = "Recently Saved", imageUrl = "", modifier = Modifier.weight(1f))
                }

                Spacer(modifier = Modifier.height(24.dp))
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp,
                color = Color.White
            ) {
                Box(modifier = Modifier.padding(16.dp), contentAlignment = Alignment.Center) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(48.dp),
                            color = ShopAIRed
                        )
                    } else {
                        PrimaryButton(text = "⚡ Plan My Outfit", onClick = onPlanOutfit)
                    }
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
