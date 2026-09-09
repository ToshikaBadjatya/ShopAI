from shopai.tools.clarification_tools import GAP_PRIORITY, FindMissingSegmentsTool


def _run(text: str) -> str:
    return FindMissingSegmentsTool()._run(text)


def _gap_line(text: str) -> str:
    """The first line names the gap. The lines after it name what is already
    known, which mentions dimensions too - so assertions about the gap have to
    look here, not at the whole output."""
    return _run(text).splitlines()[0]


def test_returns_plain_text_not_json():
    """A 31B model relaying one string is far more reliable than the same
    model parsing a JSON blob and then reformatting it."""
    out = _run("help me with my style")
    assert not out.strip().startswith("{")


def test_names_one_gap_at_a_time_not_the_whole_missing_list():
    """Three dimensions are missing here; the agent should be pointed at one."""
    line = _gap_line("wedding guest dress")
    named = [dim for dim in GAP_PRIORITY if dim in line]
    assert named == ["colors"], f"expected only the next gap named, got {named}"


def test_the_heaviest_missing_dimension_comes_first():
    """Event and outfit type are double-weighted, so closing them moves a
    request toward plannable in the fewest questions."""
    line = _gap_line("something in navy")
    assert "event" in line
    assert "colors" not in line


def test_asks_about_event_first_when_nothing_is_known():
    out = _run("help me with my style")
    assert "INCOMPLETE" in out
    assert "event" in out
    assert "nothing yet" in out


def test_reports_what_is_already_known():
    out = _run("wedding guest dress")
    assert "event" in out.split("Already known:")[1]
    assert "outfit_type" in out.split("Already known:")[1]


def test_complete_once_high_tier_is_reached():
    """The same bar the rest of the system uses for plannable - not a second,
    stricter definition of 'enough'."""
    text = "black fitted midi dress for a cocktail party with gold jewellery"
    out = _run(text)

    assert "COMPLETE" in out
    assert "INCOMPLETE" not in out


def test_the_cumulative_request_is_the_accumulated_conversation():
    """Rebuilding from matched keywords alone would drop nuance like 'for my
    cousin's sangeet' in favour of the bare word 'sangeet'."""
    text = (
        "navy fitted saree for my cousin's sangeet with gold jewellery and "
        "matching heels"
    )
    out = _run(text)

    assert "COMPLETE" in out
    assert text in out


def test_high_tier_still_leaves_a_dimension_unasked():
    """High is 5 of 7, so a request can be plannable with a gap still open -
    the tool must stop asking anyway rather than chase all five."""
    text = "navy saree for my cousin's sangeet"
    out = _run(text)

    assert "COMPLETE" in out
