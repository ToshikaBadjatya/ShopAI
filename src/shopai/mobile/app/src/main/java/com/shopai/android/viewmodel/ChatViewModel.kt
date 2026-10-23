package com.shopai.android.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.shopai.android.data.api.RetrofitClient
import com.shopai.android.data.api.SupabaseAuth
import com.shopai.android.data.model.ChatItem
import com.shopai.android.data.model.ErrorKind
import com.shopai.android.data.model.OutfitPlanRequest
import com.shopai.android.data.model.OutfitPlanResponse
import com.shopai.android.data.model.PlanResponse
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
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

    /**
     * The run this conversation is on. Not UI state - nothing renders it - so a
     * plain var rather than a StateFlow. Set once per conversation in
     * [startNewConversation] and sent with every plan call after that, which is
     * what lets a vague request climb clarity tiers across turns instead of each
     * message starting a fresh run on the server.
     */
    private var currentRunId: String? = null

    /** The plan in flight - the POST, then the status polls after it. Cancelled by a stop. */
    private var planJob: Job? = null

    /** The thinking line that plan's progress is drawn on, so a stop can replace it. */
    private var planThinkingId: String? = null

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

    /**
     * Start a fresh conversation from a new request.
     *
     * A request arriving from the mood screen begins a new line of work, so the
     * previous transcript goes and a fresh run id is minted - every plan call
     * this conversation makes from here on carries it, which is what lets the
     * server treat a follow-up message as the same run rather than a new one.
     *
     * Clearing the *previous* run's task ledger is not this function's job -
     * that happens when the chat screen for that run is left, not when a new
     * one starts. See [clearCurrentTask].
     */
    fun startNewConversation(
        moodText: String,
        vibes: List<String> = emptyList(),
        occasional: Boolean = false
    ) {
        clear()
        currentRunId = newId()
        planOutfit(moodText = moodText, vibes = vibes, occasional = occasional)
    }

    /**
     * Drop the server's task ledger for the run this conversation is on.
     *
     * Called when the chat screen is left, not when a new conversation starts -
     * the ledger is scaffolding for one run, worthless once that run's screen is
     * gone. Best-effort: a failed cleanup must not block navigation, since the
     * user is already leaving.
     */
    fun clearCurrentTask() {
        // Nobody is left to read the polls. The server stops the run itself
        // when the ledger is cleared below.
        planJob?.cancel()
        val runId = currentRunId ?: return
        currentRunId = null
        viewModelScope.launch {
            try {
                RetrofitClient.apiService.clearTask(runId)
            } catch (e: Exception) {
                // Best-effort - see the doc comment above.
            }
        }
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
     * `outfit/plan/occasional` when [occasional], otherwise `outfit/plan/regular`.
     *
     * The backend answers a guardrail rejection at once; anything else comes back as
     * a `status` envelope - the plan runs in the background - and this polls
     * `outfit/plan/{runId}/status` every [POLL_INTERVAL_MS] until it succeeds, fails,
     * or is stopped. Progress shows on a single thinking line, which the reply then
     * takes the place of.
     */
    fun planOutfit(
        moodText: String,
        vibes: List<String> = emptyList(),
        occasional: Boolean = false
    ) {
        val prompt = composePrompt(moodText, vibes)
        if (prompt.isBlank() || _isPlanning.value) return

        append(ChatItem.UserMessage(id = newId(), text = prompt))

        val thinkingId = startThinking("Curating your looks...")
        planThinkingId = thinkingId

        // Set before the launch, not inside it: a second tap in between would
        // otherwise slip past the guard above.
        _isPlanning.value = true
        _planIdeas.value = emptyList()

        planJob = viewModelScope.launch {
            try {
                val request = OutfitPlanRequest(
                    prompt = prompt,
                    userToken = SupabaseAuth.freshAccessToken(getApplication()),
                    runId = currentRunId
                )
                val response = if (occasional) {
                    RetrofitClient.apiService.planOccasionalOutfit(request)
                } else {
                    RetrofitClient.apiService.planRegularOutfit(request)
                }

                val body = response.body()
                when {
                    !response.isSuccessful || body == null ->
                        failPlanning(thinkingId, "Sia couldn't plan this one (${response.code()}).")

                    body.kind == KIND_STATUS -> {
                        // A conversation that had no run yet is on the server's now.
                        if (currentRunId == null) currentRunId = body.runId
                        updateThinking(thinkingId, body.message.ifBlank { "Curating your looks..." })
                        pollUntilDone(thinkingId, body.runId)
                    }

                    else -> handlePlanResponse(thinkingId, body)
                }
            } catch (e: CancellationException) {
                // A stop or a screen exit - whoever cancelled has already said so.
                throw e
            } catch (e: Exception) {
                failPlanning(
                    thinkingId,
                    e.message ?: "System is down and we'll be back shortly."
                )
            } finally {
                _isPlanning.value = false
                planThinkingId = null
            }
        }
    }

    /**
     * Polls a background run until it is no longer `running`, then shows how it ended.
     *
     * A failed poll is retried - one dropped request on mobile data is not a failed
     * plan - but [MAX_POLL_FAILURES] in a row is. A run the server no longer knows
     * (404: restarted, or long finished) is over. [MAX_POLL_MS] caps the whole wait.
     */
    private suspend fun pollUntilDone(thinkingId: String, runId: String) {
        val deadline = System.currentTimeMillis() + MAX_POLL_MS
        var lastStep = -1
        var failures = 0

        while (true) {
            delay(POLL_INTERVAL_MS)

            if (System.currentTimeMillis() > deadline) {
                stopOnServer(runId)
                failPlanning(thinkingId, "Sia is taking too long on this one. Try again in a bit.")
                return
            }

            val response = try {
                RetrofitClient.apiService.planStatus(runId)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (++failures >= MAX_POLL_FAILURES) {
                    failPlanning(thinkingId, e.message ?: "Lost touch with Sia. Try again?")
                    return
                }
                continue
            }

            if (response.code() == 404) {
                failPlanning(thinkingId, "Sia lost track of this one. Try asking again.")
                return
            }

            val body = response.body()
            if (!response.isSuccessful || body == null) {
                if (++failures >= MAX_POLL_FAILURES) {
                    failPlanning(thinkingId, "Sia couldn't plan this one (${response.code()}).")
                    return
                }
                continue
            }
            failures = 0

            if (body.state == STATE_RUNNING) {
                if (body.step != lastStep && body.message.isNotBlank()) {
                    updateThinking(thinkingId, body.message)
                    lastStep = body.step
                }
                continue
            }

            handlePlanResponse(thinkingId, body)
            return
        }
    }

    /**
     * The user's stop. Polling ends here and now; the server is asked to stop the
     * crew too, best-effort - it ends at its next step, and nobody needs to wait
     * for that to say so.
     */
    fun stopPlanning() {
        val job = planJob ?: return
        if (!job.isActive) return
        job.cancel()

        planThinkingId?.let { finishThinking(it, "Stopped. Tell me when you want to pick it back up.") }
        planThinkingId = null
        _isPlanning.value = false

        currentRunId?.let { runId -> viewModelScope.launch { stopOnServer(runId) } }
    }

    private suspend fun stopOnServer(runId: String) {
        try {
            RetrofitClient.apiService.stopPlan(runId)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // Best-effort - see stopPlanning.
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

            // Only a poll loop should see this, but a stray one still means "working on it".
            KIND_STATUS -> updateThinking(thinkingId, body.message.ifBlank { "Still working..." })

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
        const val KIND_STATUS = "status"
        const val STATE_RUNNING = "running"

        const val POLL_INTERVAL_MS = 5_000L
        const val MAX_POLL_FAILURES = 3
        const val MAX_POLL_MS = 15 * 60 * 1_000L
    }
}
