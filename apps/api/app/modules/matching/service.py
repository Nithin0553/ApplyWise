from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.modules.evidence.contracts import ApprovedEvidenceProvider
from app.modules.job_analysis.contracts import AnalysisResult, Requirement

from .contracts import (
    ContentSelectionRequest,
    ContentSelectionResult,
    EvidenceReference,
    GapAssessment,
    MatchingResult,
    RequirementMatch,
    SelectionExplanation,
    SupportClassification,
)


class MatchingService:
    """Minimal deterministic F05/F06 implementation built around repo contracts."""

    def __init__(self, evidence_provider: ApprovedEvidenceProvider | None = None):
        self.evidence_provider = evidence_provider

    def match_requirements(
        self,
        *,
        analysis: AnalysisResult,
        user_id: UUID,
    ) -> MatchingResult:
        if not analysis.requirements:
            raise ValueError("analysis requires at least one requirement")

        if self.evidence_provider is None:
            evidence = ()
        else:
            evidence = tuple(self.evidence_provider.list_grounding_contexts(user_id=user_id))

        matches: list[RequirementMatch] = []
        for requirement in analysis.requirements:
            support = self._classify_requirement(requirement, evidence)
            matches.append(support)

        return MatchingResult(document_id=analysis.document_id, matches=tuple(matches), warnings=())

    def select_content(
        self,
        *,
        request: ContentSelectionRequest,
        user_id: UUID,
    ) -> ContentSelectionResult:
        explicit = set(request.explicit_evidence_ids)
        excluded = set(request.excluded_evidence_ids)

        candidates: list[UUID] = []
        seen: set[UUID] = set()
        w: list[str] = []
        explanations: list[SelectionExplanation] = []

        for match in request.requirement_matches:
            for evidence in match.evidence:
                if evidence.evidence_id in excluded:
                    continue
                if evidence.evidence_id in seen:
                    continue
                seen.add(evidence.evidence_id)
                candidates.append(evidence.evidence_id)
                explanations.append(
                    SelectionExplanation(
                        requirement_id=match.requirement_id,
                        reason=f"Supports {match.requirement_text} ({match.classification.value})",
                    )
                )

        if explicit:
            invalid = sorted(explicit - set(candidates))
            if invalid:
                raise ValueError(f"Explicit evidence IDs are invalid or unavailable: {invalid}")
            selected = tuple(
                evidence_id for evidence_id in explicit if evidence_id not in excluded
            )
            if len(selected) > request.max_evidence:
                raise ValueError("Requested selection exceeds the template evidence limit")
            return ContentSelectionResult(
                document_id=request.document_id,
                template_id=request.template_id,
                selected_evidence_ids=selected,
                explanations=tuple(explanations),
                warnings=tuple(w),
            )

        if not candidates:
            return ContentSelectionResult(
                document_id=request.document_id,
                template_id=request.template_id,
                selected_evidence_ids=(),
                explanations=tuple(explanations),
                warnings=("No eligible evidence was available for selection.",),
            )

        selected = tuple(candidates[: request.max_evidence])
        return ContentSelectionResult(
            document_id=request.document_id,
            template_id=request.template_id,
            selected_evidence_ids=selected,
            explanations=tuple(explanations[: len(selected)]),
            warnings=tuple(w),
        )

    def _classify_requirement(
        self,
        requirement: Requirement,
        evidence: Sequence[object],
    ) -> RequirementMatch:
        requirement_matches: list[EvidenceReference] = []
        evidence_text = " ".join(
            str(getattr(item, "description", "")) + " " + str(getattr(item, "title", ""))
            for item in evidence
        ).lower()
        requirement_text = requirement.text.lower()
        if requirement_text and requirement_text in evidence_text:
            aligned = [
                item for item in evidence if requirement_text in str(getattr(item, "description", ""))
            ]
            if not aligned:
                aligned = [
                    item for item in evidence if requirement_text in str(getattr(item, "title", "")).lower()
                ]
            for item in aligned:
                requirement_matches.append(
                    EvidenceReference(
                        evidence_id=getattr(item, "evidence_id"),
                        approved_at=getattr(item, "approved_at"),
                        title=getattr(item, "title"),
                        summary=(getattr(item, "description", None) or getattr(item, "skill_name", None)),
                    )
                )

        if not requirement_matches:
            return RequirementMatch(
                requirement_id=requirement.id,
                requirement_text=requirement.text,
                classification=SupportClassification.UNSUPPORTED,
                evidence=(),
                explanation="No approved evidence currently supports this requirement.",
                unmet_conditions=(requirement.text,),
                gap_assessment=GapAssessment.QUALIFICATION_GAP,
                review_warnings=tuple(requirement.review_reasons or ("Evidence matching is unavailable; review required.",)),
            )

        if requirement.experience is not None and requirement.experience.minimum_years is not None:
            matched = False
            for item in evidence:
                if getattr(item, "start_date", None) is None and getattr(item, "end_date", None) is None:
                    continue
                matched = True
                break
            if not matched:
                return RequirementMatch(
                    requirement_id=requirement.id,
                    requirement_text=requirement.text,
                    classification=SupportClassification.PARTIALLY_SUPPORTED,
                    evidence=tuple(requirement_matches),
                    explanation=f"Evidence supports the requirement text, but the required experience threshold remains insufficiently documented.",
                    unmet_conditions=(f"At least {requirement.experience.minimum_years} years of experience required.",),
                    gap_assessment=GapAssessment.QUALIFICATION_GAP,
                    review_warnings=tuple(requirement.review_reasons),
                )

        return RequirementMatch(
            requirement_id=requirement.id,
            requirement_text=requirement.text,
            classification=SupportClassification.STRONGLY_SUPPORTED,
            evidence=tuple(requirement_matches),
            explanation="Approved evidence directly supports the requirement and its stated constraints.",
            unmet_conditions=(),
            gap_assessment=None,
            review_warnings=tuple(requirement.review_reasons),
        )


def match_requirements(
    *,
    analysis: AnalysisResult,
    evidence_provider: ApprovedEvidenceProvider | None = None,
    user_id: UUID,
) -> MatchingResult:
    return MatchingService(evidence_provider=evidence_provider).match_requirements(
        analysis=analysis,
        user_id=user_id,
    )


def select_content(
    *,
    request: ContentSelectionRequest,
    evidence_provider: ApprovedEvidenceProvider | None = None,
    user_id: UUID,
) -> ContentSelectionResult:
    return MatchingService(evidence_provider=evidence_provider).select_content(
        request=request,
        user_id=user_id,
    )
