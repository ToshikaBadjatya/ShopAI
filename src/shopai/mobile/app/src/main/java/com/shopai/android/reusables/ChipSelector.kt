package com.shopai.android.reusables

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.ui.theme.ChipBorder
import com.shopai.android.ui.theme.ChipSelected
import com.shopai.android.ui.theme.ShopAIRed

@Composable
fun ChipSelector(
    options: List<String>,
    selected: Set<String>,
    onSelectionChanged: (Set<String>) -> Unit,
    multiSelect: Boolean = false,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        options.forEach { option ->
            val isSelected = option in selected
            FilterChip(
                selected = isSelected,
                onClick = {
                    onSelectionChanged(
                        if (multiSelect) {
                            if (isSelected) selected - option else selected + option
                        } else {
                            if (isSelected) emptySet() else setOf(option)
                        }
                    )
                },
                label = {
                    Text(
                        text = option,
                        fontSize = 13.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
                    )
                },
                shape = RoundedCornerShape(20.dp),
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = ChipSelected,
                    selectedLabelColor = Color.White,
                    containerColor = Color.White,
                    labelColor = ChipSelected
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = isSelected,
                    selectedBorderColor = Color.Transparent,
                    borderColor = ChipBorder,
                    borderWidth = 1.dp,
                    selectedBorderWidth = 0.dp
                )
            )
        }
    }
}
