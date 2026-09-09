from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from shopai.api.app import app

client = TestClient(app)


def test_a_new_run_returns_its_run_id():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    assert response.status_code == 200
    assert response.json()["runId"] == "run-1"


def test_a_low_tier_reply_comes_back_as_a_message_not_a_plan():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "How do you usually like to dress?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    body = response.json()
    assert body["kind"] == "message"
    assert body["message"] == "How do you usually like to dress?"


def test_a_continued_run_reuses_the_supplied_run_id():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "", "raw": "",
            "run_id": "run-1", "clarity": {"tier": "medium"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "something in navy", "userToken": "tok", "runId": "run-1"},
        )

    passed = shopai.return_value.run_master_recommendation.call_args
    assert passed.kwargs["run_id"] == "run-1"


def test_both_turns_are_appended_to_the_transcript():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem:
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    senders = [c.args[1] for c in mem.conversation.append.call_args_list]
    assert senders == ["user", "agent"]


def test_compaction_is_attempted_after_the_turn():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem, \
         patch("shopai.api.app.user_id_from_token", return_value="user-1"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    mem.conversation.compact.assert_called_once_with("user-1", "run-1")


def test_a_compaction_failure_does_not_cost_the_user_their_answer():
    """Mem0 raises outright when MEM0_API_KEY is unset. Housekeeping must not
    turn into a 500."""
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem, \
         patch("shopai.api.app.user_id_from_token", return_value="user-1"):
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        mem.conversation.compact.side_effect = RuntimeError("Mem0 is not configured.")
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "tok"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "What's the occasion?"


def test_an_expired_session_token_does_not_500_the_plan():
    """Regression: a Supabase access token is short-lived (~1h) and the app
    does not refresh it, so this is routine, not exceptional. Recording the
    transcript must not be able to block the plan itself."""
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem:
        mem.conversation.append.side_effect = Exception("JWT expired")
        shopai.return_value.run_validation.return_value = {
            "allowed": True, "rejection": "", "message": "", "findings": {}
        }
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "help me with my style", "userToken": "stale-tok"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "message"
    assert body["message"] == "What's the occasion?"


def test_an_out_of_scope_request_is_still_refused():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = {
            "allowed": False, "rejection": "out_of_scope",
            "message": "This is a shopping bot, I cannot help with that request.",
            "findings": {},
        }
        response = client.post(
            "/outfit/plan/regular",
            json={"prompt": "debug my python", "userToken": "tok"},
        )

    body = response.json()
    assert body["kind"] == "error"
    assert body["errorKind"] == "out_of_scope"
