"""Select the configured AI provider (``AI_PROVIDER`` setting)."""

from __future__ import annotations

from app.core.config import settings

from .anthropic import AnthropicAIProvider
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
    if name == "anthropic":
        # Constructed per call so a key rotated in the environment takes effect
        # without a restart, and so an absent key fails here rather than at the
        # first request to the model.
        return AnthropicAIProvider(
            api_key=settings.ai_api_key or "", model=settings.ai_model
        )
    # Further real providers are added here, each in its own module inside
    # app/services/ai/. No vendor SDK is imported anywhere in the backend.
    raise UnknownAIProviderError(f"Unsupported AI provider: {provider_name!r}")
