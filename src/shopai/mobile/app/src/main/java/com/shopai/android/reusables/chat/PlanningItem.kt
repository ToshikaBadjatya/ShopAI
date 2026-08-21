package com.shopai.android.reusables.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Autorenew
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.data.model.PlanStep
import com.shopai.android.data.model.StepStatus
import com.shopai.android.ui.theme.CardBackground
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.StepConnector
import com.shopai.android.ui.theme.StepPending
import com.shopai.android.ui.theme.TextHint
import com.shopai.android.ui.theme.TextPrimary
import com.shopai.android.ui.theme.TextSecondary

/**
 * Card showing what Sia is working through, one [PlanStep] per row: completed steps
 * are ticked, the active step is ringed and highlighted, pending steps stay muted.
 */
@Composable
fun PlanningItem(
    header: String,
    steps: List<PlanStep>,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = CardBackground),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Autorenew,
                    contentDescription = null,
                    tint = TextSecondary,
                    modifier = Modifier.size(20.dp)
                )
                Text(
                    text = header.uppercase(),
                    color = TextSecondary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 1.sp
                )
            }

            steps.forEachIndexed { index, step ->
                PlanStepRow(
                    step = step,
                    isLast = index == steps.lastIndex,
                    modifier = Modifier.padding(top = 16.dp)
                )
            }
        }
    }
}

@Composable
private fun PlanStepRow(
    step: PlanStep,
    isLast: Boolean,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(IntrinsicSize.Min),
        horizontalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Column(
            modifier = Modifier
                .width(28.dp)
                .fillMaxHeight(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            StepIndicator(step.status)
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .width(3.dp)
                        .fillMaxHeight()
                        .background(StepConnector)
                )
            }
        }

        Text(
            text = step.label,
            fontSize = 16.sp,
            lineHeight = 22.sp,
            color = when (step.status) {
                StepStatus.DONE -> TextPrimary
                StepStatus.IN_PROGRESS -> ShopAIRed
                StepStatus.TODO -> TextHint
            },
            fontWeight = if (step.status == StepStatus.IN_PROGRESS) {
                FontWeight.Bold
            } else {
                FontWeight.Normal
            },
            modifier = Modifier.padding(
                top = 3.dp,
                bottom = if (isLast) 0.dp else 18.dp
            )
        )
    }
}

@Composable
private fun StepIndicator(status: StepStatus) {
    when (status) {
        StepStatus.DONE -> Box(
            modifier = Modifier
                .size(28.dp)
                .background(ShopAIRed, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.Check,
                contentDescription = "Done",
                tint = Color.White,
                modifier = Modifier.size(17.dp)
            )
        }

        StepStatus.IN_PROGRESS -> Box(
            modifier = Modifier
                .size(28.dp)
                .border(width = 3.dp, color = ShopAIRed, shape = CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .size(11.dp)
                    .background(ShopAIRed, CircleShape)
            )
        }

        StepStatus.TODO -> Box(
            modifier = Modifier
                .size(28.dp)
                .background(StepPending, CircleShape)
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFFF5F5F7)
@Composable
private fun PlanningItemPreview() {
    ShopAITheme {
        PlanningItem(
            header = "Sia is thinking...",
            steps = listOf(
                PlanStep("Planning the research", StepStatus.DONE),
                PlanStep("Thinking", StepStatus.DONE),
                PlanStep("Collecting references", StepStatus.IN_PROGRESS),
                PlanStep("Validating research", StepStatus.TODO)
            ),
            modifier = Modifier.padding(16.dp)
        )
    }
}
