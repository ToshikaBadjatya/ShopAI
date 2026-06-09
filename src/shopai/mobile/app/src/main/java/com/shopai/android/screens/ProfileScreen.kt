package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.Percent
import androidx.compose.material.icons.filled.Straighten
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.reusables.BodyTypeCard
import com.shopai.android.reusables.ChipSelector
import com.shopai.android.reusables.PrimaryButton
import com.shopai.android.reusables.ShopAITopBar
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.TextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    onBack: () -> Unit = {},
    onSaveProfile: () -> Unit = {},
    selectedHeight: String = "Select your height",
    onHeightSelected: (String) -> Unit = {},
    selectedBodyType: String = "",
    onBodyTypeSelected: (String) -> Unit = {},
    selectedColors: Set<String> = emptySet(),
    onColorToggled: (String) -> Unit = {},
    selectedStyles: Set<String> = emptySet(),
    onStyleToggled: (String) -> Unit = {}
) {
    var heightDropdownExpanded by remember { mutableStateOf(false) }

    val heightOptions = listOf(
        "Under 5'0\"", "5'0\" - 5'3\"", "5'4\" - 5'7\"", "5'8\" - 5'11\"", "6'0\" and above"
    )
    val bodyTypes = listOf(
        Triple(Icons.Default.FitnessCenter, "Athletic", "athletic"),
        Triple(Icons.Default.Percent, "Curvy", "curvy"),
        Triple(Icons.Default.Straighten, "Slim", "slim"),
        Triple(Icons.Default.AccessibilityNew, "Plus", "plus")
    )
    val colorPalette = listOf("#E53935", "#212121", "#9E9E9E", "#F5F5DC", "#1A237E", "#795548")
    val styleOptions = listOf(
        "Streetwear", "Minimalist", "Formal", "Boho", "Vintage", "Preppy", "Athleisure"
    )

    Scaffold(
        topBar = {
            ShopAITopBar(showBack = true, onBack = onBack)
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
                    text = "Tell us about yourself",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1A1A2E)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Personalize your AI stylist for perfect recommendations.",
                    fontSize = 14.sp,
                    color = TextSecondary
                )

                Spacer(modifier = Modifier.height(28.dp))

                Text(text = "Height", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF1A1A2E))
                Spacer(modifier = Modifier.height(8.dp))
                ExposedDropdownMenuBox(
                    expanded = heightDropdownExpanded,
                    onExpandedChange = { heightDropdownExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedHeight,
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = heightDropdownExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(),
                        shape = RoundedCornerShape(10.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ShopAIRed,
                            unfocusedBorderColor = Color(0xFFDDDDE8)
                        )
                    )
                    ExposedDropdownMenu(
                        expanded = heightDropdownExpanded,
                        onDismissRequest = { heightDropdownExpanded = false }
                    ) {
                        heightOptions.forEach { option ->
                            DropdownMenuItem(
                                text = { Text(option) },
                                onClick = {
                                    onHeightSelected(option)
                                    heightDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(text = "Body Type", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF1A1A2E))
                Spacer(modifier = Modifier.height(12.dp))
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.height(220.dp),
                    userScrollEnabled = false
                ) {
                    items(bodyTypes.size) { index ->
                        val (icon, label, key) = bodyTypes[index]
                        BodyTypeCard(
                            icon = icon,
                            label = label,
                            selected = selectedBodyType == key,
                            onClick = { onBodyTypeSelected(key) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(text = "Favorite Color Palette", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF1A1A2E))
                Spacer(modifier = Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    colorPalette.forEach { hex ->
                        val color = try {
                            Color(android.graphics.Color.parseColor(hex))
                        } catch (e: Exception) {
                            Color.Gray
                        }
                        val isSelected = hex in selectedColors
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(color)
                                .then(
                                    if (isSelected) Modifier.border(2.dp, ShopAIRed, CircleShape)
                                    else Modifier
                                )
                                .clickable { onColorToggled(hex) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(text = "Clothing Style (Multi-select)", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF1A1A2E))
                Spacer(modifier = Modifier.height(10.dp))
                ChipSelector(
                    options = styleOptions,
                    selected = selectedStyles,
                    onSelectionChanged = { newSet -> newSet.forEach { onStyleToggled(it) } },
                    multiSelect = true
                )

                Spacer(modifier = Modifier.height(28.dp))
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp,
                color = Color.White
            ) {
                PrimaryButton(
                    text = "Save Profile →",
                    onClick = onSaveProfile,
                    modifier = Modifier.padding(16.dp)
                )
            }
        }
    }
}
