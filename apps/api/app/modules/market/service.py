from __future__ import annotations

from collections import Counter
from datetime import datetime
from uuid import UUID

from app.modules.evidence.contracts import ApprovedEvidenceProvider
from app.modules.job_analysis.contracts import AnalysisResult

from .contracts import MarketSkillDemandResult, MarketSkillStatus, SkillComparison, SkillFrequency


class MarketSkillDemandService:
    """Minimal F16 market-skill analysis contract implementation."""

    def __init__(self, evidence_provider: ApprovedEvidenceProvider | None = None):
        self.evidence_provider = evidence_provider

    def analyze_collection(
        self,
        *,
        target_role: str,
        descriptions: tuple[str, ...],
        recurrence_threshold: int = 1,
        user_id: UUID | None = None,
    ) -> MarketSkillDemandResult:
        if not target_role.strip():
            raise ValueError("target_role is required")
        if not descriptions:
            raise ValueError("at least one job description is required")
        if recurrence_threshold <= 0:
            raise ValueError("recurrence_threshold must be positive")

        canonical_terms: dict[str, list[str]] = {}
        counts: Counter[str] = Counter()
        for description in descriptions:
            tokens = {term.strip().lower() for term in description.replace(";", " ").split() if term.strip()}
            for term in tokens:
                if len(term) < 3:
                    continue
                counts[term] += 1
                canonical_terms.setdefault(term, []).append(term)

        skills: list[SkillFrequency] = []
        for skill_name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if count < recurrence_threshold:
                continue
            skills.append(
                SkillFrequency(
                    skill_id=skill_name,
                    canonical_name=skill_name,
                    original_terms=(skill_name,),
                    posting_count=count,
                    posting_percentage=(count / len(descriptions)) * 100,
                    recurring=count >= recurrence_threshold,
                    priority=("required",),
                )
            )

        if user_id is None or self.evidence_provider is None:
            comparison = ()
        else:
            evidence = self.evidence_provider.list_grounding_contexts(user_id=user_id)
            comparison = tuple(
                SkillComparison(
                    skill_id=f"skill:{skill['skill_id']}",
                    canonical_name=skill['canonical_name'],
                    classification=(
                        MarketSkillStatus.STRONGLY_SUPPORTED
                        if evidence
                        else MarketSkillStatus.UNSUPPORTED
                    ),
                    explanation=(
                        "Current approved evidence supports this recurring skill request."
                        if evidence
                        else "No user-approved evidence is available for this skill."
                    ),
                    evidence_ids=tuple(item.evidence_id for item in evidence[:3]),
                    evidence_approved_at=tuple(item.approved_at for item in evidence[:3]),
                )
                for skill in skills
            )

        return MarketSkillDemandResult(
            analysis_id=f"market-{target_role.lower().replace(' ', '-')}",
            target_role=target_role,
            taxonomy_version="v1",
            recurrence_threshold=recurrence_threshold,
            submitted_count=len(descriptions),
            duplicate_count=0,
            excluded_count=0,
            analyzed_count=len(descriptions),
            skills=tuple(skills),
            comparisons=comparison,
            warnings=("This is a prototype market-skill summary; it does not claim full labor-market certainty.",),
        )


def analyze_collection(
    *,
    target_role: str,
    descriptions: tuple[str, ...],
    recurrence_threshold: int = 1,
    evidence_provider: ApprovedEvidenceProvider | None = None,
    user_id: UUID | None = None,
) -> MarketSkillDemandResult:
    return MarketSkillDemandService(evidence_provider=evidence_provider).analyze_collection(
        target_role=target_role,
        descriptions=descriptions,
        recurrence_threshold=recurrence_threshold,
        user_id=user_id,
    )
