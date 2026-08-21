package com.shopai.android.data.model

/** State of a single step in a planning / thinking block. */
enum class StepStatus { DONE, IN_PROGRESS, TODO }

data class PlanStep(
    val label: String,
    val status: StepStatus = StepStatus.TODO
)

/** Flavour of a non-happy-path reply from Sia; drives icon and bubble colouring. */
enum class ErrorKind {
    /** Request is outside what a shopping assistant does. */
    OUT_OF_SCOPE,

    /** Request is refused on policy grounds. */
    NOT_ALLOWED,

    /** Sia is unavailable right now. */
    SYSTEM_DOWN,

    /** Sia understood only partly and is checking before acting. */
    CLARIFICATION
}

data class ChatOption(
    val id: String,
    val title: String,
    val subtitle: String = ""
)

/** One row in the chat [LazyColumn][androidx.compose.foundation.lazy.LazyColumn]. */
sealed interface ChatItem {
    val id: String

    data class UserMessage(
        override val id: String,
        val text: String
    ) : ChatItem

    data class AssistantMessage(
        override val id: String,
        val text: String
    ) : ChatItem

    data class PlanBlock(
        override val id: String,
        val header: String = "Sia is thinking...",
        val steps: List<PlanStep> = emptyList()
    ) : ChatItem

    data class Error(
        override val id: String,
        val text: String,
        val kind: ErrorKind = ErrorKind.OUT_OF_SCOPE,
        /** Optional one-tap answers rendered as chips under the bubble. */
        val quickReplies: List<String> = emptyList()
    ) : ChatItem

    data class Permission(
        override val id: String,
        val text: String,
        val allowLabel: String = "Allow",
        val denyLabel: String = "Deny",
        /** Link opening the full list of actions Sia wants to perform. */
        val detailsLabel: String = "View More"
    ) : ChatItem

    data class OptionsBlock(
        override val id: String,
        val title: String = "Curated for you:",
        val options: List<ChatOption> = emptyList(),
        /** true renders checkboxes and allows many selections, false renders radios. */
        val multiSelect: Boolean = false
    ) : ChatItem
}
