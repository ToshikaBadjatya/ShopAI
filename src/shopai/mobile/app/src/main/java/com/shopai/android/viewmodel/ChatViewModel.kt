package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.model.ChatItem
import com.shopai.android.data.model.ErrorKind
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.PlanResponse
import com.shopai.android.prefs.Session
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Owns the conversation with Sia. Held at activity scope so the screen that starts a
 * request and the screen that shows it are talking to the same transcript.
 */
class ChatViewModel(application: Application) : AndroidViewModel(application) {

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

    /** Drops the item carrying [id], if any. */
    fun remove(id: String) {
        _items.value = _items.value.filterNot { it.id == id }
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

    // ----------------------------------------------------------------- thinking

    /** Shows a muted line naming the work in flight, and returns its id. */
    fun startThinking(text: String = "Thinking..."): String {
        val id = newId()
        append(ChatItem.Thinking(id = id, text = text))
        return id
    }

    /** Swaps the line's text as the work moves on. */
    fun updateThinking(id: String, text: String) {
        replace(ChatItem.Thinking(id = id, text = text))
    }

    /** Puts [output] exactly where the thinking line was, dropping the line itself. */
    fun finishThinking(id: String, output: ChatItem) {
        _items.value = _items.value.map { item -> if (item.id == id) output else item }
    }

    /** Convenience for the common case: the thinking line becomes a reply from Sia. */
    fun finishThinking(id: String, text: String) {
        finishThinking(id, ChatItem.AssistantMessage(id = newId(), text = text))
    }

    // ----------------------------------------------------------------- planning

    /**
     * Posts the composed prompt as the user's message and asks the backend for looks:
     * `outfit/plan/occasional` when [occasional], otherwise `outfit/plan`. Progress
     * shows as a single thinking line, which the reply then takes the place of.
     */
    fun planOutfit(
        moodText: String,
        vibes: List<String> = emptyList(),
        occasional: Boolean = false
    ) {
        val prompt = composePrompt(moodText, vibes)
        if (prompt.isBlank() || _isPlanning.value) return

        append(ChatItem.UserMessage(id = newId(), text = prompt))
//        append(
//            ChatItem.AssistantMessage(
//                id = newId(),
//                text = "On it, bestie! I'm curating a look for you right now."
//            )
//        )

        val thinkingId = startThinking("Curating your looks...")

        viewModelScope.launch {
            _isPlanning.value = true
            _planIdeas.value = emptyList()
            try {
                val request = OutfitPlanRequest(
                    prompt = prompt,
                    userToken = Session.getAuth(getApplication()).accessToken.ifBlank { null }
                )
                val response = if (occasional) {
                    RetrofitClient.apiService.planOccasionalOutfit(request)
                } else {
                    RetrofitClient.apiService.planRegularOutfit(request)
                }

                val body = response.body()
                if (response.isSuccessful && body != null) {
                    handlePlanResponse(thinkingId, body)
                } else {
                    failPlanning(thinkingId, "Sia couldn't plan this one (${response.code()}).")
                }
            } catch (e: Exception) {
                failPlanning(
                    thinkingId,
                    e.message ?: "System is down and we'll be back shortly."
                )
            } finally {
                _isPlanning.value = false
            }
        }
    }

    /** Turns one envelope into whatever the transcript should show for it. */
    private fun handlePlanResponse(thinkingId: String, body: PlanResponse) {
        when (body.kind) {
            KIND_PLAN -> {
                _planIdeas.value = body.outfits
                finishThinking(
                    thinkingId,
                    body.message.ifBlank { ideasReadyText(body.outfits.size) }
                )
            }

            KIND_MESSAGE -> finishThinking(thinkingId, body.message)

            KIND_PERMISSION -> {
                remove(thinkingId)
                append(ChatItem.Permission(id = newId(), text = body.message))
            }

            KIND_ERROR -> failPlanning(thinkingId, body.message, errorKind(body.errorKind))

            // An unknown kind is a newer server talking to an older app: say the
            // message rather than dropping the turn on the floor.
            else -> finishThinking(
                thinkingId,
                body.message.ifBlank { "Sia sent something this version can't show yet." }
            )
        }
    }

    private fun errorKind(raw: String): ErrorKind = when (raw) {
        "out_of_scope" -> ErrorKind.OUT_OF_SCOPE
        "not_allowed" -> ErrorKind.NOT_ALLOWED
        "clarification" -> ErrorKind.CLARIFICATION
        else -> ErrorKind.SYSTEM_DOWN
    }

    /** Drops the thinking line - the work stopped, it did not finish - and says why. */
    private fun failPlanning(
        thinkingId: String,
        message: String,
        kind: ErrorKind = ErrorKind.SYSTEM_DOWN
    ) {
        remove(thinkingId)
        append(
            ChatItem.Error(
                id = newId(),
                text = message.ifBlank { "Something went wrong on Sia's side." },
                kind = kind
            )
        )
    }

    private fun ideasReadyText(count: Int): String = when (count) {
        0 -> "I couldn't pull a look together for that. Tell me a bit more?"
        1 -> "I've curated a look for you."
        else -> "I've curated $count looks for you."
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

    private companion object {
        const val KIND_PLAN = "plan"
        const val KIND_MESSAGE = "message"
        const val KIND_PERMISSION = "permission"
        const val KIND_ERROR = "error"
    }
}
