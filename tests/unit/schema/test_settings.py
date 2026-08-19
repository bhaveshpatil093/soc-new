import pytest

from tads.schema.settings import get_settings


def test_settings_successful_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings load successfully when given valid environment variables."""
    monkeypatch.setenv("ELASTIC_HOST", "https://es.example.com:9200")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    monkeypatch.setenv("ELASTIC_PASSWORD", "supersecret123")

    settings = get_settings()
    assert str(settings.elastic_host) == "https://es.example.com:9200/"
    assert settings.elastic_username == "admin"
    assert settings.elastic_password.get_secret_value() == "supersecret123"


def test_settings_missing_var_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path 1: Missing environment variable."""
    monkeypatch.setenv("ELASTIC_HOST", "https://es.example.com:9200")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    monkeypatch.delenv("ELASTIC_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="Configuration Validation Error") as exc_info:
        get_settings()

    err_msg = str(exc_info.value)
    assert "elastic_password" in err_msg
    assert "Field required" in err_msg or "required" in err_msg.lower()


def test_settings_malformed_host_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path 2: Malformed host (not a valid URL)."""
    monkeypatch.setenv("ELASTIC_HOST", "not-a-valid-url")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    monkeypatch.setenv("ELASTIC_PASSWORD", "supersecret123")

    with pytest.raises(ValueError, match="Configuration Validation Error") as exc_info:
        get_settings()

    err_msg = str(exc_info.value)
    assert "elastic_host" in err_msg
    # Ensure the secret is NOT leaked in the error message about the host
    assert "supersecret123" not in err_msg


def test_settings_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test failure path 3: Invalid timeout (negative)."""
    monkeypatch.setenv("ELASTIC_HOST", "https://es.example.com:9200")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    monkeypatch.setenv("ELASTIC_PASSWORD", "supersecret123")
    monkeypatch.setenv("ELASTIC_TIMEOUT", "-5.0")

    with pytest.raises(ValueError, match="Configuration Validation Error") as exc_info:
        get_settings()

    err_msg = str(exc_info.value)
    assert "elastic_timeout" in err_msg
    assert "supersecret123" not in err_msg


def test_settings_password_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that printing or repr-ing the Settings object does not leak the password."""
    monkeypatch.setenv("ELASTIC_HOST", "https://es.example.com:9200")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    secret = "MY_ULTIMATE_SECRET_DO_NOT_LEAK"
    monkeypatch.setenv("ELASTIC_PASSWORD", secret)

    settings = get_settings()

    # Check string representation
    settings_str = str(settings)
    settings_repr = repr(settings)

    assert secret not in settings_str, "Secret leaked in str()!"
    assert secret not in settings_repr, "Secret leaked in repr()!"
    assert "**********" in settings_str or "**********" in settings_repr


def test_settings_password_not_leaked_in_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure that validation errors scrub the input value to prevent secret leakage."""
    monkeypatch.setenv("ELASTIC_HOST", "https://es.example.com:9200")
    monkeypatch.setenv("ELASTIC_USERNAME", "admin")
    secret = "LEAKY_SECRET_VALUE"
    # Pass a valid password but trigger an error on another field, and ensure the raw inputs
    # are scrubbed if Pydantic attempts to print the whole dictionary of inputs.
    monkeypatch.setenv("ELASTIC_PASSWORD", secret)
    monkeypatch.setenv("ELASTIC_TIMEOUT", "not-a-float")

    with pytest.raises(ValueError) as exc_info:
        get_settings()

    err_msg = str(exc_info.value)
    assert secret not in err_msg, f"Secret leaked in error message! Msg: {err_msg}"
    assert "<REDACTED>" in err_msg
