"""F08 verification service, and the provider F09 consumes.

Every read re-resolves the user's currently approved F02 evidence and
re-classifies from scratch. Nothing about a verdict is cached or persisted, so
there is no window in which a stored classification disagrees with the evidence
it was based on.

The cost of that choice is one F02 read per call rather than per statement;
the benefit is that "authoritative, not a saved snapshot" is a property of the
code rather than a promise in a document.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analysis import classify, derive_revision
from .contracts import (
    ApprovedEvidenceProvider,
    EvidenceFacts,
    VerificationStatus,
    VerifiedStatement,
)
from .models import VerifiedStatementRecord
from .schemas import MAX_STATEMENTS_PER_USER, StatementSubmission


class StatementNotFoundError(LookupError):
    """Unknown and foreign-owned statements share one error.

    A caller must not be able to tell which, so neither the service nor the
    route distinguishes them.
    """


class TooManyStatementsError(ValueError):
    """The user already holds the maximum number of statements."""


class VerificationService:
    """Implements ``VerificationProvider``; see ``contracts`` for the seam."""

    def __init__(self, session: Session, evidence: ApprovedEvidenceProvider) -> None:
        self.session = session
        self.evidence = evidence

    # --- internals --------------------------------------------------------

    def _approved(self, *, user_id: UUID) -> dict[UUID, EvidenceFacts]:
        return {
            item.evidence_id: item
            for item in self.evidence.list_grounding_contexts(user_id=user_id)
        }

    def _owned(self, *, user_id: UUID, statement_id: UUID) -> VerifiedStatementRecord:
        record = self.session.scalar(
            select(VerifiedStatementRecord).where(
                VerifiedStatementRecord.user_id == user_id,
                VerifiedStatementRecord.id == statement_id,
            )
        )
        if record is None:
            raise StatementNotFoundError("Statement not found")
        return record

    @staticmethod
    def _verify(
        record: VerifiedStatementRecord, approved: dict[UUID, EvidenceFacts]
    ) -> VerifiedStatement:
        evidence_ids = record.cited_ids()
        status, findings = classify(
            text=record.text, evidence_ids=evidence_ids, approved=approved
        )
        return VerifiedStatement(
            statement_id=record.id,
            user_id=record.user_id,
            text=record.text,
            evidence_ids=evidence_ids,
            status=status,
            revision=derive_revision(
                text=record.text,
                evidence_ids=evidence_ids,
                approved=approved,
                status=status,
            ),
            findings=findings,
        )

    # --- the F09-facing provider -----------------------------------------

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> VerifiedStatement | None:
        """Current verdict for one statement, or None if it is not this user's."""
        try:
            record = self._owned(user_id=user_id, statement_id=statement_id)
        except StatementNotFoundError:
            return None
        return self._verify(record, self._approved(user_id=user_id))

    def list_current(self, *, user_id: UUID) -> tuple[VerifiedStatement, ...]:
        """Every statement this user holds, classified against current evidence.

        Statements whose evidence has gone are returned as UNSUPPORTED rather
        than dropped: F09 needs to see that an approval has been invalidated,
        and a silently missing statement looks the same as one that never
        existed.
        """
        approved = self._approved(user_id=user_id)
        records = self.session.scalars(
            select(VerifiedStatementRecord)
            .where(VerifiedStatementRecord.user_id == user_id)
            .order_by(VerifiedStatementRecord.created_at, VerifiedStatementRecord.id)
        ).all()
        return tuple(self._verify(record, approved) for record in records)

    # --- owner-facing operations -----------------------------------------

    def submit(
        self, *, user_id: UUID, submission: StatementSubmission
    ) -> VerifiedStatement:
        """Persist a claim and return F08's verdict on it.

        The claim's text is the user's own; F08 does not police what a user may
        write down. What a caller cannot do is assert what the claim is worth:
        the classification is computed here, from evidence resolved server-side.
        """
        existing = self.session.scalar(
            select(VerifiedStatementRecord.id)
            .where(VerifiedStatementRecord.user_id == user_id)
            .limit(1)
            .offset(MAX_STATEMENTS_PER_USER - 1)
        )
        if existing is not None:
            raise TooManyStatementsError(
                f"At most {MAX_STATEMENTS_PER_USER} statements can be held at once."
            )

        record = VerifiedStatementRecord(
            user_id=user_id,
            text=submission.text.strip(),
            evidence_ids=VerifiedStatementRecord.pack_ids(submission.evidence_ids),
        )
        self.session.add(record)
        self.session.flush()
        return self._verify(record, self._approved(user_id=user_id))

    def withdraw(self, *, user_id: UUID, statement_id: UUID) -> None:
        record = self._owned(user_id=user_id, statement_id=statement_id)
        self.session.delete(record)
        self.session.flush()


def export_eligible(status: VerificationStatus) -> bool:
    """Req-Qual-Trace-2: only UNSUPPORTED claims are barred from export.

    INFERRED is not certified, but it is not fabricated either, and F09 lets
    the user stand behind it. The decision to approve remains theirs; this
    only reports whether verification blocks the claim outright.
    """
    return status is not VerificationStatus.UNSUPPORTED
