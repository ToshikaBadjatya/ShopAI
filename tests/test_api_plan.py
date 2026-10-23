from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from shopai.api.app import app
from shopai.runs import runs

client = TestClient(app)


@pytest.fixture(autouse=True)
def _inline_runs():
    """Run the background job inside the request, so the patches still apply
    and a status poll right after the POST sees how it ended."""
    runs.clear()
    with patch("shopai.api.app._spawn", side_effect=lambda job: job()):
        yield
    runs.clear()


def _final(response):
    """The envelope the client ends up with: the POST's, or the poll's after it."""
    body = response.json()
    if body.get("kind") != "status":
        return body
    return client.get(f"/outfit/plan/{body['runId']}/status").json()


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
    assert _final(response)["runId"] == "run-1"


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

    body = _final(response)
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
    assert _final(response)["message"] == "What's the occasion?"


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
    body = _final(response)
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


def test_top_pick_rides_on_the_plan_message():
    from shopai.api.app import OutfitPlanResponse, _plan_result

    plan = _plan_result([OutfitPlanResponse(outfitName="Pastel brunch")], top_pick="Go with Pastel brunch - lightest.")
    assert plan.kind == "plan"
    assert plan.message == "Go with Pastel brunch - lightest."


def test_parser_keeps_the_top_pick():
    from shopai.crew import Shopai

    raw = '{"recommendations": [{"outfit_name": "A", "products": []}], "top_pick": "A - cooler."}'
    assert Shopai()._parse_recommendation_crew_output(raw)["top_pick"] == "A - cooler."


def test_lifespan_starts_tracing_and_clears_the_plan_store_on_exit():
    from shopai.api import app as app_module

    app_module._plan_store["p"] = {"recommendation": {}}
    with patch("shopai.api.app.setup_telemetry") as setup:
        with TestClient(app):  # entering the context runs startup
            setup.assert_called_once()
            assert "p" in app_module._plan_store
        # leaving it runs shutdown
    assert app_module._plan_store == {}


def test_importing_the_app_does_not_start_tracing():
    """Tests build TestClient(app) bare; that must not register Arize."""
    with patch("shopai.api.app.setup_telemetry") as setup:
        TestClient(app).get("/openapi.json")
    setup.assert_not_called()


# ---------------------------------------------------------------------------
# Background runs: status, stop, busy
# ---------------------------------------------------------------------------

ALLOWED = {"allowed": True, "rejection": "", "message": "", "findings": {}}


def test_an_allowed_request_returns_a_running_status_at_once():
    with patch("shopai.api.app._spawn"), \
         patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        response = client.post(
            "/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"}
        )

    body = response.json()
    assert body["kind"] == "status"
    assert body["state"] == "running"
    assert body["runId"] == "run-1"
    shopai.return_value.run_master_recommendation.assert_not_called()


def test_a_poll_while_running_says_what_the_master_is_doing():
    with patch("shopai.api.app._spawn"), \
         patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory") as mem:
        shopai.return_value.run_validation.return_value = ALLOWED
        mem.task.get_status.return_value = {"status_counts": {"completed": 1, "in_progress": 1}}
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        runs.progress("run-1", "Searching stores for navy kurta...")
        body = client.get("/outfit/plan/run-1/status").json()

    assert body["kind"] == "status"
    assert body["state"] == "running"
    assert body["message"] == "Searching stores for navy kurta..."
    assert body["step"] == 1
    assert body["ledger"] == {"completed": 1, "in_progress": 1}


def test_a_finished_plan_comes_back_on_the_poll():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [{"outfit_name": "Navy day", "products": []}],
            "summary": "", "raw": "", "run_id": "run-1", "clarity": {"tier": "high"},
        }
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        body = client.get("/outfit/plan/run-1/status").json()

    assert body["kind"] == "plan"
    assert body["state"] == "succeeded"
    assert body["outfits"][0]["outfitName"] == "Navy day"


def test_a_master_failure_ends_the_run_as_failed():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.side_effect = RuntimeError("gateway down")
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        body = client.get("/outfit/plan/run-1/status").json()

    assert body["kind"] == "error"
    assert body["state"] == "failed"
    assert body["errorKind"] == "system_down"


def test_a_stopped_run_ends_as_cancelled():
    from shopai.runs import RunCancelled

    def master(*_, should_stop, **__):
        client.post("/outfit/plan/run-1/stop")
        if should_stop():
            raise RunCancelled()
        return {}

    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.side_effect = master
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        body = client.get("/outfit/plan/run-1/status").json()

    assert body["state"] == "cancelled"
    assert body["kind"] == "message"


def test_stopping_a_finished_run_leaves_it_as_it_finished():
    with patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        shopai.return_value.run_master_recommendation.return_value = {
            "recommendations": [], "summary": "What's the occasion?",
            "raw": "", "run_id": "run-1", "clarity": {"tier": "low"},
        }
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        stopped = client.post("/outfit/plan/run-1/stop").json()
        body = client.get("/outfit/plan/run-1/status").json()

    assert stopped["state"] == "succeeded"
    assert body["state"] == "succeeded"


def test_a_second_message_while_the_run_is_going_is_busy():
    with patch("shopai.api.app._spawn"), \
         patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        body = client.post(
            "/outfit/plan/regular", json={"prompt": "in silk", "runId": "run-1"}
        ).json()

    assert body["kind"] == "error"
    assert body["errorKind"] == "busy"


def test_an_unknown_run_is_404():
    assert client.get("/outfit/plan/nope/status").status_code == 404
    assert client.post("/outfit/plan/nope/stop").status_code == 404


def test_clearing_the_task_stops_a_running_run():
    with patch("shopai.api.app._spawn"), \
         patch("shopai.api.app.Shopai") as shopai, \
         patch("shopai.api.app.memory"):
        shopai.return_value.run_validation.return_value = ALLOWED
        client.post("/outfit/plan/regular", json={"prompt": "navy kurta", "runId": "run-1"})
        client.delete("/task/run-1")

    assert runs.is_cancelled("run-1")
