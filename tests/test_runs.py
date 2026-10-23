from unittest.mock import patch

import pytest

from shopai.runs import FINISHED_TTL_SECONDS, RunRegistry


def test_a_run_starts_running():
    registry = RunRegistry()
    registry.start("r", "Getting started...")
    run = registry.get("r")
    assert run.state == "running"
    assert run.message == "Getting started..."
    assert run.step == 0


def test_progress_moves_the_step_only_on_a_new_line():
    registry = RunRegistry()
    registry.start("r")
    registry.progress("r", "Planning")
    registry.progress("r", "Planning")
    registry.progress("r", "Reviewing")
    assert registry.get("r").step == 2
    assert registry.get("r").message == "Reviewing"


def test_a_running_run_cannot_start_twice():
    registry = RunRegistry()
    registry.start("r")
    with pytest.raises(ValueError):
        registry.start("r")


def test_a_finished_run_can_take_its_next_turn():
    registry = RunRegistry()
    registry.start("r")
    registry.finish("r", "succeeded", "done")
    registry.start("r")
    assert registry.get("r").state == "running"


def test_the_first_ending_wins():
    registry = RunRegistry()
    registry.start("r")
    registry.finish("r", "cancelled", "stopped")
    registry.finish("r", "succeeded", "late plan")
    assert registry.get("r").state == "cancelled"
    assert registry.get("r").result == "stopped"


def test_stop_raises_the_flag_and_is_idempotent():
    registry = RunRegistry()
    registry.start("r")
    assert registry.request_stop("r") == "running"
    assert registry.request_stop("r") == "running"
    assert registry.is_cancelled("r")


def test_stopping_a_finished_run_changes_nothing():
    registry = RunRegistry()
    registry.start("r")
    registry.finish("r", "succeeded", "plan")
    assert registry.request_stop("r") == "succeeded"
    assert not registry.is_cancelled("r")


def test_an_unknown_run_is_none():
    registry = RunRegistry()
    assert registry.get("x") is None
    assert registry.request_stop("x") is None
    assert not registry.is_cancelled("x")


def test_old_finished_runs_are_swept_but_running_ones_stay():
    registry = RunRegistry()
    with patch("shopai.runs.time.monotonic", return_value=0.0):
        registry.start("old")
        registry.finish("old", "succeeded", "plan")
        registry.start("slow")
    with patch("shopai.runs.time.monotonic", return_value=FINISHED_TTL_SECONDS + 1):
        registry.start("new")
    assert registry.get("old") is None
    assert registry.get("slow") is not None
