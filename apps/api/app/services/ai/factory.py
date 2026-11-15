"""Select the configured AI provider (``AI_PROVIDER`` setting)."""

from __future__ import annotations

from app.core.config import settings

from .anthropic import AnthropicAIProvider
from .demo import DemoAIProvider
from .fallback import FallbackAIProvider
from .provider import AIProvider
from .stub import StubAIProvider


# Shorter than the provider's own default: a request that hangs for half a
# minute before falling back is worse than one that gives up sooner.
DEMO_SAFE_TIMEOUT_SECONDS = 20.0


class UnknownAIProviderError(ValueError):
    """Raised when ``AI_PROVIDER`` names a provider that is not implemented."""


def get_ai_provider(provider_name: str) -> AIProvider:
    name = provider_name.strip().lower()
    if name == "stub":
        return StubAIProvider()
    if name == "demo":
        return DemoAIProvider()
    if name == "anthropic":
        if not settings.ai_api_key:
            # Reported as an unsupported provider so the caller gets a plain
            # 400 naming the missing setting, rather than a 500 from the
            # constructor raising AIProviderError the router does not catch.
            raise UnknownAIProviderError(
                "AI_PROVIDER=anthropic requires AI_API_KEY to be set."
            )
        # Constructed per call so a key rotated in the environment takes effect
        # without a restart. Wrapped so a timeout, a rate limit or an
        # unparseable reply falls back to the deterministic provider instead of
        # failing the request; the substitution is logged.
        return FallbackAIProvider(
            AnthropicAIProvider(
                api_key=settings.ai_api_key,
                model=settings.ai_model,
                timeout=DEMO_SAFE_TIMEOUT_SECONDS,
            ),
            StubAIProvider(),
        )
    # Further real providers are added here, each in its own module inside
    # app/services/ai/. No vendor SDK is imported anywhere in the backend.
    raise UnknownAIProviderError(f"Unsupported AI provider: {provider_name!r}")
