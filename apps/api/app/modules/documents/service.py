"""F10 export eligibility gate.

The single place that decides whether a stored version may be exported. It
refuses anything whose provenance is not F09_APPROVED, so an unverified or
merely user-edited draft cannot reach a downloadable file.
"""

from __future__ import annotations

from app.modules.applications.schemas import (
    ApprovalSnapshotStatus,
    ProvenanceOrigin,
    ResumeVersionSnapshot,
    VerificationSnapshotStatus,
)


class DocumentNotFinalizedError(ValueError):
    """Raised when a resume is not eligible for trusted export."""


def validate_export_eligibility(snapshot: ResumeVersionSnapshot) -> None:
    """Validate statement eligibility for trusted F10 export.

    The caller must also verify ownership and trusted finalization.
    """

    if not snapshot.statements:
        raise DocumentNotFinalizedError(
            "Resume has no statements eligible for export."
        )

    for statement in snapshot.statements:
        if (
            statement.verification_status == VerificationSnapshotStatus.UNSUPPORTED
            or statement.approval_status != ApprovalSnapshotStatus.APPROVED
            or statement.origin != ProvenanceOrigin.F09_APPROVED
        ):
            raise DocumentNotFinalizedError(
                "Resume contains unsupported or unapproved statements."
            )

        if not statement.evidence_ids:
            raise DocumentNotFinalizedError(
                "Resume contains a statement without supporting evidence."
            )

        if not statement.text.strip():
            raise DocumentNotFinalizedError(
                "Resume contains an empty statement."
            )
