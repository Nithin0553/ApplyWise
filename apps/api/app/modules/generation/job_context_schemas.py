"""Request and response for reading a role title and employer from a posting.

Unlike F07's statements this output is not evidence-grounded and is not
verified: it pre-fills two fields the user can edit. It is kept in its own
module to make that difference obvious rather than letting it sit beside the
grounded-generation contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# The paste box in the UI stops at 6000 characters; the same bound here keeps
# an arbitrarily long body from being forwarded to a paid provider.
MAX_DESCRIPTION_CHARS = 6000


class JobContextSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)


class JobContextSuggestionView(BaseModel):
    """Either field may be empty: the posting may not state it."""

    role_title: str = ""
    company_name: str = ""
