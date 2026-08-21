package com.shopai.android.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AddCircleOutline
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shopai.android.data.model.ChatItem
import com.shopai.android.data.model.ChatOption
import com.shopai.android.data.model.ErrorKind
import com.shopai.android.data.model.PlanStep
import com.shopai.android.data.model.StepStatus
import com.shopai.android.reusables.ShopAITopBar
import com.shopai.android.reusables.chat.AssistantMessageItem
import com.shopai.android.reusables.chat.ErrorItem
import com.shopai.android.reusables.chat.OptionsItem
import com.shopai.android.reusables.chat.PermissionItem
import com.shopai.android.reusables.chat.PlanningItem
import com.shopai.android.reusables.chat.UserMessageItem
import com.shopai.android.ui.theme.Background
import com.shopai.android.ui.theme.ChatInputBackground
import com.shopai.android.ui.theme.ShopAIRed
import com.shopai.android.ui.theme.ShopAITheme
import com.shopai.android.ui.theme.TextHint
import com.shopai.android.ui.theme.TextPrimary
import com.shopai.android.ui.theme.TextSecondary

/**
 * Conversation with Sia. Every row is a [ChatItem]; the screen itself holds no state
 * beyond the draft message, so the caller owns the transcript and the selections.
 */
@Composable
fun ChatScreen(
    items: List<ChatItem>,
    modifier: Modifier = Modifier,
    title: String = "Chat with Sia",
    selectedOptionIds: Set<String> = emptySet(),
    onOptionSelected: (blockId: String, optionId: String) -> Unit = { _, _ -> },
    onBack: () -> Unit = {},
    onSendMessage: (String) -> Unit = {},
    onAttach: () -> Unit = {},
    onQuickReply: (itemId: String, reply: String) -> Unit = { _, _ -> },
    onPermissionAllow: (itemId: String) -> Unit = {},
    onPermissionDeny: (itemId: String) -> Unit = {},
    onPermissionDetails: (itemId: String) -> Unit = {}
) {
    val listState = rememberLazyListState()

    LaunchedEffect(items.size) {
        if (items.isNotEmpty()) {
            listState.animateScrollToItem(items.lastIndex)
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = { ShopAITopBar(title = title, showBack = true, onBack = onBack) },
        bottomBar = { ChatInputBar(onSend = onSendMessage, onAttach = onAttach) },
        containerColor = Background
    ) { padding ->
        LazyColumn(
            state = listState,
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            items(items = items, key = { it.id }) { item ->
                when (item) {
                    is ChatItem.UserMessage -> UserMessageItem(text = item.text)

                    is ChatItem.AssistantMessage -> AssistantMessageItem(text = item.text)

                    is ChatItem.Error -> ErrorItem(
                        text = item.text,
                        kind = item.kind,
                        quickReplies = item.quickReplies,
                        onQuickReply = { reply -> onQuickReply(item.id, reply) }
                    )

                    is ChatItem.Permission -> PermissionItem(
                        text = item.text,
                        allowLabel = item.allowLabel,
                        denyLabel = item.denyLabel,
                        detailsLabel = item.detailsLabel,
                        onAllow = { onPermissionAllow(item.id) },
                        onDeny = { onPermissionDeny(item.id) },
                        onViewDetails = { onPermissionDetails(item.id) }
                    )

                    is ChatItem.PlanBlock -> PlanningItem(
                        header = item.header,
                        steps = item.steps
                    )

                    is ChatItem.OptionsBlock -> OptionsItem(
                        title = item.title,
                        options = item.options,
                        selectedIds = selectedOptionIds,
                        multiSelect = item.multiSelect,
                        onOptionSelected = { optionId -> onOptionSelected(item.id, optionId) }
                    )
                }
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    onSend: (String) -> Unit,
    onAttach: () -> Unit
) {
    var draft by remember { mutableStateOf("") }

    Surface(color = Color.White, shadowElevation = 8.dp) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .imePadding()
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .background(ChatInputBackground, RoundedCornerShape(32.dp))
                .padding(horizontal = 6.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onAttach) {
                Icon(
                    imageVector = Icons.Default.AddCircleOutline,
                    contentDescription = "Add attachment",
                    tint = TextSecondary
                )
            }

            TextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.weight(1f),
                placeholder = {
                    Text(text = "Type your message...", color = TextHint, fontSize = 16.sp)
                },
                textStyle = androidx.compose.ui.text.TextStyle(
                    color = TextPrimary,
                    fontSize = 16.sp
                ),
                singleLine = true,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    cursorColor = ShopAIRed
                )
            )

            IconButton(
                onClick = {
                    if (draft.isNotBlank()) {
                        onSend(draft.trim())
                        draft = ""
                    }
                },
                modifier = Modifier
                    .size(48.dp)
                    .background(ShopAIRed, CircleShape)
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Send,
                    contentDescription = "Send",
                    tint = Color.White,
                    modifier = Modifier.size(22.dp)
                )
            }
        }
    }
}

