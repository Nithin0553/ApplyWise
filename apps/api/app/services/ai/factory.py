"""Select the configured AI provider (``AI_PROVIDER`` setting)."""

from __future__ import annotations

from .demo import DemoAIProvider
from .provider import AIProvider
from .stub import StubAIProvider


class UnknownAIProviderError(ValueError):
    """Raised when ``AI_PROVIDER`` names a provider that is not implemented."""


def get_ai_provider(provider_name: str) -> AIProvider:
    name = provider_name.strip().lower()
    if name == "stub":
        return StubAIProvider()
    if name == "demo":
        return DemoAIProvider()
    # Real providers (e.g. "openai", "anthropic") are added here later,
    # each in its own module inside app/services/ai/. No vendor SDK is
    # imported anywhere else in the backend.
    raise UnknownAIProviderError(f"Unsupported AI provider: {provider_name!r}")
