"""F13's trusted materialization and F10 handoff.

Only the authenticated owner's *current* F09 decisions and approved F02 evidence
can produce F09_APPROVED snapshots. Historical snapshots alone are NEVER an
export authorization: F10 must call current_export_content before rendering.
Until F08 is present, F09 fails closed and this service cannot finalize anything.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.evidence.service import EvidenceService
from app.modules.generation.cover_letter_contracts import (
    StatementNotApprovedError,
    select_approved_statements,
)
from app.modules.statement_review.service import StatementReviewService

from .schemas import (
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceOrigin,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
    ResumeVersionView,
    VerificationSnapshotStatus,
)
from .service import ApplicationService


class FinalizationNotEligibleError(ValueError):
    """No trusted final snapshot/export is possible with the current sources."""


class TrustedFinalizationService:
    """Server-only bridge from F02 + F08/F09 to immutable F13 versions.

    Both collaborating modules are consulted through their public service
    contracts, not through F13 reads of their private database tables.
    """

    def __init__(self, session: Session, statement_reviews: StatementReviewService):
        self.applications = ApplicationService(session)
        self.evidence = EvidenceService(session)
        self.statement_reviews = statement_reviews

    def _current_content(
        self, *, user_id: UUID, statement_ids: tuple[UUID, ...]
    ) -> ResumeVersionContent:
        try:
            selected = select_approved_statements(
                self.statement_reviews, user_id=user_id, statement_ids=statement_ids
            )
        except StatementNotApprovedError as exc:
            # Do not distinguish missing, foreign, rejected, revoked or stale IDs.
            raise FinalizationNotEligibleError(
                "Selected statements are not currently eligible; refresh the review."
            ) from exc

        approved_evidence = {
            item.id: item for item in self.evidence.list_approved(user_id=user_id)
        }
        evidence_ids: list[UUID] = []
        seen_evidence: set[UUID] = set()
        provenance: list[ProvenanceSnapshotItem] = []
        for statement in selected:
            if statement.verification_status not in ("VERIFIED", "INFERRED"):
                raise FinalizationNotEligibleError("Unsupported statement.")
            for evidence_id in statement.evidence_ids:
                evidence = approved_evidence.get(evidence_id)
                if evidence is None or evidence.approved_at is None:
                    raise FinalizationNotEligibleError(
                        "Supporting evidence is no longer approved; re-verify."
                    )
                if evidence_id not in seen_evidence:
                    seen_evidence.add(evidence_id)
                    evidence_ids.append(evidence_id)
            provenance.append(
                ProvenanceSnapshotItem(
                    statement_id=statement.statement_id,
                    text=statement.text,
                    evidence_ids=statement.evidence_ids,
                    verification_status=VerificationSnapshotStatus(
                        statement.verification_status
                    ),
                    approval_status=ApprovalSnapshotStatus.APPROVED,
                    origin=ProvenanceOrigin.F09_APPROVED,
                )
            )

        evidence_snapshot = tuple(
            EvidenceSnapshotItem(
                evidence_id=evidence_id,
                evidence_type=approved_evidence[evidence_id].evidence_type,
                title=approved_evidence[evidence_id].title,
                organization=approved_evidence[evidence_id].organization,
                role=approved_evidence[evidence_id].role,
                description=approved_evidence[evidence_id].description,
                approved_at=approved_evidence[evidence_id].approved_at,
            )
            for evidence_id in evidence_ids
        )
        return ResumeVersionContent(
            evidence=evidence_snapshot, statements=tuple(provenance)
        )

    def finalize(
        self, *, user_id: UUID, application_id: UUID, statement_ids: tuple[UUID, ...]
    ) -> ResumeVersionView:
        # Check ownership before calling the F08/F09 provider or writing anything.
        self.applications.get_application(user_id=user_id, application_id=application_id)
        content = self._current_content(user_id=user_id, statement_ids=statement_ids)
        return self.applications.save_resume_version(
            user_id=user_id, application_id=application_id, content=content
        )

    def current_export_content(
        self, *, user_id: UUID, resume_version_id: UUID
    ) -> ResumeVersionContent:
        """F10's ONLY trusted source: revalidate at the moment of export.

        In particular, a saved, user-reviewed historical draft must not become
        exportable by supplying its UUID. A formerly trusted version whose
        evidence/text/revision has changed is likewise rejected.
        """
        version = self.applications.get_resume_version(
            user_id=user_id, resume_version_id=resume_version_id
        )
        previous = version.snapshot
        if not previous.statements or any(
            item.origin != ProvenanceOrigin.F09_APPROVED
            for item in previous.statements
        ):
            raise FinalizationNotEligibleError(
                "This historical draft has not passed trusted finalization."
            )
        current = self._current_content(
            user_id=user_id,
            statement_ids=tuple(item.statement_id for item in previous.statements),
        )
        if (
            current.statements != previous.statements
            or current.evidence != previous.evidence
        ):
            raise FinalizationNotEligibleError(
                "The saved content is stale; verify and approve a new version."
            )
        return current
