from shopai.conversation_summary import (
    KEEP_RECENT_TURNS, SUMMARIZE_AFTER_CHARS, SUMMARIZE_AFTER_TURNS,
    request_context, should_summarize, split_for_fold,
)


def _turns(n, sender="user", text="x"):
    return [{"sender": sender, "message": f"{text}{i}", "created_at": f"t{i:02d}"} for i in range(n)]


def test_does_not_summarise_at_the_turn_threshold():
    assert should_summarize(_turns(SUMMARIZE_AFTER_TURNS)) is False


def test_summarises_once_past_the_turn_threshold():
    assert should_summarize(_turns(SUMMARIZE_AFTER_TURNS + 1)) is True


def test_summarises_when_few_turns_are_long():
    long_turns = [{"sender": "user", "message": "w" * (SUMMARIZE_AFTER_CHARS + 1), "created_at": "t0"}]
    assert should_summarize(long_turns) is True


def test_nothing_to_summarise_is_not_a_trigger():
    assert should_summarize([]) is False


def test_fold_keeps_the_most_recent_turns_verbatim_and_in_order():
    turns = _turns(10)
    to_fold, recent = split_for_fold(turns)
    assert recent == turns[-KEEP_RECENT_TURNS:]
    assert to_fold == turns[:-KEEP_RECENT_TURNS]


def test_a_short_run_folds_nothing():
    turns = _turns(KEEP_RECENT_TURNS)
    assert split_for_fold(turns) == ([], turns)


def test_context_with_no_summary_is_every_user_turn_on_one_line():
    turns = [
        {"sender": "user", "message": "I need a dress", "created_at": "t0"},
        {"sender": "agent", "message": "What's the occasion?", "created_at": "t1"},
        {"sender": "user", "message": "for a wedding,\nin navy", "created_at": "t2"},
    ]
    assert request_context("", turns) == "I need a dress for a wedding, in navy"


def test_context_puts_the_summary_before_the_recent_turns():
    turns = [{"sender": "user", "message": "make it cheaper", "created_at": "t9"}]
    assert request_context("navy wedding dress, avoid maroon", turns) == (
        "navy wedding dress, avoid maroon make it cheaper"
    )


def test_context_ignores_the_agents_own_turns():
    turns = [{"sender": "agent", "message": "Any colours you love?", "created_at": "t0"}]
    assert request_context("", turns) == ""
