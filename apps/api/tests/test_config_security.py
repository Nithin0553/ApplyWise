"""Production must never start with a default or weak JWT signing key."""

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings


def _settings(**values: str) -> Settings:
    return Settings(_env_file=None, **values)


def test_development_allows_the_default_key() -> None:
    assert _settings(app_env="development").app_secret_key == DEFAULT_SECRET_KEY


@pytest.mark.parametrize("key", [DEFAULT_SECRET_KEY, "too-short"])
def test_production_rejects_default_or_short_key(key: str) -> None:
    with pytest.raises(ValidationError):
        _settings(app_env="production", app_secret_key=key)


def test_production_accepts_a_strong_key() -> None:
    settings = _settings(app_env="production", app_secret_key="k" * 48)
    assert settings.app_secret_key == "k" * 48


def test_mixed_case_production_rejects_default_key() -> None:
    with pytest.raises(ValidationError):
        _settings(app_env="Production", app_secret_key=DEFAULT_SECRET_KEY)


def test_environment_is_normalized_for_all_production_guards() -> None:
    production = _settings(app_env=" Production ", app_secret_key="s" * 48)
    assert production.app_env == "production"
    development = _settings(app_env="Development")
    assert development.app_env == "development"
