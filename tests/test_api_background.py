from unittest.mock import patch

from fastapi.testclient import TestClient

from shopai.api import app as api
from shopai.api.app import app

client = TestClient(app)

ALLOWED = {"allowed": True, "rejection": "", "message": "", "findings": {}}
QUESTION = {
    "recommendations": [], "summary": "What's the occasion?", "raw": "",
    "run_id": "run-1", "clarity": {"tier": "low"},
}


def _plan(token):
    body = {"prompt": "help me with my style"}
    if token:
        body["userToken"] = token
    with patch("shopai.api.app.Shopai") as shopai, patch("shopai.api.app.memory") as mem:
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.return_value = QUESTION
        response = client.post("/outfit/plan/regular", json=body)
    return response, shopai, mem


def test_a_signed_in_request_schedules_maintenance_for_its_run():
    response, shopai, _ = _plan("tok")
    assert response.status_code == 200
    shopai.return_value.maintain_conversation.assert_called_once_with("run-1", "tok", final=False)


def test_a_guest_request_schedules_nothing():
    _, shopai, _ = _plan(None)
    shopai.return_value.maintain_conversation.assert_not_called()


def test_the_dead_mem0_compaction_is_no_longer_called():
    _, _, mem = _plan("tok")
    mem.conversation.compact.assert_not_called()


def test_a_maintenance_failure_never_reaches_the_user():
    with patch("shopai.api.app.Shopai") as shopai, patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.return_value = QUESTION
        shopai.return_value.maintain_conversation.side_effect = Exception("model unreachable")
        response = client.post(
            "/outfit/plan/regular", json={"prompt": "help me with my style", "userToken": "tok"}
        )
    assert response.status_code == 200
    assert response.json()["kind"] == "message"


def test_two_overlapping_maintenance_runs_for_one_chat_do_not_both_work():
    api._maintaining.add("run-9")
    try:
        with patch("shopai.api.app.Shopai") as shopai:
            api._maintain("run-9", "tok")
        shopai.return_value.maintain_conversation.assert_not_called()
    finally:
        api._maintaining.discard("run-9")


def test_the_overlap_guard_is_released_afterwards():
    with patch("shopai.api.app.Shopai") as shopai:
        shopai.return_value.maintain_conversation.side_effect = Exception("boom")
        api._maintain("run-8", "tok")
    assert "run-8" not in api._maintaining


def test_ending_a_chat_with_a_token_finalises_it_and_clears_the_ledger():
    with patch("shopai.api.app.Shopai") as shopai, patch("shopai.api.app.memory") as mem:
        mem.task.delete.return_value = True
        response = client.delete("/task/run-1", headers={"Authorization": "Bearer tok"})
    assert response.json() == {"cleared": True}
    shopai.return_value.maintain_conversation.assert_called_once_with("run-1", "tok", final=True)


def test_ending_a_chat_without_a_token_only_clears_the_ledger():
    with patch("shopai.api.app.Shopai") as shopai, patch("shopai.api.app.memory") as mem:
        mem.task.delete.return_value = True
        response = client.delete("/task/run-1")
    assert response.json() == {"cleared": True}
    shopai.return_value.maintain_conversation.assert_not_called()


def test_a_malformed_authorization_header_is_ignored():
    with patch("shopai.api.app.Shopai") as shopai, patch("shopai.api.app.memory") as mem:
        mem.task.delete.return_value = True
        client.delete("/task/run-1", headers={"Authorization": "Basic abc"})
    shopai.return_value.maintain_conversation.assert_not_called()
