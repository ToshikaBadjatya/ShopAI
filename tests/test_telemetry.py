from unittest.mock import patch

from shopai import telemetry


def test_setup_telemetry_skips_when_no_api_key(monkeypatch, capsys):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_not_called()
    captured = capsys.readouterr()
    assert "PHOENIX_API_KEY not set" in captured.out


def test_setup_telemetry_registers_when_api_key_present(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_called_once_with(project_name="shopai", auto_instrument=True)


def test_setup_telemetry_passes_custom_endpoint(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://custom.example.com")

    with patch("shopai.telemetry.register") as mock_register:
        telemetry.setup_telemetry()

    mock_register.assert_called_once_with(
        project_name="shopai",
        auto_instrument=True,
        endpoint="https://custom.example.com",
    )
