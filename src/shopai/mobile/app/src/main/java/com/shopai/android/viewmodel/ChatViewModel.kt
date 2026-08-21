package com.shopai.android.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.ChatItem
import com.shopai.android.data.model.ErrorKind
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.PlanStep
import com.shopai.android.data.model.StepStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Owns the conversation with Sia. Held at activity scope so the screen that starts a
 * request and the screen that shows it are talking to the same transcript.
 */
class ChatViewModel : ViewModel() {

    private val _items = MutableStateFlow<List<ChatItem>>(emptyList())
    val items: StateFlow<List<ChatItem>> = _items.asStateFlow()

    private val _selectedOptionIds = MutableStateFlow<Set<String>>(emptySet())
    val selectedOptionIds: StateFlow<Set<String>> = _selectedOptionIds.asStateFlow()

    private val _isPlanning = MutableStateFlow(false)
    val isPlanning: StateFlow<Boolean> = _isPlanning.asStateFlow()

    /** Results of the last successful plan. Deliberately kept out of the transcript. */
    private val _planIdeas = MutableStateFlow<List<OutfitPlanResponse>>(emptyList())
    val planIdeas: StateFlow<List<OutfitPlanResponse>> = _planIdeas.asStateFlow()

    // ---------------------------------------------------------------- transcript

    /** Replaces the whole transcript. */
    fun setChat(items: List<ChatItem>) {
        _items.value = items
    }

    fun append(item: ChatItem) {
        _items.value = _items.value + item
    }

    fun appendAll(items: List<ChatItem>) {
        _items.value = _items.value + items
    }

    /** Swaps the item carrying the same id, leaving the rest untouched. */
    fun replace(item: ChatItem) {
        _items.value = _items.value.map { existing ->
            if (existing.id == item.id) item else existing
        }
    }

    fun clear() {
        _items.value = emptyList()
        _selectedOptionIds.value = emptySet()
        _planIdeas.value = emptyList()
    }

    fun selectOption(optionId: String, multiSelect: Boolean = false) {
        _selectedOptionIds.value = when {
            !multiSelect -> setOf(optionId)
            optionId in _selectedOptionIds.value -> _selectedOptionIds.value - optionId
            else -> _selectedOptionIds.value + optionId
        }
    }

    // ----------------------------------------------------------------- planning

    /**
     * Posts [moodText] as the user's message and asks the backend for looks:
     * `outfit/plan/occasional` when [occasional], otherwise `outfit/plan`.
     */
    fun planOutfit(
        moodText: String,
        vibes: List<String> = emptyList(),
        occasional: Boolean = false
    ) {
        val prompt = composePrompt(moodText, vibes)
        if (prompt.isBlank() || _isPlanning.value) return

        append(ChatItem.UserMessage(id = newId(), text = prompt))
        append(
            ChatItem.AssistantMessage(
                id = newId(),
                text = "On it, bestie! I'm curating a look for you right now."
            )
        )

        val planId = newId()
        var steps = listOf(
            PlanStep(STEP_UNDERSTANDING, StepStatus.IN_PROGRESS),

        )
        append(ChatItem.PlanBlock(id = planId, steps = steps))

        viewModelScope.launch {
            _isPlanning.value = true
            _planIdeas.value = emptyList()
            try {
                val request = OutfitPlanRequest(prompt = prompt)
                val response = if (occasional) {
                    RetrofitClient.apiService.planOccasionalOutfit(request)
                } else {
                    RetrofitClient.apiService.planOutfit(request)
                }

                if (response.isSuccessful) {
                    steps = steps.markDone(STEP_CURATING).inProgress(STEP_FINISHING)
                    replace(ChatItem.PlanBlock(id = planId, steps = steps))

                    _planIdeas.value = response.body() ?: emptyList()

                    steps = steps.markDone(STEP_FINISHING)
                    replace(ChatItem.PlanBlock(id = planId, steps = steps))
                } else {
                    failPlanning(planId, steps, "Sia couldn't plan this one (${response.code()}).")
                }
            } catch (e: Exception) {
                failPlanning(
                    planId,
                    steps,
                    e.message ?: "System is down and we'll be back shortly."
                )
            } finally {
                _isPlanning.value = false
            }
        }
    }

    private fun failPlanning(planId: String, steps: List<PlanStep>, message: String) {
        replace(ChatItem.PlanBlock(id = planId, steps = steps.stall()))
        append(
            ChatItem.Error(
                id = newId(),
                text = message,
                kind = ErrorKind.SYSTEM_DOWN
            )
        )
    }

    private fun composePrompt(moodText: String, vibes: List<String>): String {
        val vibesText = vibes.joinToString(", ")
        return when {
            moodText.isNotBlank() && vibesText.isNotBlank() -> "$moodText. Vibe: $vibesText"
            moodText.isNotBlank() -> moodText
            else -> vibesText
        }
    }

    private fun newId(): String = UUID.randomUUID().toString()

    private fun List<PlanStep>.markDone(label: String) = map { step ->
        if (step.label == label) step.copy(status = StepStatus.DONE) else step
    }

    private fun List<PlanStep>.inProgress(label: String) = map { step ->
        if (step.label == label) step.copy(status = StepStatus.IN_PROGRESS) else step
    }

    /** Drops any running step back to pending - the work stopped, it did not finish. */
    private fun List<PlanStep>.stall() = map { step ->
        if (step.status == StepStatus.IN_PROGRESS) step.copy(status = StepStatus.TODO) else step
    }

    private companion object {
        const val STEP_UNDERSTANDING = "Understanding your mood"
        const val STEP_CURATING = "Curating your looks"
        const val STEP_FINISHING = "Finishing touches"
    }
}
