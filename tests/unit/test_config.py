"""Config readers + the places-source factory (env-driven selection)."""

from __future__ import annotations

import pytest

from app.adapters.places import GooglePlacesSource, get_places_source
from app.core import config

pytestmark = pytest.mark.unit


def test_database_url_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert config.database_url() == config.DEFAULT_SQLITE_URL


def test_database_url_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2:///custom")
    assert config.database_url() == "postgresql+psycopg2:///custom"


def test_places_provider_default(monkeypatch):
    monkeypatch.delenv("PLACES_PROVIDER", raising=False)
    assert config.places_provider() == "google"


def test_google_places_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    assert config.google_places_api_key() is None
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "abc123")
    assert config.google_places_api_key() == "abc123"


def test_factory_requires_key(monkeypatch):
    monkeypatch.setenv("PLACES_PROVIDER", "google")
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_PLACES_API_KEY"):
        get_places_source()


def test_factory_returns_google_with_key(monkeypatch):
    monkeypatch.setenv("PLACES_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "abc123")
    assert isinstance(get_places_source(), GooglePlacesSource)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("PLACES_PROVIDER", "bing")
    with pytest.raises(RuntimeError, match="Unknown PLACES_PROVIDER"):
        get_places_source()
