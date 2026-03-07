"""Environment parsing and immutable runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


class SettingsError(RuntimeError):
    """Raised when environment configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Validated runtime configuration loaded from environment."""

    schedule_name: str
    action: str
    argo_enabled: bool
    schedule_scope: str
    default_startup_replicas: int
    hpa_min_zero_enabled: bool
    hpa_delete_restore_enabled: bool
    hpa_delete_only_enabled: bool
    protected_app_strict_mode: bool
    argo_discovery_use_automatic: bool
    argo_discovery_use_manual: bool
    argo_api_retries: int
    argo_api_retry_base_seconds: float
    argo_api_retry_max_seconds: float
    argo_server: str
    argo_token: str
    argo_scheme: str
    argo_insecure: bool
    verbose: bool
    dry_run: bool


def env_str(name: str, default: str | None = None) -> str:
    """Read a string environment variable, optionally with default."""
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise SettingsError(f"Missing required environment variable: {name}")
        return default
    return value


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean env var represented as 'true' or 'false'."""
    raw = os.getenv(name)
    if raw is None:
        return default
    if raw not in {"true", "false"}:
        raise SettingsError(f"{name} must be 'true' or 'false'")
    return raw == "true"


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer") from exc


def env_float(name: str, default: float) -> float:
    """Read a float environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number") from exc


def load_settings() -> Settings:
    """Build immutable settings from current environment variables."""
    schedule_name = env_str("SCHEDULE_NAME")
    action = env_str("ACTION")
    if action not in {"shutdown", "startup"}:
        raise SettingsError("ACTION must be 'shutdown' or 'startup'")

    argo_enabled_raw = env_str("ARGO_ENABLED")
    if argo_enabled_raw not in {"true", "false"}:
        raise SettingsError("ARGO_ENABLED must be 'true' or 'false'")

    schedule_scope = env_str("SCHEDULE_SCOPE", "namespace")
    if schedule_scope not in {"namespace", "deployment"}:
        raise SettingsError("SCHEDULE_SCOPE must be 'namespace' or 'deployment'")

    argo_enabled = argo_enabled_raw == "true"

    settings = Settings(
        schedule_name=schedule_name,
        action=action,
        argo_enabled=argo_enabled,
        schedule_scope=schedule_scope,
        default_startup_replicas=int(env_str("DEFAULT_STARTUP_REPLICAS", "1")),
        hpa_min_zero_enabled=env_bool("HPA_MIN_ZERO_ENABLED", False),
        hpa_delete_restore_enabled=env_bool("HPA_DELETE_RESTORE_ENABLED", False),
        hpa_delete_only_enabled=env_bool("HPA_DELETE_ONLY_ENABLED", False),
        protected_app_strict_mode=env_bool("PROTECTED_APP_STRICT_MODE", True),
        argo_discovery_use_automatic=env_bool("ARGO_DISCOVERY_USE_AUTOMATIC", True),
        argo_discovery_use_manual=env_bool("ARGO_DISCOVERY_USE_MANUAL", False),
        argo_api_retries=env_int("ARGO_API_RETRIES", 2),
        argo_api_retry_base_seconds=env_float("ARGO_API_RETRY_BASE_SECONDS", 0.2),
        argo_api_retry_max_seconds=env_float("ARGO_API_RETRY_MAX_SECONDS", 1.0),
        argo_server=env_str("ARGO_SERVER", ""),
        argo_token=env_str("ARGO_TOKEN", ""),
        argo_scheme=env_str("ARGO_SCHEME", "https"),
        argo_insecure=env_bool("ARGO_INSECURE", False),
        verbose=env_bool("VERBOSE", False),
        dry_run=env_bool("DRY_RUN", False),
    )

    if settings.argo_enabled:
        if not settings.argo_server:
            raise SettingsError("Missing required environment variable: ARGO_SERVER")
        if not settings.argo_token:
            raise SettingsError("Missing required environment variable: ARGO_TOKEN")
        if settings.argo_scheme not in {"http", "https"}:
            raise SettingsError("ARGO_SCHEME must be 'http' or 'https'")

    return settings
