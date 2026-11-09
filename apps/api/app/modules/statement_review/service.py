"""F09 review state machine and server-controlled approved-statement provider.

A user decision is valid only for the exact *current* F08 verification
revision. This service cannot certify client-built snapshots or arbitrary
statement text, and it does not write into F08's module or F02's tables.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.generation.cover_letter_schemas import ApprovedStatement

from .contract import (
    CurrentVerificationProvider,
    CurrentVerifiedStatement,
    VerificationStatus,
)
from .models import ReviewDecision, StatementReviewEventRecord, StatementReviewRecord
from .schemas import (
    EffectiveReviewStatus,
    ReviewHistoryItem,
    StatementReviewView,
)


class ReviewNotFoundError(LookupError):
    """Unknown and foreign-owned statements share one error."""


class ReviewNotEligibleError(ValueError):
    """F08 did not certify this claim for approval."""


class StaleVerificationError(ValueError):
    """The user's expected verification revision is not current."""


class StatementReviewService:
    def __init__(self, session: Session, verifier: CurrentVerificationProvider):
        self.session = session
        self.verifier = verifier

    def _verified(self, *, user_id: UUID, statement_id: UUID) -> CurrentVerifiedStatement:
        candidate = self.verifier.get_current(user_id=user_id, statement_id=statement_id)
        if (
            candidate is None
            or candidate.user_id != user_id
            or candidate.statement_id != statement_id
        ):
            raise ReviewNotFoundError("Statement not found")
        return candidate

    def _record(
        self, *, user_id: UUID, statement_id: UUID, lock: bool = False
    ) -> StatementReviewRecord | None:
        statement = select(StatementReviewRecord).where(
            StatementReviewRecord.user_id == user_id,
            StatementReviewRecord.statement_id == statement_id,
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    @staticmethod
    def _view(
        item: CurrentVerifiedStatement, record: StatementReviewRecord | None
    ) -> StatementReviewView:
        current = bool(record and record.verification_revision == item.revision)
        if record is None:
            review_status = EffectiveReviewStatus.UNREVIEWED
        elif not current:
            review_status = EffectiveReviewStatus.STALE
        elif record.decision == ReviewDecision.APPROVED:
            review_status = EffectiveReviewStatus.APPROVED
        else:
            review_status = EffectiveReviewStatus.REJECTED
        eligible = (
            current
            and record is not None
            and record.decision == ReviewDecision.APPROVED
            and item.status != VerificationStatus.UNSUPPORTED
        )
        return StatementReviewView(
            statement_id=item.statement_id,
            text=item.text,
            evidence_ids=item.evidence_ids,
            verification_status=item.status,
            verification_revision=item.revision,
            review_status=review_status,
            finalization_eligible=eligible,
            reviewed_revision=record.verification_revision if record else None,
        )

    def get_review(self, *, user_id: UUID, statement_id: UUID) -> StatementReviewView:
        current = self._verified(user_id=user_id, statement_id=statement_id)
        record = self._record(user_id=user_id, statement_id=statement_id)
        return self._view(current, record)

    def decide(
        self,
        *,
        user_id: UUID,
        statement_id: UUID,
        decision: ReviewDecision,
        expected_revision: str,
    ) -> StatementReviewView:
        current = self._verified(user_id=user_id, statement_id=statement_id)
        if current.revision != expected_revision:
            raise StaleVerificationError("Verification changed. Reload before reviewing.")
        if decision == ReviewDecision.APPROVED and current.status == VerificationStatus.UNSUPPORTED:
            raise ReviewNotEligibleError("UNSUPPORTED statements cannot be approved.")

        record = self._record(user_id=user_id, statement_id=statement_id, lock=True)
        if record is not None:
            if record.decision == decision and record.verification_revision == current.revision:
                return self._view(current, record)
            record.decision = decision
            record.verification_revision = current.revision
            record.event_count += 1
        else:
            record = StatementReviewRecord(
                user_id=user_id,
                statement_id=statement_id,
                decision=decision,
                verification_revision=current.revision,
                event_count=1,
            )
            self.session.add(record)
            self.session.flush()
        event = StatementReviewEventRecord(
            review_id=record.id,
            user_id=user_id,
            decision=decision,
            verification_revision=current.revision,
            sequence=record.event_count,
        )
        self.session.add(event)
        self.session.flush()
        return self._view(current, record)

    def history(self, *, user_id: UUID, statement_id: UUID) -> tuple[ReviewHistoryItem, ...]:
        self._verified(user_id=user_id, statement_id=statement_id)
        record = self._record(user_id=user_id, statement_id=statement_id)
        if record is None:
            return ()
        events = self.session.scalars(
            select(StatementReviewEventRecord)
            .where(
                StatementReviewEventRecord.review_id == record.id,
                StatementReviewEventRecord.user_id == user_id,
            )
            .order_by(StatementReviewEventRecord.sequence)
        ).all()
        return tuple(ReviewHistoryItem.model_validate(event) for event in events)

    def list_approved_statements(self, *, user_id: UUID) -> tuple[ApprovedStatement, ...]:
        """F09's implementation of the F11/F13 approved-statement provider.

        This read ALWAYS re-resolves F08's current revisions. Old approvals
        cannot survive a material edit or an evidence status change.
        """
        live = self.verifier.list_current(user_id=user_id)
        owned = self.session.scalars(
            select(StatementReviewRecord)
            .where(
                StatementReviewRecord.user_id == user_id,
                StatementReviewRecord.decision == ReviewDecision.APPROVED,
            )
        ).all()
        saved = {item.statement_id: item for item in owned}
        result: list[ApprovedStatement] = []
        for item in live:
            if item.user_id != user_id or item.status == VerificationStatus.UNSUPPORTED:
                continue
            decision = saved.get(item.statement_id)
            if decision is None or decision.verification_revision != item.revision:
                continue
            result.append(
                ApprovedStatement(
                    statement_id=item.statement_id,
                    text=item.text,
                    evidence_ids=item.evidence_ids,
                    verification_status=item.status.value,
                    approval_status="APPROVED",
                )
            )
        return tuple(result)
