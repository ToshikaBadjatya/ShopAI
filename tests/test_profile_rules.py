import pytest

from shopai.profile_rules import check_fact, merge_fact, normalize_value


def _ok(field, value, evidence, text):
    ok, reason = check_fact(field, value, evidence, text)
    return ok, reason


def test_unknown_fields_are_refused():
    assert _ok("details", "x", "I am tall", "I am tall")[0] is False


def test_evidence_must_be_the_shoppers_words():
    ok, reason = _ok("colors_to_avoid", ["maroon"], "I always avoid maroon", "show me a dress")
    assert ok is False and "evidence" in reason


def test_a_lasting_first_person_preference_is_accepted():
    text = "I always avoid maroon. Show me a dress."
    assert _ok("colors_to_avoid", ["maroon"], "I always avoid maroon", text)[0] is True


def test_a_one_off_want_is_not_a_lasting_preference():
    text = "For this wedding I want red"
    ok, reason = _ok("colors_that_work", ["red"], "I want red", text)
    assert ok is False and "lasting" in reason


def test_a_statement_about_someone_else_is_refused():
    text = "my cousin is 6 feet tall"
    ok, reason = _ok("height", "6 feet", "cousin is 6 feet tall", text)
    assert ok is False and "someone else" in reason


def test_a_first_person_attribute_is_accepted():
    assert _ok("height", "5'4", "I'm 5'4", "I'm 5'4 and want a dress")[0] is True


def test_a_sentence_without_i_or_my_is_refused():
    ok, reason = _ok("body_type", "pear", "pear shaped", "pear shaped people suit a-line")
    assert ok is False and "shopper" in reason


def test_volunteered_background_is_accepted_for_culture_summary():
    text = "I grew up in a Marwari family, so I wear a lot of bandhani."
    assert _ok("culture_summary", "Marwari family", "I grew up in a Marwari family", text)[0] is True


def test_evidence_cannot_straddle_two_sentences():
    text = "I like linen. Always cotton."
    ok, _ = _ok("preferred_fabrics", ["cotton"], "linen. Always cotton", text)
    assert ok is False


@pytest.mark.parametrize("field,value,expected", [
    ("height", "  5'4 ", "5'4"),
    ("colors_that_work", "sage", ["sage"]),
    ("colors_that_work", [" sage ", "", "Navy"], ["sage", "Navy"]),
])
def test_normalize_value_accepts_the_right_shapes(field, value, expected):
    assert normalize_value(field, value) == expected


@pytest.mark.parametrize("field,value", [
    ("height", ["5'4"]),
    ("height", ""),
    ("colors_that_work", []),
    ("colors_that_work", 5),
    ("height", "x" * 201),
])
def test_normalize_value_refuses_the_wrong_shapes(field, value):
    assert normalize_value(field, value) is None


def test_text_fields_replace():
    assert merge_fact({"height": "5'2"}, "height", "5'4") == {"height": "5'4"}


def test_list_fields_merge_without_case_duplicates():
    row = {"preferred_fabrics": ["Linen"]}
    assert merge_fact(row, "preferred_fabrics", ["linen", "cotton"]) == {
        "preferred_fabrics": ["Linen", "cotton"]
    }


def test_a_colour_added_to_avoid_leaves_the_works_list():
    row = {"colors_that_work": ["Maroon", "sage"], "colors_to_avoid": []}
    assert merge_fact(row, "colors_to_avoid", ["maroon"]) == {
        "colors_to_avoid": ["maroon"],
        "colors_that_work": ["sage"],
    }


def test_a_colour_added_to_works_leaves_the_avoid_list():
    row = {"colors_that_work": [], "colors_to_avoid": ["Sage"]}
    assert merge_fact(row, "colors_that_work", ["sage"]) == {
        "colors_that_work": ["sage"],
        "colors_to_avoid": [],
    }
