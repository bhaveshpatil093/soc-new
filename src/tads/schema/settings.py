from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized settings module for TADS.
    Loads configuration from environment variables and validates them.
    """

    elastic_host: HttpUrl = Field(
        ...,
        description="The full URL to the Elasticsearch or Kibana cluster (e.g. https://es.example.com:9200)",
    )
    elastic_username: str = Field(
        ..., description="Username for authentication", min_length=1
    )
    elastic_password: SecretStr = Field(
        ..., description="Password for authentication. MUST be kept secret."
    )
    elastic_headers: dict[str, str] = Field(
        default_factory=dict,
        description="(Optional) Custom headers to include in every request",
    )
    elastic_ca_cert: Path | None = Field(
        default=None,
        description="(Optional) Absolute path to CA certificate for TLS verification",
    )
    elastic_verify_tls: bool = Field(
        default=True,
        description="(Optional) Whether to verify TLS certificates (true/false, default true)",
    )
    elastic_timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="(Optional) Client timeout in seconds (must be positive, default 30.0)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("elastic_password", mode="before")
    @classmethod
    def validate_password_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Ensure the password is not empty, and if it is, fail with a generic message."""
        if not v or not str(v).strip():
            raise ValueError(
                "ELASTIC_PASSWORD is required and cannot be empty. "
                "Check your .env file or environment variables."
            )
        return v

    @field_validator("elastic_ca_cert")
    @classmethod
    def validate_ca_cert_exists(cls, v: Path | None, info: ValidationInfo) -> Path | None:
        if v is not None and not v.exists():
            raise ValueError(f"ELASTIC_CA_CERT path does not exist: {v}")
        return v


def get_settings() -> Settings:
    """
    Loads and validates settings, raising clear, safe errors if invalid.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        # Pydantic's default ValidationError might echo back the raw input for some fields.
        # While SecretStr masks the output when printing the model, validation errors
        # on the field *before* it's parsed (e.g. if we had custom validators) might leak.
        # We ensure no secret is leaked by catching and raising a safe message.
        # To be absolutely sure, if the error contains 'elastic_password', we scrub it.

        error_msg = str(e)
        # Scrub any potential leakage of the secret value from error messages
        import re
        # Find lines in Pydantic's ValidationError output that might contain the value
        # Pydantic formats errors like:
        # elastic_password
        #   String should have at least 1 characters [type=string_too_short, input_value='', input_type=str]

        # We replace the input_value part if it's there for password.
        # For simplicity and absolute security, if we fail to load settings, we just
        # scrub any "input_value='...'" entirely from the error string just in case,
        # or we just raise a generic error for the password field.

        safe_msg_lines = []
        for line in error_msg.split('\n'):
            if "input_value=" in line:
                line = re.sub(r"input_value=.*?,", "input_value=<REDACTED>,", line)
                line = re.sub(r"input_value=.*\]", "input_value=<REDACTED>]", line)
            safe_msg_lines.append(line)

        safe_msg = "\n".join(safe_msg_lines)
        raise ValueError(f"Configuration Validation Error:\n{safe_msg}") from None
