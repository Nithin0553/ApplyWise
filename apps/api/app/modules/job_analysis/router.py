from fastapi import APIRouter, HTTPException

from .contracts import AnalysisRequest, AnalysisResult
from .parser import UnparseableDescription
from .service import analyze_job_description

router = APIRouter(prefix="/api/f04", tags=["F04 job analysis prototype"])


@router.post("/analyze", response_model=AnalysisResult)
def analyze(request: AnalysisRequest) -> AnalysisResult:
    try:
        return analyze_job_description(request)
    except UnparseableDescription as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
