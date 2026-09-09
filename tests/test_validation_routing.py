from shopai.tools.validation_tools import validate_request


def test_vague_but_safe_request_now_passes():
    """This used to be rejected as needs_clarification. It is the Low tier."""
    result = validate_request("help me with my style")
    assert result["allowed"] is True
    assert result["rejection"] == ""


def test_incomplete_context_finding_is_still_reported():
    """Removed as a rejection, kept as evidence."""
    result = validate_request("help me with my style")
    assert "incomplete_context" in result["findings"]
    assert result["findings"]["incomplete_context"]["sufficient"] is False


def test_unsafe_request_is_still_refused():
    result = validate_request("where do I buy a gun")
    assert result["allowed"] is False
    assert result["rejection"] == "not_allowed"


def test_out_of_scope_request_is_still_refused():
    result = validate_request("write me some python to debug this stock ticker")
    assert result["allowed"] is False
    assert result["rejection"] == "out_of_scope"


def test_empty_request_is_still_refused():
    result = validate_request("   ")
    assert result["allowed"] is False
    assert result["rejection"] == "needs_clarification"