/** Sample transcript exercising every item type and every step state. */
internal val sampleChatItems: List<ChatItem> = listOf(
    ChatItem.UserMessage(
        id = "m1",
        text = "A bold late night party outfit with sleek fabrics, statement accessories, " +
            "and a dramatic silhouette. Show me outfit recommendations and help me choose one."
    ),
    ChatItem.AssistantMessage(
        id = "m2",
        text = "On it, bestie! I'm curating a high-drama party look for you right now."
    ),
    ChatItem.PlanBlock(
        id = "m3",
        header = "Sia is thinking...",
        steps = listOf(
            PlanStep("Planning the research", StepStatus.DONE),
            PlanStep("Thinking", StepStatus.DONE),
            PlanStep("Collecting references", StepStatus.IN_PROGRESS),
            PlanStep("Validating research", StepStatus.TODO)
        )
    ),
    ChatItem.OptionsBlock(
        id = "m4",
        title = "Curated for you:",
        options = listOf(
            ChatOption("o1", "Midnight Velvet Mini", "Sleek fabric, dramatic puffed sleeves."),
            ChatOption("o2", "Satin Slip & Leather", "Edge meets elegance."),
            ChatOption("o3", "Sequin Statement Jumpsuit", "For maximum impact."),
            ChatOption("o4", "Metallic Drape Gown", "Silky finish with a bold silhouette.")
        )
    )
)

/** Sample transcript of the states Sia cannot fulfil as asked. */
internal val sampleErrorChatItems: List<ChatItem> = listOf(
    ChatItem.Permission(
        id = "e1",
        text = "Sia needs permission to access your socials. View more to see the actions " +
            "performed."
    ),
    ChatItem.UserMessage(id = "e2", text = "What is the weather like today?"),
    ChatItem.Error(
        id = "e3",
        text = "I'm a shopping assistant, I cannot do this job.",
        kind = ErrorKind.OUT_OF_SCOPE
    ),
    ChatItem.UserMessage(id = "e4", text = "Hack this website."),
    ChatItem.Error(
        id = "e5",
        text = "I'm not allowed to perform this task. Ask for something else.",
        kind = ErrorKind.NOT_ALLOWED
    ),
    ChatItem.Error(
        id = "e6",
        text = "System is down and we'll be back till 4:00 PM.",
        kind = ErrorKind.SYSTEM_DOWN
    ),
    ChatItem.Error(
        id = "e7",
        text = "I'm not sure if I'm understanding it right. Are you looking for formal " +
            "shoes for a wedding?",
        kind = ErrorKind.CLARIFICATION,
        quickReplies = listOf("Yes, exactly", "No, casual")
    )
)

@Preview(showBackground = true, heightDp = 900)
@Composable
private fun ChatScreenPreview() {
    var selected by remember { mutableStateOf(setOf("o1")) }

    ShopAITheme {
        ChatScreen(
            items = sampleChatItems,
            selectedOptionIds = selected,
            onOptionSelected = { _, optionId -> selected = setOf(optionId) }
        )
    }
}

@Preview(showBackground = true, heightDp = 900)
@Composable
private fun ChatScreenMultiSelectPreview() {
    var selected by remember { mutableStateOf(setOf("o1", "o3")) }
    val items = sampleChatItems.map { item ->
        if (item is ChatItem.OptionsBlock) {
            item.copy(title = "Pick everything you like:", multiSelect = true)
        } else {
            item
        }
    }

    ShopAITheme {
        ChatScreen(
            items = items,
            selectedOptionIds = selected,
            onOptionSelected = { _, optionId ->
                selected = if (optionId in selected) selected - optionId else selected + optionId
            }
        )
    }
}

@Preview(showBackground = true, heightDp = 1000)
@Composable
private fun ChatScreenErrorStatesPreview() {
    ShopAITheme {
        ChatScreen(items = sampleErrorChatItems)
    }
}
