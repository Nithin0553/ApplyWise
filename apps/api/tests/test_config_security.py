"""Production must never start with a default or weak JWT signing key."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import _api_documentation_urls

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


@pytest.mark.parametrize("environment", ["production", " Production ", "PRODUCTION"])
def test_production_hides_all_api_docs_and_openapi_schema(environment: str) -> None:
    """The same normalized environment must disable all three FastAPI endpoints."""
    normalized = _settings(app_env=environment, app_secret_key="k" * 48).app_env
    app = FastAPI(**_api_documentation_urls(normalized))
    client = TestClient(app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_development_preserves_api_docs_and_openapi_schema() -> None:
    normalized = _settings(app_env="development").app_env
    app = FastAPI(**_api_documentation_urls(normalized))
    client = TestClient(app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200
