"""F16: market skill-demand analysis."""

from .contracts import MarketSkillDemandResult, MarketSkillStatus, SkillComparison, SkillFrequency
from .service import MarketSkillDemandService, analyze_collection

__all__ = [
    "MarketSkillDemandResult",
    "MarketSkillDemandService",
    "MarketSkillStatus",
    "SkillComparison",
    "SkillFrequency",
    "analyze_collection",
]
