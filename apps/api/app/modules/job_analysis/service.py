"""Public producer entry point. Consumers depend on contracts, not parser internals."""

from .contracts import AnalysisRequest, AnalysisResult
from .parser import extract


def analyze_job_description(request: AnalysisRequest) -> AnalysisResult:
    return extract(request.job_description)
