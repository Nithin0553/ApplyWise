"""F05/F06: matching, gap analysis, and content selection."""

from .contracts import (
    ContentSelectionRequest,
    ContentSelectionResult,
    MatchingResult,
    RequirementMatch,
    SupportClassification,
)
from .service import MatchingService, match_requirements, select_content

__all__ = [
    "ContentSelectionRequest",
    "ContentSelectionResult",
    "MatchingResult",
    "MatchingService",
    "RequirementMatch",
    "SupportClassification",
    "match_requirements",
    "select_content",
]
