"""F07 errors. Callers can catch ``GenerationError`` to handle all of them."""


class GenerationError(Exception):
    """Base class for all F07 generation failures."""


class GenerationUnavailableError(GenerationError):
    """The AI provider failed, timed out, or raised an unexpected error."""


class MalformedProviderResponseError(GenerationError):
    """The AI provider returned something that is not a valid response."""
