package com.shopai.android.reusables.chat

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.data.model.ChatOption
import com.shopai.android.ui.theme.CardBackground
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextPrimary
import com.shopai.android.ui.theme.TextSecondary

/**
 * A titled list of choices. With [multiSelect] the rows carry checkboxes and any
 * number can be picked; without it they carry radios and picking one clears the rest.
 * Selection lives with the caller - tapping anywhere on a row reports it back.
 */
@Composable
fun OptionsItem(
    title: String,
    options: List<ChatOption>,
    selectedIds: Set<String>,
    onOptionSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
    multiSelect: Boolean = false
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (title.isNotEmpty()) {
            Text(
                text = title,
                color = TextPrimary,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 4.dp)
            )
        }

        options.forEach { option ->
            OptionRow(
                option = option,
                selected = option.id in selectedIds,
                multiSelect = multiSelect,
                onClick = { onOptionSelected(option.id) }
            )
        }
    }
}

@Composable
private fun OptionRow(
    option: ChatOption,
    selected: Boolean,
    multiSelect: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardBackground),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(start = 18.dp, end = 10.dp, top = 16.dp, bottom = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = option.title,
                    color = TextPrimary,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold
                )
                if (option.subtitle.isNotEmpty()) {
                    Text(
                        text = option.subtitle,
                        color = TextSecondary,
                        fontSize = 15.sp,
                        lineHeight = 21.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }

            if (multiSelect) {
                Checkbox(
                    checked = selected,
                    onCheckedChange = { onClick() },
                    colors = CheckboxDefaults.colors(
                        checkedColor = ShopAIRed,
                        checkmarkColor = Color.White,
                        uncheckedColor = TextSecondary
                    )
                )
            } else {
                RadioButton(
                    selected = selected,
                    onClick = onClick,
                    colors = RadioButtonDefaults.colors(
                        selectedColor = ShopAIRed,
                        unselectedColor = TextSecondary
                    )
                )
            }
        }
    }
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7, heightDp = 760)
@Composable
private fun OptionsItemPreview() {
    val options = listOf(
        ChatOption("1", "Midnight Velvet Mini", "Sleek fabric, dramatic puffed sleeves."),
        ChatOption("2", "Satin Slip & Leather", "Edge meets elegance."),
        ChatOption("3", "Sequin Statement Jumpsuit", "For maximum impact.")
    )
    var single by remember { mutableStateOf(setOf("1")) }
    var multi by remember { mutableStateOf(setOf("1", "3")) }

    ShopAITheme {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(28.dp)
        ) {
            OptionsItem(
                title = "Curated for you:",
                options = options,
                selectedIds = single,
                onOptionSelected = { single = setOf(it) }
            )
            OptionsItem(
                title = "Pick everything you like:",
                options = options,
                selectedIds = multi,
                multiSelect = true,
                onOptionSelected = { id ->
                    multi = if (id in multi) multi - id else multi + id
                }
            )
        }
    }
}
