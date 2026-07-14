from unittest.mock import patch

from shopai import telemetry


def test_setup_telemetry_skips_when_no_api_key(monkeypatch, capsys):
    monkeypatch.delenv("ARIZE_API_KEY", raising=False)
    monkeypatch.setenv("ARIZE_SPACE_ID", "test-space")

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_not_called()
    captured = capsys.readouterr()
    assert "ARIZE_API_KEY and ARIZE_SPACE_ID must both be set" in captured.out


def test_setup_telemetry_skips_when_no_space_id(monkeypatch, capsys):
    monkeypatch.setenv("ARIZE_API_KEY", "test-key")
    monkeypatch.delenv("ARIZE_SPACE_ID", raising=False)

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_not_called()
    captured = capsys.readouterr()
    assert "ARIZE_API_KEY and ARIZE_SPACE_ID must both be set" in captured.out


def test_setup_telemetry_registers_when_configured(monkeypatch):
    monkeypatch.setenv("ARIZE_API_KEY", "test-key")
    monkeypatch.setenv("ARIZE_SPACE_ID", "test-space")

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_called_once_with(project_name="shopai", auto_instrument=True)
