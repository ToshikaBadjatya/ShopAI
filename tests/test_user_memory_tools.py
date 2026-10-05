import json
from unittest.mock import patch

from shopai.memory.user_memory import LIST_FIELDS, TEXT_FIELDS
from shopai.tools.user_memory_tools import (
    GetUserMemoryTool, UpdateUserMemoryTool, user_memory_tools,
)

TEXT = "I always avoid maroon. Show me a dress."


def _update(field, value, evidence, user_text=TEXT, token="tok"):
    with patch("shopai.tools.user_memory_tools.memory") as mem:
        mem.user_info.read.return_value = {"colors_that_work": ["Maroon", "sage"]}
        tool = UpdateUserMemoryTool(access_token=token, user_text=user_text)
        out = json.loads(tool._run(field=field, value=value, evidence=evidence))
    return out, mem


def test_a_rule_passing_fact_is_merged_and_written_with_the_bound_token():
    out, mem = _update("colors_to_avoid", ["maroon"], "I always avoid maroon")
    assert out["ok"] is True
    mem.user_info.write.assert_called_once_with(
        values={"colors_to_avoid": ["maroon"], "colors_that_work": ["sage"]}, access_token="tok"
    )


def test_evidence_not_in_the_shoppers_words_writes_nothing():
    out, mem = _update("colors_to_avoid", ["maroon"], "I hate maroon")
    assert out["ok"] is False
    mem.user_info.write.assert_not_called()


def test_a_guest_cannot_write():
    out, mem = _update("colors_to_avoid", ["maroon"], "I always avoid maroon", token="")
    assert out["ok"] is False
    mem.user_info.read.assert_not_called()
    mem.user_info.write.assert_not_called()


def test_the_wrong_value_shape_is_refused():
    out, mem = _update("height", ["5'4"], "I always avoid maroon")
    assert out["ok"] is False
    mem.user_info.write.assert_not_called()


def test_a_save_failure_is_reported_not_raised():
    with patch("shopai.tools.user_memory_tools.memory") as mem:
        mem.user_info.read.return_value = {}
        mem.user_info.write.side_effect = Exception("JWT expired")
        tool = UpdateUserMemoryTool(access_token="tok", user_text=TEXT)
        out = json.loads(tool._run(field="colors_to_avoid", value=["maroon"], evidence="I always avoid maroon"))
    assert out["ok"] is False


def test_the_update_tool_offers_exactly_the_twelve_fields_and_no_user_id():
    schema = UpdateUserMemoryTool().args_schema.model_json_schema()
    assert set(schema["properties"]["field"]["enum"]) == set(TEXT_FIELDS + LIST_FIELDS)
    assert len(TEXT_FIELDS + LIST_FIELDS) == 12
    assert "user_id" not in schema["properties"]


def _get(row, field=None, token="tok"):
    with patch("shopai.tools.user_memory_tools.memory") as mem:
        mem.user_info.read.return_value = row
        args = {"field": field} if field else {}
        return json.loads(GetUserMemoryTool(access_token=token)._run(**args)), mem


def test_get_returns_the_requested_field():
    out, _ = _get({"height": "5'4", "body_type": "pear"}, field="height")
    assert out == {"height": "5'4"}


def test_get_returns_every_filled_field_but_never_the_id_or_details():
    row = {"user_id": "u1", "height": "5'4", "body_type": "", "preferred_styles": ["minimal"],
           "culture_summary": "Marwari family", "details": {"phone": "1"}}
    out, _ = _get(row)
    assert out == {"height": "5'4", "preferred_styles": ["minimal"], "culture_summary": "Marwari family"}


def test_get_for_a_guest_is_empty_and_reads_nothing():
    out, mem = _get({"height": "5'4"}, token="")
    assert out == {}
    mem.user_info.read.assert_not_called()


def test_get_read_failure_is_empty():
    with patch("shopai.tools.user_memory_tools.memory") as mem:
        mem.user_info.read.side_effect = Exception("JWT expired")
        assert json.loads(GetUserMemoryTool(access_token="tok")._run()) == {}


def test_the_factory_binds_both_tools():
    names = {t.name for t in user_memory_tools("tok", TEXT)}
    assert names == {"get_user_memory", "update_user_memory"}
